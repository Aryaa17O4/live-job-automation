"""
agents/api_scrapers/aicte.py  — Workflow 1
AICTE Internship Portal  →  Google Sheets
Uses AICTE's public REST API for internship listings.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

PLATFORM = "AICTE Portal"
API_URL = "https://internship.aicte-india.org/api/internships"


def run():
    print(f"[{PLATFORM}] Fetching internships...")
    params = {"page": 1, "limit": 100, "status": "active"}
    r = safe_get(API_URL, params=params)
    if not r:
        print(f"[{PLATFORM}] Failed to fetch.")
        return

    try:
        data = r.json()
        listings = data if isinstance(data, list) else data.get("data", data.get("internships", []))
    except Exception:
        print(f"[{PLATFORM}] JSON parse error.")
        return

    jobs = []
    for item in listings:
        title = item.get("title", item.get("internshipTitle", "Internship"))
        company = item.get("company", item.get("organizationName", "Unknown"))
        location = item.get("location", item.get("city", "India"))
        url = item.get("url", item.get("applyLink", "https://internship.aicte-india.org"))
        if not keyword_match(f"{title} {item.get('skills', '')}"):
            continue
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": location,
            "url": url,
            "status": "Scraped",
        })
    print(f"[{PLATFORM}] Matched {len(jobs)} internships.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
