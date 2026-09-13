"""
agents/api_scrapers/rss_feeds.py  — Workflow 1
All RSS-based platforms → Google Sheets

Platforms:
  4. We Work Remotely
  5. Jobspresso
  6. Working Nomads
  7. GitHub Jobs (via RSS mirror)
  8. Stack Overflow Jobs
  9. Dev.to Jobs
 13. Foundit / Monster India
 14. Indeed
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import parse_rss, keyword_match
from core.sheets_logger import log_jobs

FEEDS = [
    {
        "platform": "We Work Remotely",
        "url": "https://weworkremotely.com/remote-jobs.rss",
    },
    {
        "platform": "Jobspresso",
        "url": "https://jobspresso.co/feed/",
    },
    {
        "platform": "Working Nomads",
        "url": "https://www.workingnomads.com/jobs?category=development&format=rss",
    },
    {
        "platform": "GitHub Jobs",
        "url": "https://github.com/about/jobs.atom",
    },
    {
        "platform": "Stack Overflow",
        "url": "https://stackoverflow.com/jobs/feed",
    },
    {
        "platform": "Dev.to Jobs",
        "url": "https://dev.to/feed/tag/hiring",
    },
    {
        "platform": "Foundit",
        "url": "https://www.foundit.in/rss/jobs",
    },
    {
        "platform": "Indeed",
        "url": "https://in.indeed.com/rss?q=software+developer&l=India",
    },
]


def _parse_rss_job(entry: dict, platform: str) -> dict | None:
    """Normalize a raw RSS entry into our job schema."""
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    if not keyword_match(f"{title} {summary}"):
        return None
    # Try to extract company from title (common RSS pattern: "Role @ Company")
    company = "Unknown"
    if " at " in title:
        company = title.split(" at ")[-1].strip()
    elif " @ " in title:
        company = title.split(" @ ")[-1].strip()
    return {
        "platform": platform,
        "title": title.split(" at ")[0].split(" @ ")[0].strip(),
        "company": company,
        "location": "Remote",
        "url": entry.get("link", ""),
        "status": "Scraped",
    }


def run():
    for feed in FEEDS:
        platform = feed["platform"]
        print(f"[{platform}] Parsing RSS feed...")
        entries = parse_rss(feed["url"])
        jobs = []
        for e in entries:
            job = _parse_rss_job(e, platform)
            if job:
                jobs.append(job)
        print(f"[{platform}] Matched {len(jobs)} jobs.")
        log_jobs(jobs)


if __name__ == "__main__":
    run()
