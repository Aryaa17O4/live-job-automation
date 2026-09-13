"""
core/sheets_logger.py
─────────────────────
Central Google Sheets logger used by ALL three workflows.
Headers: Date | Platform | Job Title | Company | Location | Status | Job URL
Duplicate check: Job Title + Company + Platform
"""

import os
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

HEADERS = ["Date", "Platform", "Job Title", "Company", "Location", "Status", "Job URL"]


def _get_sheet():
    """Authenticate and return the target worksheet."""
    creds = Credentials.from_service_account_file(
        os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"], scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    wb = client.open_by_key(sheet_id)
    try:
        ws = wb.worksheet("Jobs")
    except gspread.WorksheetNotFound:
        ws = wb.add_worksheet(title="Jobs", rows="5000", cols="7")
        ws.append_row(HEADERS)
    return ws


def _existing_keys(ws):
    """Return a set of (job_title_lower, company_lower, platform_lower) tuples."""
    records = ws.get_all_records()
    return {
        (
            str(r.get("Job Title", "")).strip().lower(),
            str(r.get("Company", "")).strip().lower(),
            str(r.get("Platform", "")).strip().lower(),
        )
        for r in records
    }


def log_jobs(jobs: list[dict]) -> dict:
    """
    Log a list of job dicts to Google Sheets.

    Each dict must contain:
        platform, title, company, location, url
    Optional:
        status  (defaults to "Scraped")

    Returns:
        {"added": int, "skipped": int}
    """
    if not jobs:
        return {"added": 0, "skipped": 0}

    ws = _get_sheet()
    existing = _existing_keys(ws)
    rows_to_add = []
    skipped = 0

    for job in jobs:
        key = (
            job.get("title", "").strip().lower(),
            job.get("company", "").strip().lower(),
            job.get("platform", "").strip().lower(),
        )
        if key in existing:
            skipped += 1
            continue
        existing.add(key)  # prevent within-batch duplicates
        rows_to_add.append(
            [
                datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                job.get("platform", ""),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", "Remote"),
                job.get("status", "Scraped"),
                job.get("url", ""),
            ]
        )

    if rows_to_add:
        ws.append_rows(rows_to_add, value_input_option="USER_ENTERED")

    print(f"[SheetsLogger] Added: {len(rows_to_add)} | Skipped (dup): {skipped}")
    return {"added": len(rows_to_add), "skipped": skipped}
