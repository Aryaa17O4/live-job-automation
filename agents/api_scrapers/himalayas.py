"""
agents/api_scrapers/himalayas.py  — Workflow 1
Himalayas public API  →  Google Sheets
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

API_URL = "https://himalayas.app/jobs/api"
PLATFORM = "Himalayas"


def run():
    print(f"[{PLATFORM}] Fetching jobs...")
    r = safe_get(API_URL, params={"limit": 100})
    if not r:
        print(f"[{PLATFORM}] Failed to fetch.")
        return

    data = r.json().get("jobs", [])
    jobs = []
    for item in data:
        title = item.get("title", "")
        company = item.get("company", {}).get("name", "Unknown")
        skills = " ".join(item.get("requirements", {}).get("skills", []))
        if not keyword_match(f"{title} {skills}"):
            continue
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": item.get("locationRestrictions", ["Remote"])[0]
                        if item.get("locationRestrictions") else "Remote",
            "url": item.get("applicationLink", item.get("url", "")),
            "status": "Scraped",
        })
    print(f"[{PLATFORM}] Matched {len(jobs)} jobs.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
