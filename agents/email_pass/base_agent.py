"""
agents/email_pass/base_agent.py  — Workflow 2
Abstract base for all email/password Playwright agents.
Subclasses implement: login(), search_jobs(), apply_to_job()
"""
import os
import time
from abc import ABC, abstractmethod
from playwright.sync_api import sync_playwright, Page, Browser


class BaseEmailPassAgent(ABC):
    """
    Base class for email/password login agents.

    Env vars expected per agent (prefix = platform slug, e.g. CUTSHORT):
        <PREFIX>_EMAIL
        <PREFIX>_PASSWORD
    """

    platform: str = "Unknown"
    env_prefix: str = ""
    base_url: str = ""

    def __init__(self):
        prefix = self.env_prefix or self.platform.upper().replace(" ", "_").replace(".", "")
        self.email = os.environ.get(f"{prefix}_EMAIL", "")
        self.password = os.environ.get(f"{prefix}_PASSWORD", "")
        if not self.email or not self.password:
            raise EnvironmentError(
                f"[{self.platform}] Missing env vars: {prefix}_EMAIL / {prefix}_PASSWORD"
            )

    # ── Playwright helpers ─────────────────────────────────────────────────

    def _launch(self) -> tuple[Browser, Page]:
        self._pw = sync_playwright().start()
        browser = self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                       "Chrome/124.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()
        page.set_default_timeout(30_000)
        return browser, page

    def _close(self, browser: Browser):
        try:
            browser.close()
            self._pw.stop()
        except Exception:
            pass

    def _wait(self, seconds: float = 2.0):
        time.sleep(seconds)

    # ── Interface ──────────────────────────────────────────────────────────

    @abstractmethod
    def login(self, page: Page) -> bool:
        """Navigate to login page, fill credentials, submit. Return True on success."""

    @abstractmethod
    def search_jobs(self, page: Page) -> list[dict]:
        """After login, search for matching jobs. Return list of job dicts."""

    @abstractmethod
    def apply_to_job(self, page: Page, job: dict) -> bool:
        """Navigate to job and apply. Return True on success."""

    # ── Orchestration ──────────────────────────────────────────────────────

    def run(self) -> list[dict]:
        """Full run: login → search → apply → return results."""
        from core.sheets_logger import log_jobs

        browser, page = self._launch()
        applied = []
        try:
            if not self.login(page):
                print(f"[{self.platform}] Login failed.")
                return []
            self._wait(2)
            jobs = self.search_jobs(page)
            print(f"[{self.platform}] Found {len(jobs)} matching jobs.")
            for job in jobs:
                try:
                    success = self.apply_to_job(page, job)
                    job["status"] = "Applied" if success else "Failed"
                    applied.append(job)
                    self._wait(3)
                except Exception as e:
                    print(f"[{self.platform}] Apply error for '{job.get('title')}': {e}")
                    job["status"] = "Error"
                    applied.append(job)
        finally:
            self._close(browser)

        log_jobs(applied)
        return applied
