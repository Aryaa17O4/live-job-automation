"""
gmail_job_agent.py — v3 STRICT
Scrapes Gmail for genuine job/internship emails only.
3-layer filter: sender blocklist + subject blocklist + body keyword check
Match % powered by resume_tailor.py
"""

import os, re, base64, datetime, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from resume_tailor import calculate_match, get_match_label

# ── Config ────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID   = os.environ.get("GOOGLE_SHEET_ID", "")
CREDS_FILE = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")

ACCOUNTS = [
    {"label": os.environ.get("GMAIL_LABEL_1", "Primary"),
     "token": os.environ.get("GMAIL_TOKEN_1", "token_1.json")},
    {"label": os.environ.get("GMAIL_LABEL_2", "Secondary"),
     "token": os.environ.get("GMAIL_TOKEN_2", "token_2.json")},
]

SHEET_HEADERS = [
    "Date", "Source", "Platform", "Email ID", "Job Title", "Company",
    "Location", "Stipend", "Duration", "Match %", "Job URL", "JD URL",
    "Resume URL", "Cover Letter URL", "Status", "Processed At",
]

# ── STRICT Gmail search query ─────────────────────────────────────────────
# Only emails where subject explicitly mentions hiring/internship terms
# Hard-excludes GitHub, OTP, invoices, newsletters at the API level
GMAIL_QUERY = (
    "("
      "subject:(internship) OR "
      "subject:(\"we are hiring\") OR "
      "subject:(\"job opening\") OR "
      "subject:(\"hiring for\") OR "
      "subject:(\"apply now\") OR "
      "subject:(\"job opportunity\") OR "
      "subject:(\"exciting opportunity\") OR "
      "subject:(\"open position\") OR "
      "subject:(\"new jobs\") OR "
      "subject:(\"career opportunity\") OR "
      "subject:(\"we're hiring\") OR "
      "subject:(fresher) OR "
      "subject:(recruitment) OR "
      "subject:(\"job alert\")"
    ") "
    "newer_than:14d "
    "-from:noreply@github.com "
    "-from:notifications@github.com "
    "-from:no-reply@github.com "
    "-from:no-reply@accounts.google.com "
    "-from:no-reply@google.com "
    "-from:mailer@linkedin.com "
    "-from:jobs-noreply@linkedin.com "
    "-subject:(OTP) "
    "-subject:(\"verification code\") "
    "-subject:(\"GitHub Actions\") "
    "-subject:(workflow) "
    "-subject:(\"pull request\") "
    "-subject:(merged) "
    "-subject:(invoice) "
    "-subject:(receipt) "
    "-subject:(payment) "
    "-subject:(newsletter) "
    "-subject:(\"password reset\") "
    "-subject:(\"security alert\") "
    "-subject:(\"personal access token\") "
)

# ── 3-Layer Filter ────────────────────────────────────────────────────────

# Layer 1: Block these senders always
BLOCKED_SENDERS = [
    "github.com", "github.io",
    "no-reply@", "noreply@",
    "accounts.google.com",
    "mailer@linkedin", "jobs-noreply@linkedin",
    "swiggy", "zomato", "amazon", "flipkart",
    "myntra", "meesho", "ajio",
    "coursera", "udemy", "edureka",
    "razorpay.com",
]

# Layer 2: Block these subject patterns always
BLOCKED_SUBJECTS = [
    "github actions", "workflow run", "pull request",
    "build failed", "build passed", "merged",
    "otp", "one time password", "verification code",
    "password reset", "forgot password",
    "invoice", "receipt", "payment successful",
    "order confirmed", "your order",
    "newsletter", "weekly digest", "daily digest",
    "security alert", "new device", "sign-in",
    "personal access token", "token added",
    "unsubscribe", "promotional",
]

# Layer 3: Subject must have at least 1 of these
REQUIRED_SUBJECT = [
    "intern", "internship", "hiring", "job", "opportunity",
    "position", "opening", "vacancy", "career", "apply",
    "role", "recruit", "stipend", "fresher", "placement",
]

# Layer 3: Body must have at least 2 of these
REQUIRED_BODY = [
    "intern", "internship", "apply", "application",
    "stipend", "salary", "compensation", "ctc",
    "job description", "responsibilities", "qualifications",
    "we are looking", "we're hiring", "join our team",
    "skills required", "requirements",
    "location", "remote", "hybrid", "onsite",
    "duration", "months",
]


def _is_job_email(sender: str, subject: str, body: str) -> bool:
    s = sender.lower()
    sub = subject.lower()
    bod = body[:1500].lower()

    # Layer 1 — sender block
    if any(b in s for b in BLOCKED_SENDERS):
        return False

    # Layer 2 — subject block
    if any(b in sub for b in BLOCKED_SUBJECTS):
        return False

    # Layer 3a — subject must have a job keyword
    if not any(kw in sub for kw in REQUIRED_SUBJECT):
        return False

    # Layer 3b — body must have at least 2 job phrases
    if sum(1 for kw in REQUIRED_BODY if kw in bod) < 2:
        return False

    return True


