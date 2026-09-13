"""
agents/api_scrapers/simplifyjobs.py  — Workflow 1
Simplify Jobs public API  →  Google Sheets
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

PLATFORM = "Simplify Jobs"
# Simplify exposes a public jobs JSON used by their frontend
API_URL = "https://simplify.jobs/api/jobs"


def run():
    print(f"[{PLATFORM}] Fetching jobs...")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://simplify.jobs/",
    }
    params = {"limit": 100, "page": 1}
    r = safe_get(API_URL, params=params, headers=headers)
    if not r:
        print(f"[{PLATFORM}] Failed to fetch.")
        return

    try:
        raw = r.json()
        listings = raw if isinstance(raw, list) else raw.get("jobs", raw.get("data", []))
    except Exception:
        print(f"[{PLATFORM}] JSON parse error.")
        return

    jobs = []
    for item in listings:
        title = item.get("title", item.get("role", ""))
        company = item.get("company", item.get("company_name", "Unknown"))
        location = item.get("location", "Remote")
        url = item.get("url", item.get("apply_url", item.get("link", "")))

        if not keyword_match(f"{title} {item.get('description', '')}"):
            continue
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "status": "Scraped",
        })

    print(f"[{PLATFORM}] Matched {len(jobs)} jobs.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
