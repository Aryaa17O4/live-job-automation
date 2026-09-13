import requests
from bs4 import BeautifulSoup
from core.sheets_logger import log_jobs
import os

def run():
    keywords = os.environ.get("JOB_KEYWORDS", "python,backend,software intern").split(",")
    results = []

    for keyword in keywords:
        keyword = keyword.strip()
        url = f"https://internshala.com/internships/keywords-{keyword.replace(' ', '-')}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

        try:
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            for card in soup.select(".individual_internship"):
                title_el = card.select_one(".profile")
                company_el = card.select_one(".company_name")
                location_el = card.select_one(".location_link")
                link_el = card.select_one("a.view_detail_button")

                title = title_el.get_text(strip=True) if title_el else ""
                company = company_el.get_text(strip=True) if company_el else ""
                location = location_el.get_text(strip=True) if location_el else "Remote"
                link = "https://internshala.com" + link_el["href"] if link_el else url

                if not title:
                    continue

                results.append({
                    "platform": "Internshala",
                    "title": title,
                    "company": company,
                    "location": location,
                    "status": "Scraped",
                    "url": link,
                })

        except Exception as e:
            print(f"[Internshala] Error for keyword '{keyword}': {e}")

    log_jobs(results)
    print(f"[Internshala] Logged {len(results)} jobs")

if __name__ == "__main__":
    run()
