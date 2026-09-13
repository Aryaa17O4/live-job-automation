"""
agents/email_pass/cutshort.py  — Workflow 2
Cutshort.io  →  email/password login  →  auto apply  →  Google Sheets
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import keyword_match
from agents.email_pass.base_agent import BaseEmailPassAgent
from playwright.sync_api import Page


class CutshortAgent(BaseEmailPassAgent):
    platform = "Cutshort"
    env_prefix = "CUTSHORT"
    base_url = "https://cutshort.io"

    def login(self, page: Page) -> bool:
        page.goto(f"{self.base_url}/login")
        page.wait_for_selector("input[type='email']", timeout=15000)
        page.fill("input[type='email']", self.email)
        page.fill("input[type='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/dashboard**", timeout=15000)
            return True
        except Exception:
            return False

    def search_jobs(self, page: Page) -> list[dict]:
        from core.utils import KEYWORDS
        page.goto(f"{self.base_url}/jobs")
        self._wait(2)
        jobs = []
        cards = page.query_selector_all("div[data-testid='job-card']")
        for card in cards:
            title = card.query_selector("h2,h3,.job-title")
            company = card.query_selector(".company-name,.employer")
            location = card.query_selector(".location")
            link = card.query_selector("a")
            t = title.inner_text() if title else ""
            c = company.inner_text() if company else "Unknown"
            l = location.inner_text() if location else "India"
            href = link.get_attribute("href") if link else ""
            if keyword_match(t):
                jobs.append({
                    "platform": self.platform,
                    "title": t,
                    "company": c,
                    "location": l,
                    "url": href if href.startswith("http") else self.base_url + href,
                })
        return jobs

    def apply_to_job(self, page: Page, job: dict) -> bool:
        page.goto(job["url"])
        self._wait(2)
        apply_btn = page.query_selector("button:has-text('Apply'), a:has-text('Apply now')")
        if not apply_btn:
            return False
        apply_btn.click()
        self._wait(2)
        # Submit any quick-apply modal
        submit = page.query_selector("button:has-text('Submit'), button[type='submit']")
        if submit:
            submit.click()
            self._wait(2)
            return True
        return False


def run():
    agent = CutshortAgent()
    agent.run()


if __name__ == "__main__":
    run()