# ── ThreadedHTTPServer for OAuth (avoids 502 proxy timeouts) ─────────────
class _OAuthHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        _OAuthHandler.auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Auth complete. Close this tab.")

    def log_message(self, *args): pass


class ThreadedOAuthServer(HTTPServer):
    def __init__(self, addr, handler):
        super().__init__(addr, handler)
        self._t = threading.Thread(target=self.serve_forever, daemon=True)

    def start(self): self._t.start()

    def wait_for_code(self, timeout=180):
        self._t.join(timeout)
        return _OAuthHandler.auth_code


# ── Auth ──────────────────────────────────────────────────────────────────
def _get_credentials(token_path: str) -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds, token_path)
        return creds

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDS_FILE, SCOPES, redirect_uri="http://localhost:8765"
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\nOpen to authenticate:\n{auth_url}\n")
    srv = ThreadedOAuthServer(("localhost", 8765), _OAuthHandler)
    srv.start()
    code = srv.wait_for_code()
    srv.shutdown()
    if not code:
        raise RuntimeError("OAuth timeout.")
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_token(creds, token_path)
    return creds


def _save_token(creds, path):
    with open(path, "w") as f:
        f.write(creds.to_json())


# ── Gmail helpers ─────────────────────────────────────────────────────────
def _get_body(payload: dict) -> str:
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            body += _get_body(part)
    elif payload.get("mimeType") in ("text/plain", "text/html"):
        data = payload.get("body", {}).get("data", "")
        if data:
            body += base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
    return body


