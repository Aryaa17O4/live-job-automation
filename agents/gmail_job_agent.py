"""
gmail_job_agent.py
------------------
Scrapes two Gmail accounts for job postings, extracts metadata,
scores each against Aryan's resume, and logs to Google Sheets.

Column schema (16 cols):
  Date | Source | Platform | Email ID | Job Title | Company | Location |
  Stipend | Duration | Match % | Job URL | JD URL | Resume URL |
  Cover Letter URL | Status | Processed At
"""

import os
import re
import base64
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ── local module ──────────────────────────────────────────────────────────
from resume_tailor import calculate_match, get_match_label

# ── Config ────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]

SHEET_ID    = os.environ.get("GOOGLE_SHEET_ID", "")
CREDS_FILE  = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")

# Two Gmail accounts — set via environment variables
ACCOUNTS = [
    {
        "label":   os.environ.get("GMAIL_LABEL_1", "Primary"),
        "token":   os.environ.get("GMAIL_TOKEN_1", "token_1.json"),
    },
    {
        "label":   os.environ.get("GMAIL_LABEL_2", "Secondary"),
        "token":   os.environ.get("GMAIL_TOKEN_2", "token_2.json"),
    },
]

# Search query used in Gmail API
GMAIL_QUERY = (
    "subject:(internship OR hiring OR job OR apply OR opportunity OR role OR position) "
    "newer_than:7d"
)

SHEET_HEADERS = [
    "Date", "Source", "Platform", "Email ID", "Job Title", "Company",
    "Location", "Stipend", "Duration", "Match %", "Job URL", "JD URL",
    "Resume URL", "Cover Letter URL", "Status", "Processed At",
]

# ── ThreadedHTTPServer for OAuth (avoids 502 proxy timeouts) ──────────────
class _OAuthHandler(BaseHTTPRequestHandler):
    auth_code: Optional[str] = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        _OAuthHandler.auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Auth complete. You may close this tab.")

    def log_message(self, *args):
        pass  # suppress request noise

class ThreadedOAuthServer(HTTPServer):
    def __init__(self, server_address, handler):
        super().__init__(server_address, handler)
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)

    def start(self):
        self._thread.start()

    def wait_for_code(self, timeout=120) -> Optional[str]:
        self._thread.join(timeout)
        return _OAuthHandler.auth_code


# ── Auth helpers ──────────────────────────────────────────────────────────

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

    # Fresh OAuth flow via ThreadedHTTPServer
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDS_FILE, SCOPES,
        redirect_uri="http://localhost:8765"
    )
    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\nOpen this URL to authenticate:\n{auth_url}\n")

    server = ThreadedOAuthServer(("localhost", 8765), _OAuthHandler)
    server.start()
    code = server.wait_for_code(timeout=180)
    server.shutdown()

    if not code:
        raise RuntimeError("OAuth timeout — no auth code received.")

    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_token(creds, token_path)
    return creds


def _save_token(creds: Credentials, path: str):
    with open(path, "w") as f:
        f.write(creds.to_json())


# ── Gmail helpers ─────────────────────────────────────────────────────────

def _get_email_body(payload: dict) -> str:
    """Recursively decode email body from MIME payload."""
    body = ""
    if "parts" in payload:
        for part in payload["parts"]:
            body += _get_email_body(part)
    elif payload.get("mimeType") in ("text/plain", "text/html"):
        data = payload.get("body", {}).get("data", "")
        if data:
            body += base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
    return body


def _extract_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


# ── Metadata extraction from email body ───────────────────────────────────

_STIPEND_PATTERNS = [
    r"stipend[:\s]+(?:rs\.?|inr|₹)?\s*(\d[\d,]*)\s*(?:/-|per\s*month|p\.?m\.?|/month)?",
    r"(?:rs\.?|inr|₹)\s*(\d[\d,]+)\s*(?:/-|per\s*month|p\.?m\.?|/month)",
    r"(\d[\d,]+)\s*(?:rs\.?|inr|₹)\s*(?:per\s*month|p\.?m\.?)?",
    r"salary[:\s]+(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
    r"compensation[:\s]+(?:rs\.?|inr|₹)?\s*(\d[\d,]*)",
    r"(\d{4,6})\s*/\s*(?:month|mo)",
    r"usd?\s*(\d[\d,]+)",
    r"\$\s*(\d[\d,]+)",
]

