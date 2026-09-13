"""
agents/api_scrapers/hn_hiring.py  — Workflow 1
Hacker News "Who is Hiring?" monthly thread  →  Google Sheets
Uses HN Algolia API to find current month's thread.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import datetime
from core.utils import safe_get, keyword_match
from core.sheets_logger import log_jobs

PLATFORM = "HN Who's Hiring"
ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"
ITEM_API = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def _find_thread_id() -> int | None:
    """Find this month's 'Ask HN: Who is hiring?' thread ID."""
    month = datetime.utcnow().strftime("%B %Y")
    params = {
        "query": f"Ask HN: Who is hiring? ({month})",
        "tags": "story,ask_hn",
        "hitsPerPage": 5,
    }
    r = safe_get(ALGOLIA_SEARCH, params=params)
    if not r:
        return None
    hits = r.json().get("hits", [])
    for h in hits:
        if "who is hiring" in h.get("title", "").lower():
            return h.get("objectID")
    return None


def _get_comments(thread_id: int) -> list[str]:
    """Return top-level comment texts from the thread."""
    r = safe_get(ITEM_API.format(thread_id))
    if not r:
        return []
    kids = r.json().get("kids", [])[:200]  # top 200 comments
    texts = []
    for kid in kids:
        cr = safe_get(ITEM_API.format(kid))
        if cr:
            text = cr.json().get("text", "")
            if text:
                texts.append(text)
    return texts


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()


def run():
    print(f"[{PLATFORM}] Finding monthly thread...")
    thread_id = _find_thread_id()
    if not thread_id:
        print(f"[{PLATFORM}] Thread not found.")
        return

    print(f"[{PLATFORM}] Thread ID: {thread_id}. Fetching comments...")
    comments = _get_comments(int(thread_id))
    jobs = []
    for text in comments:
        clean = _strip_html(text)
        if not keyword_match(clean):
            continue
        # First line is usually: "Company | Role | Location | ..."
        lines = [l.strip() for l in clean.split("\n") if l.strip()]
        if not lines:
            continue
        parts = lines[0].split("|")
        company = parts[0].strip() if parts else "Unknown"
        title = parts[1].strip() if len(parts) > 1 else "Software Engineer"
        location = parts[2].strip() if len(parts) > 2 else "Remote"
        jobs.append({
            "platform": PLATFORM,
            "title": title,
            "company": company,
            "location": location,
            "url": f"https://news.ycombinator.com/item?id={thread_id}",
            "status": "Scraped",
        })
    print(f"[{PLATFORM}] Matched {len(jobs)} jobs.")
    log_jobs(jobs)


if __name__ == "__main__":
    run()
