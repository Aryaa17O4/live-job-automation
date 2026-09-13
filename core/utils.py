"""
core/utils.py
─────────────
Shared helpers: keyword filtering, safe HTTP requests, RSS parsing.
"""

import os
import time
import feedparser
import requests
from typing import Optional

KEYWORDS = [
    kw.strip().lower()
    for kw in os.environ.get(
        "JOB_KEYWORDS",
        "python,django,fastapi,react,node,backend,fullstack,software intern,developer intern",
    ).split(",")
    if kw.strip()
]

LOCATION_FILTER = os.environ.get("LOCATION_FILTER", "").lower()  # e.g. "india" or ""


def keyword_match(text: str) -> bool:
    """Return True if any keyword is found in text (case-insensitive)."""
    if not KEYWORDS:
        return True
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)


def location_match(location: str) -> bool:
    """Return True if location filter passes (empty filter = pass all)."""
    if not LOCATION_FILTER:
        return True
    return LOCATION_FILTER in location.lower()


def safe_get(url: str, params: Optional[dict] = None, headers: Optional[dict] = None,
             retries: int = 3, timeout: int = 20) -> Optional[requests.Response]:
    """Resilient GET with retry + backoff."""
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            print(f"[safe_get] Attempt {attempt+1} failed for {url}: {e}")
            time.sleep(2 ** attempt)
    return None


def parse_rss(url: str) -> list[dict]:
    """
    Parse an RSS/Atom feed and return a list of normalized dicts:
        title, link, summary, published
    """
    try:
        feed = feedparser.parse(url)
        entries = []
        for e in feed.entries:
            entries.append({
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "summary": e.get("summary", e.get("description", "")),
                "published": e.get("published", ""),
            })
        return entries
    except Exception as ex:
        print(f"[parse_rss] Failed to parse {url}: {ex}")
        return []
