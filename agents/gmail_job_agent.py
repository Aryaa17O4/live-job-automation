import os, re, json, html
from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as SACredentials
from googleapiclient.discovery import build

GMAIL_TOKEN_1_JSON = os.getenv("GMAIL_TOKEN_1_JSON")
GMAIL_TOKEN_2_JSON = os.getenv("GMAIL_TOKEN_2_JSON")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SHEET_SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

HEADERS = ["Date","Platform","Job Title","Company","Location","Stipend / Salary",
           "Duration","Application Deadline","Job URL","Email Subject","Email Sender",
           "Gmail Message ID","Account","Full Job Description","Status"]

PLATFORMS = {
    "internshala": ["internshala.com"], "linkedin": ["linkedin.com"],
    "naukri": ["naukri.com"], "indeed": ["indeed.com"],
    "wellfound": ["wellfound.com", "angel.co"], "cutshort": ["cutshort.io"],
    "hirist": ["hirist.tech", "hirist.com"], "foundit": ["foundit.in"],
    "unstop": ["unstop.com"], "yc jobs": ["ycombinator.com/jobs"],
    "remote ok": ["remoteok.com"], "remotive": ["remotive.com"],
    "himalayas": ["himalayas.app"], "simplify jobs": ["simplify.jobs"],
    "we work remotely": ["weworkremotely.com"],
}

JOB_WORDS = re.compile(
    r"\b(job|jobs|hiring|internship|intern|developer|engineer|"
    r"software|backend|frontend|data|machine learning|ai|career|"
    r"vacancy|opportunity|apply|opening|recruitment)\b", re.I)

URL_RE = re.compile(r'https?://[^\s<>"\']+', re.I)


def make_gmail_client(token_json_str):
    info = json.loads(token_json_str)
    creds = Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri=info.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=info.get("client_id"),
        client_secret=info.get("client_secret"),
        scopes=info.get("scopes", GMAIL_SCOPES),
    )
    return build("gmail", "v1", credentials=creds)


def detect_platform(url):
    for name, domains in PLATFORMS.items():
        for d in domains:
            if d in url:
                return name
    return "unknown"


def extract_urls(text):
    return list(set(URL_RE.findall(text or "")))


def pick_job_url(urls):
    for url in urls:
        for domains in PLATFORMS.values():
            for d in domains:
                if d in url:
                    return url
    for url in urls:
        if any(k in url for k in ["job", "intern", "career", "apply", "opening"]):
            return url
    return urls[0] if urls else ""


def get_body(msg):
    def _decode(data):
        import base64
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    payload = msg.get("payload", {})
    parts = payload.get("parts", [])
    if not parts:
        body_data = payload.get("body", {}).get("data", "")
        return html.unescape(BeautifulSoup(_decode(body_data), "html.parser").get_text(" ")) if body_data else ""

    text = ""
    for part in parts:
        mime = part.get("mimeType", "")
        data = part.get("body", {}).get("data", "")
        if not data:
            continue
        decoded = _decode(data)
        if "html" in mime:
            text += BeautifulSoup(decoded, "html.parser").get_text(" ")
        elif "text" in mime:
            text += decoded
    return html.unescape(text)


def fetch_page_text(url):
    try:
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:3000]
    except Exception:
        return ""


def fetch_jobs_from_account(service, account_label):
    jobs = []
    query = "newer_than:7d (job OR internship OR hiring OR developer OR engineer OR career)"
    try:
        result = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        messages = result.get("messages", [])
    except Exception as e:
        print(f"[{account_label}] Gmail fetch error: {e}")
        return jobs

    for m in messages:
        try:
            msg = service.users().messages().get(userId="me", id=m["id"], format="full").execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "")
            sender = headers.get("From", "")
            date_str = headers.get("Date", "")
            body = get_body(msg)

            if not JOB_WORDS.search(subject + " " + body[:500]):
                continue

            urls = extract_urls(body)
            if not urls:
                continue

            job_url = pick_job_url(urls)
            platform = detect_platform(job_url)
            page_text = fetch_page_text(job_url)

            jobs.append({
                "date": date_str,
                "platform": platform,
                "title": "",
                "company": "",
                "location": "",
                "stipend": "",
                "duration": "",
                "deadline": "",
                "job_url": job_url,
                "subject": subject,
                "sender": sender,
                "msg_id": m["id"],
                "account": account_label,
                "description": page_text[:1000],
                "status": "New",
            })
            print(f"[{account_label}] Found: {subject[:60]}")
        except Exception as e:
            print(f"[{account_label}] Error processing message: {e}")
            continue

    return jobs


def write_to_sheet(jobs):
    if not GOOGLE_CREDENTIALS or not GOOGLE_SHEET_ID:
        print("Missing sheet credentials — skipping sheet write.")
        return

    sa_info = json.loads(GOOGLE_CREDENTIALS)
    creds = SACredentials.from_service_account_info(sa_info, scopes=SHEET_SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(GOOGLE_SHEET_ID)

    try:
        ws = sh.worksheet("Gmail Jobs")
    except Exception:
        ws = sh.add_worksheet(title="Gmail Jobs", rows=1000, cols=20)
        ws.append_row(HEADERS)

    existing = ws.col_values(10)  # Gmail Message ID column (index 12 = col 12, 0-based col 9)
    existing_ids = set(existing[1:])

    added = 0
    for job in jobs:
        if job["msg_id"] in existing_ids:
            continue
        ws.append_row([
            job["date"], job["platform"], job["title"], job["company"],
            job["location"], job["stipend"], job["duration"], job["deadline"],
            job["job_url"], job["subject"], job["sender"], job["msg_id"],
            job["account"], job["description"], job["status"],
        ])
        existing_ids.add(job["msg_id"])
        added += 1

    print(f"Sheet updated: {added} new jobs added.")


def main():
    all_jobs = []

    if GMAIL_TOKEN_1_JSON:
        print("Processing Account 1...")
        svc = make_gmail_client(GMAIL_TOKEN_1_JSON)
        all_jobs += fetch_jobs_from_account(svc, "account_1")
    else:
        print("GMAIL_TOKEN_1_JSON not set — skipping account 1.")

    if GMAIL_TOKEN_2_JSON:
        print("Processing Account 2...")
        svc = make_gmail_client(GMAIL_TOKEN_2_JSON)
        all_jobs += fetch_jobs_from_account(svc, "account_2")
    else:
        print("GMAIL_TOKEN_2_JSON not set — skipping account 2.")

    print(f"Total jobs found: {len(all_jobs)}")

    with open("gmail_jobs.json", "w") as f:
        json.dump(all_jobs, f, indent=2)
    print("Saved gmail_jobs.json")

    write_to_sheet(all_jobs)


if __name__ == "__main__":
    main()
