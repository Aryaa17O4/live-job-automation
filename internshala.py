"""
agents/api_scrapers/internshala.py  — Workflow 1
Internshala via internshala PyPI library  →  Google Sheets
pip install internshala
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import keyword_match
from core.sheets_logger import log_jobs

PLATFORM = "Internshala"

# Search terms to iterate over
SEARCH_TERMS = [
    "python", "django", "react", "node js",
    "machine learning", "data science", "web development",
    "backend", "full stack", "software development"
]


def run():
    try:
        from internshala import Internshala
    except ImportError:
        print("[Internshala] 'internshala' package not installed. Run: pip install internshala")
        return

    print(f"[{PLATFORM}] Fetching internships...")
    client = Internshala()
    seen_urls = set()
    jobs = []

    for term in SEARCH_TERMS:
        try:
            results = client.search(term)
            for item in results:
                url = getattr(item, "url", "") or str(item.get("url", ""))
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                title = getattr(item, "title", "") or item.get("title", "Internship")
                company = getattr(item, "company", "") or item.get("company_name", "Unknown")
                location = getattr(item, "location", "") or item.get("location", "India")

                if not keyword_match(f"{title} {term}"):
                    continue
                jobs.append({
                    "platform": PLATFORM,
                    "title": title,
                    "company": company,
                    "location": location,
                    "url": url or "https://internshala.com",
                    "status": "Scraped",
                })
        except Exception as e:
            print(f"[{PLATFORM}] Error for term '{term}': {e}")

    print(f"[{PLATFORM}] Matched {len(jobs)} internships.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
