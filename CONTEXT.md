# 🧠 Project Context — live-job-automation

## Goal
Hybrid automated job application system across 50 platforms in 3 workflows.
All results log to a single Google Sheet.

## Repo
https://github.com/Aryaa17O4/live-job-automation

## Architecture

live-job-automation/
├── core/
│   ├── sheets_logger.py # Shared Google Sheets logger (duplicate check included)
│   └── utils.py         # Keyword filter, RSS parser, safe HTTP
├── agents/
│   ├── api_scrapers/    # Workflow 1 — API & RSS (no login needed)
│   │   ├── remoteok.py
│   │   ├── remotive.py
│   │   ├── himalayas.py
│   │   ├── rss_feeds.py
│   │   ├── hn_hiring.py
│   │   ├── aicte.py
│   │   ├── internshala.py
│   │   └── simplifyjobs.py
│   ├── email_pass/      # Workflow 2 — Playwright email/password auto apply
│   │   ├── base_agent.py
│   │   ├── cutshort.py
│   │   └── all_agents.py
│   └── scrape_only/     # Workflow 3 — BeautifulSoup scrape, log for manual review
│       └── all_scrapers.py
└── .github/workflows/
    ├── workflow1_api_rss.yml
    ├── workflow2_email_pass.yml
    └── workflow3_scrape_only.yml

## 3 Workflows

### Workflow 1 — API/RSS Scrapers (15 platforms)
No login needed. Uses public APIs and RSS feeds.
Status logged: "Scraped"
Runs: Every 6 hours

Platforms:
1. Remote OK → remoteok.com/api
2. Remotive → remotive.com/api
3. Himalayas → himalayas.app/api
4. We Work Remotely → RSS
5. Jobspresso → RSS
6. Working Nomads → RSS
7. GitHub Jobs → RSS/Atom
8. Stack Overflow → RSS
9. Dev.to Jobs → RSS
10. HN Who's Hiring → Algolia API (monthly thread)
11. AICTE Portal → REST API
12. Internshala → PyPI library
13. Foundit/Monster → RSS
14. Indeed → RSS
15. Simplify Jobs → Public API

### Workflow 2 — Email/Password Auto Apply (20 platforms)
Uses Playwright headless browser with email+password login.
Status logged: "Applied" or "Failed"
Runs: Daily 3AM UTC

Platforms:
16. Cutshort
17. Hirist
18. Instahyre
19. Wellfound
20. Unstop
21. F6S
22. AngelList
23. Startup.jobs
24. VentureLoop
25. Dice
26. Built In
27. Lemon.io
28. Arc.dev
29. Contra
30. Toptal
31. Gun.io
32. Hired.com
33. Turing
34. Flexiple
35. PeoplePerHour

### Workflow 3 — Scrape-Only Logging (15 platforms)
BeautifulSoup scraping, logs for manual 30-min review bursts.
Status logged: "Scraped / Review"
Runs: Every 8 hours

Platforms:
36. YC Work at Startup
37. NextLeap
38. Techstars Jobs
39. a16z Jobs
40. Sequoia Jobs
41. Antler
42. Seedcamp
43. 500 Global
44. Product Hunt Jobs
45. Crunchbase Jobs
46. AngelCo
47. Naukri Campus
48. Times Jobs
49. Shine.com
50. Freshersworld

## Google Sheet Format
Headers: Date | Platform | Job Title | Company | Location | Status | Job URL
Duplicate check: Job Title + Company + Platform (case-insensitive)
Sheet name: "Jobs" (auto-created if missing)

## Tech Stack
- Python 3.11
- Playwright (Workflow 2 only)
- BeautifulSoup4 + requests (Workflow 3)
- feedparser (Workflow 1 RSS)
- gspread + google-auth (Google Sheets)
- GitHub Actions (scheduling)

## GitHub Secrets Required

### Always needed (all 3 workflows)
- GOOGLE_SERVICE_ACCOUNT_JSON — full GCP service account key JSON
- GOOGLE_SHEET_ID — Google Sheet ID from URL
- JOB_KEYWORDS — comma separated: python,django,react,backend,software intern
- LOCATION_FILTER — optional: india or blank for global

### Workflow 2 only (one pair per platform)
CUTSHORT_EMAIL / CUTSHORT_PASSWORD
HIRIST_EMAIL / HIRIST_PASSWORD
INSTAHYRE_EMAIL / INSTAHYRE_PASSWORD
WELLFOUND_EMAIL / WELLFOUND_PASSWORD
UNSTOP_EMAIL / UNSTOP_PASSWORD
F6S_EMAIL / F6S_PASSWORD
ANGELLIST_EMAIL / ANGELLIST_PASSWORD
STARTUPJOBS_EMAIL / STARTUPJOBS_PASSWORD
VENTURELOOP_EMAIL / VENTURELOOP_PASSWORD
DICE_EMAIL / DICE_PASSWORD
BUILTIN_EMAIL / BUILTIN_PASSWORD
LEMONIO_EMAIL / LEMONIO_PASSWORD
ARCDEV_EMAIL / ARCDEV_PASSWORD
CONTRA_EMAIL / CONTRA_PASSWORD
TOPTAL_EMAIL / TOPTAL_PASSWORD
GUNIO_EMAIL / GUNIO_PASSWORD
HIRED_EMAIL / HIRED_PASSWORD
TURING_EMAIL / TURING_PASSWORD
FLEXIPLE_EMAIL / FLEXIPLE_PASSWORD
PEOPLEPHOUR_EMAIL / PEOPLEPHOUR_PASSWORD

## Current Status
- All 50 platform agents written
- Folder structure fixed (core/, agents/, .github/workflows/)
- __init__.py files added
- All 3 GitHub Actions YML files ready
- NEXT STEP: Add GitHub Secrets → Google Sheet setup → Test run

## Next Steps
1. Add GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON secrets
2. Set up GCP Service Account + share Google Sheet with it
3. Add email/password secrets for Workflow 2 platforms
4. Manually trigger workflow_dispatch to test each workflow
5. Fix selector issues after first run (CSS selectors may need tuning per platform)

## Key Design Decisions
- No cookie-based sessions (expire too fast, bot detection)
- Email/password login via Playwright for Workflow 2
- Public APIs/RSS for Workflow 1 (zero auth needed)
- BeautifulSoup scraping for Workflow 3 (manual review before apply)
- Single sheets_logger.py used by ALL workflows
- continue-on-error: true in YML so one platform failure doesn't stop others