def _hdr(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ── Metadata extractors ───────────────────────────────────────────────────
def _find(patterns, text, group=1):
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return m.group(group).strip()
            except Exception:
                return m.group(0).strip()
    return ""


STIPEND_RE = [
    r"stipend[:\s]+(?:rs\.?|inr|₹)?\s*(\d[\d,]+)",
    r"(?:rs\.?|inr|₹)\s*(\d[\d,]+)\s*(?:/-|per\s*month|p\.?m\.?|/month)?",
    r"(\d{4,6})\s*/\s*(?:month|mo)\b",
    r"salary[:\s]+(?:rs\.?|inr|₹)?\s*(\d[\d,]+)",
    r"\$\s*(\d[\d,]+)",
]

LOCATION_RE = [
    r"location[:\s]+([A-Za-z ,/\-]+?)(?:\n|\.|\|)",
    r"\b(remote|work from home|wfh|hybrid|on-?site)\b",
    r"\b(bangalore|bengaluru|mumbai|delhi|noida|gurugram|gurgaon|pune"
    r"|hyderabad|chennai|kolkata|ahmedabad|jaipur|indore)\b",
]

DURATION_RE = [
    r"duration[:\s]+(\d+\s*(?:month|week|year)s?)",
    r"(\d+)[- ](?:month|week)[s]?\s*internship",
    r"internship\s+(?:of\s+)?(\d+\s*(?:month|week)s?)",
]

COMPANY_RE = [
    r"company[:\s]+([A-Za-z0-9 &\-\.]+)",
    r"organisation[:\s]+([A-Za-z0-9 &\-\.]+)",
    r"([A-Z][A-Za-z0-9 &\-]+?)\s+(?:Pvt\.?\s*Ltd\.?|Private Limited"
    r"|Technologies|Tech|Software|Solutions|Labs|Inc\.?)",
    r"(?:at|from|join)\s+([A-Z][A-Za-z0-9 &\-]+?)\s+(?:as|for|–|-)",
]

PLATFORM_MAP = {
    "LinkedIn":    ["linkedin.com"],
    "Internshala": ["internshala.com"],
    "Wellfound":   ["wellfound.com", "angel.co"],
    "Naukri":      ["naukri.com"],
    "Indeed":      ["indeed.com"],
    "Unstop":      ["unstop.com"],
    "Glassdoor":   ["glassdoor.com"],
    "Cutshort":    ["cutshort.io"],
    "Hirist":      ["hirist.tech"],
}


def _platform(subject, body, sender):
    txt = (subject + body[:300] + sender).lower()
    for name, domains in PLATFORM_MAP.items():
        if any(d in txt for d in domains):
            return name
    return "Email/Direct"


def _job_url(body):
    urls = re.findall(r"https?://[^\s\)\]\>\"\']+", body)
    for u in urls:
        if any(k in u.lower() for k in
               ["job", "intern", "apply", "career", "position", "opening", "vacancy"]):
            return u.rstrip(".,;)")
    return urls[0].rstrip(".,;)") if urls else ""


def _job_title(subject, body):
    # Try subject patterns
    for pat in [
        r"(?:hiring|opening|position|role|internship|vacancy)[:\s]+([^\|\-\n]{5,60})",
        r"(?:for|–|-)\s+([A-Za-z /\-&]{5,50})\s+(?:intern|role|position|developer|engineer)",
    ]:
        m = re.search(pat, subject, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Try body
    m = re.search(
        r"(?:position|role|title|opening)[:\s]+([A-Za-z /\-&]{5,50})(?:\n|at\s|,)",
        body[:400], re.IGNORECASE
    )
    if m:
        return m.group(1).strip()

    # Fallback: clean subject
    clean = re.sub(
        r"(?i)(re:|fw:|fwd:|internship at|hiring for|opening for|opportunity:|job alert:?)",
        "", subject
    ).strip()
    return clean[:80] or subject[:80]


# ── Sheets ────────────────────────────────────────────────────────────────
def _get_sheet(creds):
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet("Jobs")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet("Jobs", 1000, len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    return ws


def _existing_ids(ws):
    try:
        idx = SHEET_HEADERS.index("Email ID") + 1
        return set(ws.col_values(idx)[1:])
    except Exception:
        return set()


# ── Process one message ───────────────────────────────────────────────────
def _process(msg_id, svc, ws, seen, label):
    if msg_id in seen:
        return False

    msg     = svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
    payload = msg["payload"]
    headers = payload.get("headers", [])
    subject = _hdr(headers, "Subject")
    sender  = _hdr(headers, "From")
    date_s  = _hdr(headers, "Date")
    body    = _get_body(payload)
    plain   = re.sub(r"<[^>]+>", " ", body)   # strip HTML

    # ── 3-Layer filter ────────────────────────────────────────────────────
    if not _is_job_email(sender, subject, plain):
        print(f"  ✗ Skipped: {subject[:55]}")
        return False

    # ── Extract ───────────────────────────────────────────────────────────
    title    = _job_title(subject, plain)
    company  = _find(COMPANY_RE, plain) or sender.split("<")[0].strip()
    location = _find(LOCATION_RE, plain)
    stipend  = _find(STIPEND_RE, plain)
    duration = _find(DURATION_RE, plain)
    platform = _platform(subject, plain, sender)
    url      = _job_url(plain)

    if stipend and stipend[0].isdigit():
        stipend = f"₹{stipend}"

    # ── Match % ───────────────────────────────────────────────────────────
    match_pct   = calculate_match(plain, title)
    match_label = get_match_label(match_pct)

    # Skip very weak matches (not relevant at all)
    if match_pct < 15:
        print(f"  ✗ Low match ({match_pct}%): {title[:45]}")
        return False

    # ── Date ──────────────────────────────────────────────────────────────
    try:
        from email.utils import parsedate_to_datetime
        date_fmt = parsedate_to_datetime(date_s).strftime("%Y-%m-%d")
    except Exception:
        date_fmt = datetime.date.today().isoformat()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        date_fmt,
        label,
        platform,
        msg_id,
        title,
        company,
        location,
        stipend,
        duration,
        f"{match_pct}% ({match_label})",
        url,
        "", "", "",
        "New",
        now,
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    seen.add(msg_id)
    print(f"  ✔ {match_pct}% | {title[:40]} | {company[:25]}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────
def run_agent():
    print("=" * 60)
    print("Job Agent v3 — Strict Filter")
    print("=" * 60)

    if not SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID not set.")

    total = 0
    for acc in ACCOUNTS:
        label, token = acc["label"], acc["token"]

        if not os.path.exists(token) and not os.path.exists(CREDS_FILE):
            print(f"[{label}] No credentials — skipping.")
            continue

        print(f"\n[{label}] Authenticating…")
        try:
            creds = _get_credentials(token)
        except Exception as e:
            print(f"[{label}] Auth failed: {e}")
            continue

        svc  = build("gmail", "v1", credentials=creds)
        ws   = _get_sheet(creds)
        seen = _existing_ids(ws)

        print(f"[{label}] Querying Gmail…")
        res  = svc.users().messages().list(
            userId="me", q=GMAIL_QUERY, maxResults=100
        ).execute()
        msgs = res.get("messages", [])
        print(f"[{label}] {len(msgs)} emails matched query.")

        logged = 0
        for m in msgs:
            try:
                if _process(m["id"], svc, ws, seen, label):
                    logged += 1
            except Exception as e:
                print(f"  ✗ Error: {e}")

        print(f"[{label}] ✔ {logged} new jobs logged.")
        total += logged

    print(f"\nTotal: {total} new jobs logged.")


if __name__ == "__main__":
    run_agent()
  
