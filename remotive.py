"""
agents/api_scrapers/remotive.py  — Workflow 1
Remotive public API  →  Google Sheets
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

API_URL = "https://remotive.com/api/remote-jobs"
PLATFORM = "Remotive"


def run():
    print(f"[{PLATFORM}] Fetching jobs...")
    r = safe_get(API_URL)
    if not r:
        print(f"[{PLATFORM}] Failed to fetch.")
        return

    data = r.json().get("jobs", [])
    jobs = []
    for item in data:
        title = item.get("title", "")
        company = item.get("company_name", "Unknown")
        tags = " ".join(item.get("tags", []))
        category = item.get("category", "")
        if not keyword_match(f"{title} {tags} {category}"):
            continue
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": item.get("candidate_required_location", "Remote"),
            "url": item.get("url", ""),
            "status": "Scraped",
        })
    print(f"[{PLATFORM}] Matched {len(jobs)} jobs.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
