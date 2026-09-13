"""
agents/email_pass/all_agents.py  — Workflow 2
All email/password login agents except Cutshort (which has its own file).

Each agent inherits BaseEmailPassAgent and implements:
  login(), search_jobs(), apply_to_job()

Platforms: Hirist, Instahyre, Wellfound, Unstop, F6S, AngelList,
           Startup.jobs, VentureLoop, Dice, Built In, Lemon.io, Arc.dev,
           Contra, Toptal, Gun.io, Hired.com, Turing, Flexiple, PeoplePerHour
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.utils import keyword_match
from agents.email_pass.base_agent import BaseEmailPassAgent
from playwright.sync_api import Page


# ─── Helper: Generic quick-apply flow ────────────────────────────────────────

def generic_apply(page: Page, job: dict, base_url: str) -> bool:
    """Click the first Apply button, wait, click Submit if modal appears."""
    page.goto(job["url"])
    page.wait_for_load_state("networkidle", timeout=15000)
    for selector in [
        "button:has-text('Apply')", "a:has-text('Apply')",
        "button:has-text('Easy Apply')", "button:has-text('Quick Apply')"
    ]:
        btn = page.query_selector(selector)
        if btn:
            btn.click()
            page.wait_for_timeout(2000)
            for sub in ["button[type='submit']", "button:has-text('Submit')",
                        "button:has-text('Send application')"]:
                s = page.query_selector(sub)
                if s:
                    s.click()
                    return True
            return True
    return False


def generic_search(page: Page, jobs_url: str, platform: str,
                   card_sel: str, title_sel: str, company_sel: str,
                   loc_sel: str, link_sel: str, base_url: str) -> list[dict]:
    """Generic CSS-selector job list scraper."""
    page.goto(jobs_url)
    page.wait_for_load_state("networkidle", timeout=15000)
    jobs = []
    for card in page.query_selector_all(card_sel):
        def txt(sel):
            el = card.query_selector(sel)
            return el.inner_text().strip() if el else ""
        title = txt(title_sel)
        if not keyword_match(title):
            continue
        href = ""
        link_el = card.query_selector(link_sel)
        if link_el:
            href = link_el.get_attribute("href") or ""
        jobs.append({
            "platform": platform,
            "title": title,
            "company": txt(company_sel) or "Unknown",
            "location": txt(loc_sel) or "Remote",
            "url": href if href.startswith("http") else base_url + href,
        })
    return jobs


# ─── Agent Definitions ────────────────────────────────────────────────────────

class HiristAgent(BaseEmailPassAgent):
    platform = "Hirist"
    env_prefix = "HIRIST"
    base_url = "https://www.hirist.tech"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/jobs**", timeout=12000)
            return True
        except Exception:
            return "hirist.tech" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/it-jobs",
            self.platform, ".job-listing", ".job-title", ".company", ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class InstahyreAgent(BaseEmailPassAgent):
    platform = "Instahyre"
    env_prefix = "INSTAHYRE"
    base_url = "https://www.instahyre.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login/")
        page.fill("#id_email", self.email)
        page.fill("#id_password", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/opportunities**", timeout=12000)
            return True
        except Exception:
            return "instahyre" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/candidate/opportunities/",
            self.platform, ".opportunity-card", ".role-title", ".company-name",
            ".location", "a.opp-link", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class WellfoundAgent(BaseEmailPassAgent):
    platform = "Wellfound"
    env_prefix = "WELLFOUND"
    base_url = "https://wellfound.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='user[email]']", self.email)
        page.fill("input[name='user[password]']", self.password)
        page.click("input[type='submit']")
        try:
            page.wait_for_url("**/jobs**", timeout=12000)
            return True
        except Exception:
            return "wellfound" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, "[data-test='JobListing']", "[data-test='JobTitle']",
            "[data-test='StartupLink']", "[data-test='JobLocation']", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class UnstopAgent(BaseEmailPassAgent):
    platform = "Unstop"
    env_prefix = "UNSTOP"
    base_url = "https://unstop.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[type='email']", self.email)
        page.fill("input[type='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/dashboard**", timeout=12000)
            return True
        except Exception:
            return "unstop" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, ".opportunity-card", ".opp-title", ".org-name",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class F6SAgent(BaseEmailPassAgent):
    platform = "F6S"
    env_prefix = "F6S"
    base_url = "https://www.f6s.com"

    def login(self, page):
        page.goto(f"{self.base_url}/user/signin")
        page.fill("#email", self.email)
        page.fill("#password", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "f6s.com" in page.url and "signin" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, ".job-row", ".job-name", ".company-name",
            ".job-location", "a.job-link", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class AngelListAgent(BaseEmailPassAgent):
    platform = "AngelList"
    env_prefix = "ANGELLIST"
    base_url = "https://angel.co"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/jobs**", timeout=12000)
            return True
        except Exception:
            return "angel.co" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, ".job_listing", ".title", ".company",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class StartupJobsAgent(BaseEmailPassAgent):
    platform = "Startup.jobs"
    env_prefix = "STARTUPJOBS"
    base_url = "https://startup.jobs"

    def login(self, page):
        page.goto(f"{self.base_url}/sign_in")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("input[type='submit']")
        self._wait(3)
        return "startup.jobs" in page.url and "sign_in" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}",
            self.platform, ".job-listing", "h2.title", ".company-name",
            ".location", "a.job-link", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class VentureLoopAgent(BaseEmailPassAgent):
    platform = "VentureLoop"
    env_prefix = "VENTURELOOP"
    base_url = "https://www.ventureloop.com"

    def login(self, page):
        page.goto(f"{self.base_url}/ventureloop/login.php")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("input[type='submit']")
        self._wait(3)
        return "ventureloop" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/ventureloop/job_search.php?skill=python",
            self.platform, "tr.job_row", "td.jt a", "td.company",
            "td.location", "td.jt a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class DiceAgent(BaseEmailPassAgent):
    platform = "Dice"
    env_prefix = "DICE"
    base_url = "https://www.dice.com"

    def login(self, page):
        page.goto(f"{self.base_url}/dashboard/login")
        page.fill("#email", self.email)
        page.fill("#password", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/home**", timeout=12000)
            return True
        except Exception:
            return "dice.com" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs?q=python+developer",
            self.platform, "dhi-search-card", "a.card-title-link",
            "a.employer-name", "span.search-result-location", "a.card-title-link", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class BuiltInAgent(BaseEmailPassAgent):
    platform = "Built In"
    env_prefix = "BUILTIN"
    base_url = "https://builtin.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/profile**", timeout=12000)
            return True
        except Exception:
            return "builtin.com" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs/dev-engineering",
            self.platform, "article.job-listing", "h2.job-title", ".company-name",
            ".job-location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class LemonIOAgent(BaseEmailPassAgent):
    platform = "Lemon.io"
    env_prefix = "LEMONIO"
    base_url = "https://lemon.io"

    def login(self, page):
        page.goto(f"{self.base_url}/sign-in")
        page.fill("input[type='email']", self.email)
        page.fill("input[type='password']", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "lemon.io" in page.url and "sign-in" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, ".job-card", "h3.job-title", ".company",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class ArcDevAgent(BaseEmailPassAgent):
    platform = "Arc.dev"
    env_prefix = "ARCDEV"
    base_url = "https://arc.dev"

    def login(self, page):
        page.goto(f"{self.base_url}/remote-developer-jobs")
        # Arc.dev uses OAuth; fall back to email
        page.goto(f"{self.base_url}/candidates/sign_in")
        page.fill("input[name='candidate[email]']", self.email)
        page.fill("input[name='candidate[password]']", self.password)
        page.click("input[type='submit']")
        self._wait(3)
        return "arc.dev" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/remote-developer-jobs?technologies=python",
            self.platform, ".job-card", "h2.job-title", ".company-name",
            ".location", "a.job-link", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class ContraAgent(BaseEmailPassAgent):
    platform = "Contra"
    env_prefix = "CONTRA"
    base_url = "https://contra.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[type='email']", self.email)
        page.fill("input[type='password']", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "contra.com" in page.url and "login" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/opportunities",
            self.platform, "[data-testid='opportunity-card']",
            "[data-testid='opportunity-title']", "[data-testid='client-name']",
            "[data-testid='location']", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class ToptalAgent(BaseEmailPassAgent):
    platform = "Toptal"
    env_prefix = "TOPTAL"
    base_url = "https://www.toptal.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/developers**", timeout=12000)
            return True
        except Exception:
            return "toptal.com" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/developers/jobs",
            self.platform, ".job-listing", ".job-title", ".company",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class GunIOAgent(BaseEmailPassAgent):
    platform = "Gun.io"
    env_prefix = "GUNIO"
    base_url = "https://gun.io"

    def login(self, page):
        page.goto(f"{self.base_url}/accounts/login/")
        page.fill("#id_username", self.email)
        page.fill("#id_password", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "gun.io" in page.url and "login" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/find/",
            self.platform, ".job-card", ".job-title", ".company",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class HiredAgent(BaseEmailPassAgent):
    platform = "Hired.com"
    env_prefix = "HIRED"
    base_url = "https://hired.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/profile**", timeout=12000)
            return True
        except Exception:
            return "hired.com" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs",
            self.platform, ".JobListing", ".JobListing-title", ".JobListing-company",
            ".JobListing-location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class TuringAgent(BaseEmailPassAgent):
    platform = "Turing"
    env_prefix = "TURING"
    base_url = "https://www.turing.com"

    def login(self, page):
        page.goto(f"{self.base_url}/auth/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "turing.com" in page.url and "login" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/remote-developer-jobs",
            self.platform, ".job-card", ".job-title", ".company-name",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class FlexibleAgent(BaseEmailPassAgent):
    platform = "Flexiple"
    env_prefix = "FLEXIPLE"
    base_url = "https://flexiple.com"

    def login(self, page):
        page.goto(f"{self.base_url}/developers/login")
        page.fill("input[type='email']", self.email)
        page.fill("input[type='password']", self.password)
        page.click("button[type='submit']")
        self._wait(3)
        return "flexiple.com" in page.url and "login" not in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/hire",
            self.platform, ".job-card", "h3", ".company",
            ".location", "a", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


class PeoplePerHourAgent(BaseEmailPassAgent):
    platform = "PeoplePerHour"
    env_prefix = "PEOPLEPHOUR"
    base_url = "https://www.peopleperhour.com"

    def login(self, page):
        page.goto(f"{self.base_url}/login")
        page.fill("input[name='email']", self.email)
        page.fill("input[name='password']", self.password)
        page.click("button[type='submit']")
        try:
            page.wait_for_url("**/dashboard**", timeout=12000)
            return True
        except Exception:
            return "peopleperhour" in page.url

    def search_jobs(self, page):
        return generic_search(page, f"{self.base_url}/jobs/all?service=software-development",
            self.platform, ".joblist-item", ".item-title", ".item-buyer",
            ".location", "a.item-title", self.base_url)

    def apply_to_job(self, page, job):
        return generic_apply(page, job, self.base_url)


# ─── Registry ─────────────────────────────────────────────────────────────────

ALL_AGENTS = [
    HiristAgent,
    InstahyreAgent,
    WellfoundAgent,
    UnstopAgent,
    F6SAgent,
    AngelListAgent,
    StartupJobsAgent,
    VentureLoopAgent,
    DiceAgent,
    BuiltInAgent,
    LemonIOAgent,
    ArcDevAgent,
    ContraAgent,
    ToptalAgent,
    GunIOAgent,
    HiredAgent,
    TuringAgent,
    FlexibleAgent,
    PeoplePerHourAgent,
]


def run_all():
    for AgentClass in ALL_AGENTS:
        try:
            agent = AgentClass()
            agent.run()
        except EnvironmentError as e:
            print(f"[SKIP] {e}")
        except Exception as e:
            print(f"[ERROR] {AgentClass.platform}: {e}")


if __name__ == "__main__":
    run_all()
