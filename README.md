# 🤖 Job Agent v2 — Hybrid Automated Job Application System

Automated job scraping and application system across **50 platforms** in **3 distinct workflows**, all logging to a single Google Sheet.

---

## 🏗️ Architecture

```
job-agent-v2/
├── core/
│   ├── sheets_logger.py     # Shared Google Sheets logger (all 3 workflows)
│   └── utils.py             # Keyword filter, RSS parser, safe HTTP
├── agents/
│   ├── api_scrapers/        # Workflow 1 — API & RSS
│   │   ├── remoteok.py
│   │   ├── remotive.py
│   │   ├── himalayas.py
│   │   ├── rss_feeds.py     # WWR, Jobspresso, Working Nomads, GH Jobs, SO, Dev.to, Foundit, Indeed
│   │   ├── hn_hiring.py
│   │   ├── aicte.py
│   │   ├── internshala.py
│   │   └── simplifyjobs.py
│   ├── email_pass/          # Workflow 2 — Email/Password Auto Apply
│   │   ├── base_agent.py    # Abstract base class
│   │   ├── cutshort.py
│   │   └── all_agents.py    # 19 remaining platforms
│   └── scrape_only/         # Workflow 3 — Scrape & Log for Review
│       └── all_scrapers.py  # 15 platforms
└── .github/workflows/
    ├── workflow1_api_rss.yml
    ├── workflow2_email_pass.yml
    └── workflow3_scrape_only.yml
```

---

## 📋 Platform Map

### Workflow 1 — API / RSS Scrapers (15 platforms)
| # | Platform | Method | Frequency |
|---|----------|--------|-----------|
| 1 | Remote OK | Public JSON API | Every 6h |
| 2 | Remotive | Public JSON API | Every 6h |
| 3 | Himalayas | Public JSON API | Every 6h |
| 4 | We Work Remotely | RSS Feed | Every 6h |
| 5 | Jobspresso | RSS Feed | Every 6h |
| 6 | Working Nomads | RSS Feed | Every 6h |
| 7 | GitHub Jobs | RSS/Atom Feed | Every 6h |
| 8 | Stack Overflow | RSS Feed | Every 6h |
| 9 | Dev.to Jobs | RSS Feed | Every 6h |
| 10 | HN Who's Hiring | Algolia API + HN API | Every 6h |
| 11 | AICTE Portal | REST API | Every 6h |
| 12 | Internshala | PyPI library | Every 6h |
| 13 | Foundit/Monster | RSS Feed | Every 6h |
| 14 | Indeed | RSS Feed | Every 6h |
| 15 | Simplify Jobs | Public API | Every 6h |

### Workflow 2 — Email/Password Auto Apply (20 platforms)
| # | Platform | Status Logged |
|---|----------|---------------|
| 16 | Cutshort | Applied / Failed |
| 17 | Hirist | Applied / Failed |
| 18 | Instahyre | Applied / Failed |
| 19 | Wellfound | Applied / Failed |
| 20 | Unstop | Applied / Failed |
| 21 | F6S | Applied / Failed |
| 22 | AngelList | Applied / Failed |
| 23 | Startup.jobs | Applied / Failed |
| 24 | VentureLoop | Applied / Failed |
| 25 | Dice | Applied / Failed |
| 26 | Built In | Applied / Failed |
| 27 | Lemon.io | Applied / Failed |
| 28 | Arc.dev | Applied / Failed |
| 29 | Contra | Applied / Failed |
| 30 | Toptal | Applied / Failed |
| 31 | Gun.io | Applied / Failed |
| 32 | Hired.com | Applied / Failed |
| 33 | Turing | Applied / Failed |
| 34 | Flexiple | Applied / Failed |
| 35 | PeoplePerHour | Applied / Failed |

