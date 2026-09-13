"""
agents/api_scrapers/remoteok.py  — Workflow 1
Remote OK public JSON API  →  Google Sheets
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

API_URL = "https://remoteok.com/api"
PLATFORM = "Remote OK"


def run():
    print(f"[{PLATFORM}] Fetching jobs...")
    r = safe_get(API_URL, headers={"User-Agent": "job-agent/1.0"})
    if not r:
        print(f"[{PLATFORM}] Failed to fetch.")
        return

    data = r.json()
    jobs = []
    for item in data:
        if not isinstance(item, dict) or "slug" not in item:
            continue
        title = item.get("position", "")
        company = item.get("company", "Unknown")
        tags = " ".join(item.get("tags", []))
        if not keyword_match(f"{title} {tags}"):
            continue
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": item.get("location", "Remote"),
            "url": f"https://remoteok.com/remote-jobs/{item.get('slug', '')}",
            "status": "Scraped",
        })
    print(f"[{PLATFORM}] Matched {len(jobs)} jobs.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