_LOCATION_PATTERNS = [
    r"location[:\s]+([A-Za-z ,/]+?)(?:\n|,\s*(?:india|remote|hybrid)|$)",
    r"(?:based in|office at|located at|work from)[:\s]+([A-Za-z ,]+?)(?:\n|\.)",
    r"\b(remote|work from home|wfh|hybrid|on-?site)\b",
    r"\b(bangalore|bengaluru|mumbai|delhi|noida|gurugram|gurgaon|pune|hyderabad|chennai|kolkata|ahmedabad)\b",
]

_DURATION_PATTERNS = [
    r"duration[:\s]+(\d+\s*(?:month|week|year)s?)",
    r"(\d+)[- ](?:month|week|year)[s]?\s*internship",
    r"internship\s+(?:of\s+)?(\d+\s*(?:month|week)s?)",
    r"(\d+)[- ](?:month|week)[s]?\s+(?:contract|role|position)",
]

_URL_PATTERNS = [
    r"https?://[^\s\)\]\>\"\']+",
]

_PLATFORM_KEYWORDS = {
    "LinkedIn":    ["linkedin"],
    "Internshala": ["internshala"],
    "Wellfound":   ["wellfound", "angel.co", "angellist"],
    "Naukri":      ["naukri"],
    "Indeed":      ["indeed"],
    "Unstop":      ["unstop", "dare2compete"],
    "Glassdoor":   ["glassdoor"],
    "GitHub":      ["github"],
    "Email/Direct": [],            # fallback
}

_COMPANY_PATTERNS = [
    r"(?:at|from|with|join)\s+([A-Z][A-Za-z0-9 &\-\.]+?)(?:\s+is|\s+are|\s+has|[,\.\n])",
    r"([A-Z][A-Za-z0-9 &\-\.]+?)\s+(?:Pvt\.?\s*Ltd\.?|Private Limited|Technologies|Tech|Software|Solutions|Labs|Studios)",
    r"company[:\s]+([A-Za-z0-9 &\-\.]+)",
    r"organisation[:\s]+([A-Za-z0-9 &\-\.]+)",
    r"employer[:\s]+([A-Za-z0-9 &\-\.]+)",
]


def _extract_field(patterns: list[str], text: str, group: int = 1, flags: int = re.IGNORECASE) -> str:
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            try:
                return m.group(group).strip()
            except IndexError:
                return m.group(0).strip()
    return ""


def _detect_platform(subject: str, body: str, sender: str) -> str:
    combined = (subject + " " + body + " " + sender).lower()
    for platform, keywords in _PLATFORM_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return platform
    return "Email/Direct"


def _extract_job_url(body: str) -> str:
    """Return the most job-relevant URL from the body."""
    urls = re.findall(_URL_PATTERNS[0], body)
    # Prefer URLs that look like job posts
    for url in urls:
        ul = url.lower()
        if any(kw in ul for kw in ["job", "internship", "apply", "career", "position", "opening", "role"]):
            return url.rstrip(".,;)")
    return urls[0].rstrip(".,;)") if urls else ""


def _extract_job_title(subject: str, body: str) -> str:
    """Pull job title from subject or first 500 chars of body."""
    # Try subject line first
    title_m = re.search(
        r"(?:hiring|opening|position|role|internship|vacancy)[:\s]+([^\|\-\n]{5,60})",
        subject, re.IGNORECASE
    )
    if title_m:
        return title_m.group(1).strip()

    body_snippet = body[:500]
    title_m = re.search(
        r"(?:position|role|title|opening|job)[:\s]+([A-Za-z /\-&]+?)(?:\n|at\s|@\s|for\s|,)",
        body_snippet, re.IGNORECASE
    )
    if title_m:
        return title_m.group(1).strip()

    # Fallback: clean up subject
    clean = re.sub(r"(?i)(re:|fw:|fwd:|internship at|hiring for|opening for|opportunity:)", "", subject).strip()
    return clean[:80] if clean else subject[:80]


# ── Google Sheets helpers ─────────────────────────────────────────────────

def _get_sheet(creds: Credentials) -> gspread.Worksheet:
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    try:
        ws = sh.worksheet("Jobs")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Jobs", rows=1000, cols=len(SHEET_HEADERS))
        ws.append_row(SHEET_HEADERS)
    return ws


def _get_existing_email_ids(ws: gspread.Worksheet) -> set[str]:
    try:
        col_idx = SHEET_HEADERS.index("Email ID") + 1
        return set(ws.col_values(col_idx)[1:])    # skip header
    except Exception:
        return set()


# ── Core processing ───────────────────────────────────────────────────────

