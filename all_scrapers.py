"""
agents/scrape_only/all_scrapers.py  — Workflow 3
Scrape-only job logging  →  Google Sheets (Status = "Scraped / Review")

Platforms:
  YC Work at Startup, NextLeap, Techstars, a16z, Sequoia, Antler, Seedcamp,
  500 Global, Product Hunt Jobs, Crunchbase Jobs, AngelCo,
  Naukri Campus, Times Jobs, Shine.com, Freshersworld
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

import requests
from bs4 import BeautifulSoup
from core.utils import safe_get, keyword_match, KEYWORDS
from core.sheets_logger import log_jobs

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _soup(url: str) -> BeautifulSoup | None:
    r = safe_get(url, headers=HEADERS)
    if not r:
        return None
    return BeautifulSoup(r.text, "html.parser")


def _make_job(platform, title, company, location, url):
    return {
        "platform": platform,
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "status": "Scraped / Review",
    }


# ─────────────────────────────────────────────────────────────────────────────
# YC Work at a Startup
# ─────────────────────────────────────────────────────────────────────────────
def scrape_yc():
    PLATFORM = "YC Work at Startup"
    print(f"[{PLATFORM}] Scraping...")
    API = "https://www.workatastartup.com/jobs.json"
    r = safe_get(API, headers=HEADERS)
    if not r:
        return
    jobs = []
    for item in r.json():
        title = item.get("role", "")
        company = item.get("company", {}).get("name", "Unknown")
        if not keyword_match(f"{title} {' '.join(item.get('skills', []))}"):
            continue
        jobs.append(_make_job(PLATFORM, title, company,
                              item.get("remote_ok") and "Remote" or "US",
                              f"https://www.workatastartup.com/jobs/{item.get('id','')}"))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# NextLeap
# ─────────────────────────────────────────────────────────────────────────────
def scrape_nextleap():
    PLATFORM = "NextLeap"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://nextleap.app/jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-card, .opportunity-card, article"):
        title_el = card.select_one("h2,h3,.title")
        company_el = card.select_one(".company,.org")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        company = company_el.get_text(strip=True) if company_el else "Unknown"
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title, company, "India",
                              href if href.startswith("http") else "https://nextleap.app" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Techstars Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_techstars():
    PLATFORM = "Techstars Jobs"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://jobs.techstars.com/jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-listing, .opening"):
        title_el = card.select_one("h2,h3,.job-title")
        company_el = card.select_one(".company,.employer")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              "Remote", href if href.startswith("http") else "https://jobs.techstars.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# a16z Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_a16z():
    PLATFORM = "a16z Jobs"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://a16z.com/portfolio/#portfolio-jobs")
    if not soup:
        # fallback: Greenhouse-hosted a16z board
        soup = _soup("https://jobs.a16z.com/jobs")
    if not soup:
        return
    jobs = []
    for el in soup.select("a[href*='job'], a[href*='opening']"):
        title = el.get_text(strip=True)
        href = el.get("href", "")
        if not keyword_match(title) or not title:
            continue
        jobs.append(_make_job(PLATFORM, title, "a16z Portfolio", "Remote",
                              href if href.startswith("http") else "https://a16z.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Sequoia Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_sequoia():
    PLATFORM = "Sequoia Jobs"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://www.sequoiacap.com/jobs/")
    if not soup:
        return
    jobs = []
    for el in soup.select("a[href*='job'], .job-listing"):
        title_el = el.select_one("h2,h3,.title") or el
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = el.get("href", "") if el.name == "a" else (el.select_one("a") or {}).get("href", "")
        jobs.append(_make_job(PLATFORM, title, "Sequoia Portfolio", "Remote",
                              href if href.startswith("http") else "https://www.sequoiacap.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Antler Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_antler():
    PLATFORM = "Antler"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://www.antler.co/jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-card, .position-card, article"):
        title_el = card.select_one("h2,h3,.title")
        company_el = card.select_one(".company")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Antler Portfolio",
                              "Remote", href if href.startswith("http") else "https://www.antler.co" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Seedcamp Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_seedcamp():
    PLATFORM = "Seedcamp"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://seedcamp.com/jobs/")
    if not soup:
        return
    jobs = []
    for el in soup.select("a[href*='job'], .job"):
        title = el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = el.get("href", "")
        jobs.append(_make_job(PLATFORM, title, "Seedcamp Portfolio", "Remote",
                              href if href.startswith("http") else "https://seedcamp.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# 500 Global Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_500global():
    PLATFORM = "500 Global"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://500.co/jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-card, .opening, article"):
        title_el = card.select_one("h2,h3,.title")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title, "500 Global Portfolio", "Remote",
                              href if href.startswith("http") else "https://500.co" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Product Hunt Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_producthunt():
    PLATFORM = "Product Hunt Jobs"
    print(f"[{PLATFORM}] Scraping...")
    r = safe_get("https://www.producthunt.com/jobs.json", headers=HEADERS)
    if not r:
        return
    jobs = []
    try:
        data = r.json() if isinstance(r.json(), list) else r.json().get("jobs", [])
    except Exception:
        return
    for item in data:
        title = item.get("title", item.get("name", ""))
        company = item.get("company", {}).get("name", "Unknown") if isinstance(item.get("company"), dict) else item.get("company", "Unknown")
        if not keyword_match(f"{title} {item.get('tags', '')}"):
            continue
        jobs.append(_make_job(PLATFORM, title, company, "Remote",
                              item.get("url", "https://www.producthunt.com/jobs")))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Crunchbase Jobs (via public iframe search)
# ─────────────────────────────────────────────────────────────────────────────
def scrape_crunchbase():
    PLATFORM = "Crunchbase Jobs"
    print(f"[{PLATFORM}] Scraping (limited public data)...")
    # Crunchbase jobs are behind auth; we scrape the public job board index
    soup = _soup("https://www.crunchbase.com/discover/jobs")
    if not soup:
        return
    jobs = []
    for el in soup.select("a[href*='/job/']"):
        title = el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = el.get("href", "")
        jobs.append(_make_job(PLATFORM, title, "Unknown", "Remote",
                              href if href.startswith("http") else "https://www.crunchbase.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# AngelCo (angel.co portfolio job board)
# ─────────────────────────────────────────────────────────────────────────────
def scrape_angelco():
    PLATFORM = "AngelCo"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://angel.co/jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job_listing,.startup-job"):
        title_el = card.select_one(".title,h2,h3")
        company_el = card.select_one(".company,.startup-link")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              "Remote", href if href.startswith("http") else "https://angel.co" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Naukri Campus
# ─────────────────────────────────────────────────────────────────────────────
def scrape_naukri_campus():
    PLATFORM = "Naukri Campus"
    print(f"[{PLATFORM}] Scraping...")
    kw = "+".join(KEYWORDS[:3]) if KEYWORDS else "software+developer"
    soup = _soup(f"https://campus.naukri.com/jobs-in-india/{kw}-jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".jobTuple, article.jobTupleHeader"):
        title_el = card.select_one(".title, a.title")
        company_el = card.select_one(".companyInfo span.company-name, .comp-dtls-wrap")
        loc_el = card.select_one(".loc, .location")
        link_el = card.select_one("a.title, a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              loc_el.get_text(strip=True) if loc_el else "India",
                              href if href.startswith("http") else "https://campus.naukri.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Times Jobs
# ─────────────────────────────────────────────────────────────────────────────
def scrape_timesjobs():
    PLATFORM = "Times Jobs"
    print(f"[{PLATFORM}] Scraping...")
    kw = "%20".join(KEYWORDS[:2]) if KEYWORDS else "software+developer"
    soup = _soup(f"https://www.timesjobs.com/candidate/job-search.html?searchType=personalizedSearch&from=submit&txtKeywords={kw}&txtLocation=india")
    if not soup:
        return
    jobs = []
    for card in soup.select("li.clearfix.job-bx.wht-shd-bx"):
        title_el = card.select_one("h2 a")
        company_el = card.select_one("h3.joblist-comp-name")
        loc_el = card.select_one("ul.top-jd-dtl li")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = title_el.get("href", "")
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              loc_el.get_text(strip=True) if loc_el else "India",
                              href if href.startswith("http") else "https://www.timesjobs.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Shine.com
# ─────────────────────────────────────────────────────────────────────────────
def scrape_shine():
    PLATFORM = "Shine.com"
    print(f"[{PLATFORM}] Scraping...")
    kw = "-".join(KEYWORDS[:2]) if KEYWORDS else "software-developer"
    soup = _soup(f"https://www.shine.com/job-search/{kw}-jobs")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-listing, .jl-card"):
        title_el = card.select_one(".jl-title a, h2 a")
        company_el = card.select_one(".jl-company, .company")
        loc_el = card.select_one(".jl-location, .location")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = title_el.get("href", "")
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              loc_el.get_text(strip=True) if loc_el else "India",
                              href if href.startswith("http") else "https://www.shine.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Freshersworld
# ─────────────────────────────────────────────────────────────────────────────
def scrape_freshersworld():
    PLATFORM = "Freshersworld"
    print(f"[{PLATFORM}] Scraping...")
    soup = _soup("https://www.freshersworld.com/jobs/freshers-jobs-for-computer-science-engineers")
    if not soup:
        return
    jobs = []
    for card in soup.select(".job-container, .listing-item"):
        title_el = card.select_one(".job-title, h2 a, h3 a")
        company_el = card.select_one(".company-name, .employer")
        loc_el = card.select_one(".location")
        link_el = card.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not keyword_match(title):
            continue
        href = link_el.get("href", "") if link_el else ""
        jobs.append(_make_job(PLATFORM, title,
                              company_el.get_text(strip=True) if company_el else "Unknown",
                              loc_el.get_text(strip=True) if loc_el else "India",
                              href if href.startswith("http") else "https://www.freshersworld.com" + href))
    print(f"[{PLATFORM}] {len(jobs)} jobs.")
    log_jobs(jobs)


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

ALL_SCRAPERS = [
    scrape_yc,
    scrape_nextleap,
    scrape_techstars,
    scrape_a16z,
    scrape_sequoia,
    scrape_antler,
    scrape_seedcamp,
    scrape_500global,
    scrape_producthunt,
    scrape_crunchbase,
    scrape_angelco,
    scrape_naukri_campus,
    scrape_timesjobs,
    scrape_shine,
    scrape_freshersworld,
]


def run_all():
    for scraper in ALL_SCRAPERS:
        try:
            scraper()
        except Exception as e:
            print(f"[ERROR] {scraper.__name__}: {e}")


if __name__ == "__main__":
    run_all()