### Workflow 3 — Scrape-Only Logging (15 platforms)
| # | Platform | Status Logged |
|---|----------|---------------|
| 36 | YC Work at Startup | Scraped / Review |
| 37 | NextLeap | Scraped / Review |
| 38 | Techstars Jobs | Scraped / Review |
| 39 | a16z Jobs | Scraped / Review |
| 40 | Sequoia Jobs | Scraped / Review |
| 41 | Antler | Scraped / Review |
| 42 | Seedcamp | Scraped / Review |
| 43 | 500 Global | Scraped / Review |
| 44 | Product Hunt Jobs | Scraped / Review |
| 45 | Crunchbase Jobs | Scraped / Review |
| 46 | AngelCo | Scraped / Review |
| 47 | Naukri Campus | Scraped / Review |
| 48 | Times Jobs | Scraped / Review |
| 49 | Shine.com | Scraped / Review |
| 50 | Freshersworld | Scraped / Review |

---

## 🔐 GitHub Secrets Required

### Always Required
| Secret | Description |
|--------|-------------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON content of your GCP service account key |
| `GOOGLE_SHEET_ID` | Google Sheet ID (from URL) |
| `JOB_KEYWORDS` | Comma-separated: `python,django,react,backend` |
| `LOCATION_FILTER` | Optional: `india` or leave blank for global |

### Workflow 2 — One pair per platform
`CUTSHORT_EMAIL` / `CUTSHORT_PASSWORD`  
`HIRIST_EMAIL` / `HIRIST_PASSWORD`  
`INSTAHYRE_EMAIL` / `INSTAHYRE_PASSWORD`  
`WELLFOUND_EMAIL` / `WELLFOUND_PASSWORD`  
`UNSTOP_EMAIL` / `UNSTOP_PASSWORD`  
`F6S_EMAIL` / `F6S_PASSWORD`  
`ANGELLIST_EMAIL` / `ANGELLIST_PASSWORD`  
`STARTUPJOBS_EMAIL` / `STARTUPJOBS_PASSWORD`  
`VENTURELOOP_EMAIL` / `VENTURELOOP_PASSWORD`  
`DICE_EMAIL` / `DICE_PASSWORD`  
`BUILTIN_EMAIL` / `BUILTIN_PASSWORD`  
`LEMONIO_EMAIL` / `LEMONIO_PASSWORD`  
`ARCDEV_EMAIL` / `ARCDEV_PASSWORD`  
`CONTRA_EMAIL` / `CONTRA_PASSWORD`  
`TOPTAL_EMAIL` / `TOPTAL_PASSWORD`  
`GUNIO_EMAIL` / `GUNIO_PASSWORD`  
`HIRED_EMAIL` / `HIRED_PASSWORD`  
`TURING_EMAIL` / `TURING_PASSWORD`  
`FLEXIPLE_EMAIL` / `FLEXIPLE_PASSWORD`  
`PEOPLEPHOUR_EMAIL` / `PEOPLEPHOUR_PASSWORD`

---

## 📊 Google Sheet Format

| Date | Platform | Job Title | Company | Location | Status | Job URL |
|------|----------|-----------|---------|----------|--------|---------|
| 2026-09-13 06:00 | Remote OK | Backend Developer | Stripe | Remote | Scraped | https://... |
| 2026-09-13 03:15 | Cutshort | Python Engineer | Razorpay | Bangalore | Applied | https://... |
| 2026-09-13 08:00 | YC Work at Startup | SWE Intern | Acme Inc | SF | Scraped / Review | https://... |

**Duplicate check:** `Job Title` + `Company` + `Platform` (case-insensitive)

---

## 🚀 Setup Steps

1. **Create the repo** on GitHub, push this code.
2. **Create Google Sheet** named "Jobs" (or it auto-creates).
3. **Set up GCP Service Account** → download JSON → add as `GOOGLE_SERVICE_ACCOUNT_JSON` secret.
4. **Share your Google Sheet** with the service account email (`...@...iam.gserviceaccount.com`).
5. **Add all other secrets** in GitHub → Settings → Secrets → Actions.
6. **Enable workflows** → they run on schedule automatically.
7. **Manually trigger** any workflow via `workflow_dispatch` to test immediately.

---

## ⚙️ Local Testing

```bash
pip install -r requirements.txt
playwright install chromium

export GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/key.json
export GOOGLE_SHEET_ID=your_sheet_id
export JOB_KEYWORDS="python,django,react"

# Test individual agents
python -m agents.api_scrapers.remoteok
python -m agents.email_pass.cutshort
python -m agents.scrape_only.all_scrapers
```