def _process_message(
    msg_id: str,
    gmail_svc,
    ws: gspread.Worksheet,
    existing_ids: set[str],
    account_label: str,
) -> bool:
    """Fetch, parse, score, and append one email. Returns True if logged."""

    if msg_id in existing_ids:
        return False

    msg = gmail_svc.users().messages().get(
        userId="me", id=msg_id, format="full"
    ).execute()

    payload  = msg["payload"]
    headers  = payload.get("headers", [])
    subject  = _extract_header(headers, "Subject")
    sender   = _extract_header(headers, "From")
    date_str = _extract_header(headers, "Date")
    body     = _get_email_body(payload)
    body_plain = re.sub(r"<[^>]+>", " ", body)   # strip HTML tags

    # ── Filter: skip obvious non-job emails ──────────────────────────────
    combined_lower = (subject + " " + body_plain[:300]).lower()
    job_signals = [
        "intern", "hiring", "apply", "application", "job", "role",
        "position", "opening", "opportunity", "career", "vacancy",
        "stipend", "salary", "compensation"
    ]
    if not any(sig in combined_lower for sig in job_signals):
        return False

    # ── Extract metadata ─────────────────────────────────────────────────
    job_title = _extract_job_title(subject, body_plain)
    company   = _extract_field(_COMPANY_PATTERNS, body_plain) or sender.split("<")[0].strip()
    location  = _extract_field(_LOCATION_PATTERNS, body_plain)
    stipend   = _extract_field(_STIPEND_PATTERNS, body_plain)
    duration  = _extract_field(_DURATION_PATTERNS, body_plain)
    platform  = _detect_platform(subject, body_plain, sender)
    job_url   = _extract_job_url(body_plain)

    # Normalise stipend — add ₹ prefix if it's a bare number
    if stipend and stipend.isdigit():
        stipend = f"₹{stipend}"
    elif stipend and stipend[0].isdigit():
        stipend = f"₹{stipend}"

    # ── Match scoring ─────────────────────────────────────────────────────
    match_pct = calculate_match(body_plain, job_title)
    match_label = get_match_label(match_pct)

    # ── Parse date ───────────────────────────────────────────────────────
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        date_formatted = dt.strftime("%Y-%m-%d")
    except Exception:
        date_formatted = datetime.date.today().isoformat()

    processed_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        date_formatted,                    # Date
        account_label,                     # Source (which Gmail account)
        platform,                          # Platform
        msg_id,                            # Email ID
        job_title,                         # Job Title
        company,                           # Company
        location,                          # Location
        stipend,                           # Stipend
        duration,                          # Duration
        f"{match_pct}% ({match_label})",   # Match %
        job_url,                           # Job URL
        "",                                # JD URL (manual)
        "",                                # Resume URL (manual)
        "",                                # Cover Letter URL (manual)
        "New",                             # Status
        processed_at,                      # Processed At
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    existing_ids.add(msg_id)
    print(f"  ✔ Logged: {job_title[:50]} | {match_pct}% | {company[:30]}")
    return True


def run_agent():
    print("=" * 60)
    print("Job Agent starting…")
    print("=" * 60)

    if not SHEET_ID:
        raise ValueError("GOOGLE_SHEET_ID env var is not set.")

    total_logged = 0

    for account in ACCOUNTS:
        label      = account["label"]
        token_path = account["token"]

        if not os.path.exists(token_path) and not os.path.exists(CREDS_FILE):
            print(f"[{label}] Skipping — no credentials found.")
            continue

        print(f"\n[{label}] Authenticating…")
        try:
            creds = _get_credentials(token_path)
        except Exception as e:
            print(f"[{label}] Auth failed: {e}")
            continue

        gmail_svc = build("gmail", "v1", credentials=creds)
        ws        = _get_sheet(creds)
        existing  = _get_existing_email_ids(ws)

        print(f"[{label}] Searching Gmail…")
        results   = gmail_svc.users().messages().list(
            userId="me", q=GMAIL_QUERY, maxResults=50
        ).execute()
        messages  = results.get("messages", [])
        print(f"[{label}] Found {len(messages)} candidate emails.")

        logged = 0
        for msg in messages:
            try:
                ok = _process_message(msg["id"], gmail_svc, ws, existing, label)
                if ok:
                    logged += 1
            except Exception as e:
                print(f"  ✗ Error on {msg['id']}: {e}")

        print(f"[{label}] Logged {logged} new job(s).")
        total_logged += logged

    print(f"\nDone. Total new jobs logged: {total_logged}")


if __name__ == "__main__":
    run_agent()
