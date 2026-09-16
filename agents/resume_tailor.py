"""
resume_tailor.py
----------------
Calculates a match % between a job description and Aryan Sharma's resume
using weighted multi-category keyword scoring.

Scoring model:
- Each category contributes independently.
- Category score = min(1.0,  hits_in_category / CATEGORY_THRESHOLD)
  where THRESHOLD is the minimum hits needed for a full-category score.
  This avoids penalising large keyword lists.
- Final score = weighted sum of category scores × 100, capped at 100.
"""

import re
from typing import Optional

# ─────────────────────────────────────────────
# MASTER RESUME — structured keyword bank
# ─────────────────────────────────────────────
RESUME: dict[str, list[str]] = {
    "languages": [
        "python", "javascript", "c++", "sql", "typescript", "js"
    ],
    "frameworks": [
        "fastapi", "nodejs", "node.js", "express", "react",
        "sqlalchemy", "pandas", "numpy", "scikit-learn", "sklearn",
        "xgboost", "streamlit", "flask", "django"
    ],
    "databases": [
        "postgresql", "postgres", "mongodb", "sqlite", "mysql",
        "nosql", "redis", "orm"
    ],
    "cs_ai_ml": [
        "machine learning", "ml", "deep learning", "nlp",
        "llm", "generative ai", "rag", "langchain",
        "gemini", "openai", "groq", "huggingface",
        "classification", "regression", "xgboost", "random forest",
        "neural network", "computer vision", "data science",
        "rest api", "restful", "api", "microservices",
        "oop", "dsa", "data structures", "algorithms",
        "distributed systems", "system design"
    ],
    "devops_tools": [
        "git", "github", "github actions", "ci/cd", "cicd",
        "docker", "kubernetes", "aws", "gcp", "azure",
        "linux", "bash", "agile", "scrum", "jira"
    ],
    "soft_match": [
        "intern", "internship", "sde", "backend", "fullstack",
        "full stack", "full-stack", "frontend", "software engineer",
        "developer", "engineer", "startup", "product"
    ],
}

# How many keyword hits = full score for that category
# (prevents large lists from being impossible to saturate)
CATEGORY_THRESHOLDS: dict[str, int] = {
    "languages":    2,
    "frameworks":   2,
    "databases":    1,
    "cs_ai_ml":     3,
    "devops_tools": 2,
    "soft_match":   1,
}

# Column weights (must sum to 1.0)
WEIGHTS: dict[str, float] = {
    "languages":    0.20,
    "frameworks":   0.22,
    "databases":    0.10,
    "cs_ai_ml":     0.25,
    "devops_tools": 0.13,
    "soft_match":   0.10,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1"

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _normalise(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ./+#\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _count_hits(jd_norm: str, keywords: list[str]) -> int:
    return sum(
        1 for kw in keywords
        if re.search(r"\b" + re.escape(kw) + r"\b", jd_norm)
    )


def _category_score(hits: int, threshold: int) -> float:
    """Returns 0.0–1.0; saturates at threshold hits."""
    if threshold == 0:
        return 0.0
    return min(1.0, hits / threshold)


# ─────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────

def calculate_match(job_description: str, job_title: str = "") -> int:
    """
    Returns an integer match percentage (0–100).

    Parameters
    ----------
    job_description : str  — raw JD text from the email body.
    job_title       : str  — job title (optional, used as extra signal).
    """
    if not job_description or not job_description.strip():
        return 0

    combined = _normalise(f"{job_title} {job_description}")

    total = 0.0
    for category, keywords in RESUME.items():
        hits      = _count_hits(combined, keywords)
        threshold = CATEGORY_THRESHOLDS[category]
        cat_score = _category_score(hits, threshold)
        weight    = WEIGHTS[category]
        total    += cat_score * weight

    pct = round(total * 100)
    return min(pct, 100)


def get_match_label(pct: int) -> str:
    if pct >= 70:  return "Strong Match"
    elif pct >= 50: return "Good Match"
    elif pct >= 30: return "Partial Match"
    else:           return "Weak Match"


def debug_match(job_description: str, job_title: str = "") -> None:
    """Print per-category breakdown — useful during development."""
    combined = _normalise(f"{job_title} {job_description}")
    print(f"\n{'Category':<16} {'Hits':>4} {'Thresh':>6} {'Score':>6} {'Weight':>6} {'Contrib':>7}")
    print("-" * 55)
    total = 0.0
    for cat, kws in RESUME.items():
        hits      = _count_hits(combined, kws)
        threshold = CATEGORY_THRESHOLDS[cat]
        score     = _category_score(hits, threshold)
        weight    = WEIGHTS[cat]
        contrib   = score * weight
        total    += contrib
        hit_kws   = [kw for kw in kws if re.search(r"\b" + re.escape(kw) + r"\b", combined)]
        print(f"{cat:<16} {hits:>4} {threshold:>6} {score:>6.2f} {weight:>6.2f} {contrib*100:>6.1f}%  ← {hit_kws}")
    pct = round(min(total * 100, 100))
    print(f"\n{'TOTAL':>45}  {pct}%  ({get_match_label(pct)})\n")


# ─────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────
if __name__ == "__main__":
    jd1 = """
    Looking for a Python Backend Intern with FastAPI, PostgreSQL, REST APIs.
    Docker and GitHub Actions CI/CD experience a plus.
    Machine learning / LLM integration (Gemini / OpenAI) preferred.
    Agile startup environment. 6-month internship, remote, stipend 15000/month.
    """
    debug_match(jd1, "Backend Intern")

    jd2 = """
    Frontend React Developer — HTML, CSS, Figma, JavaScript.
    No backend or ML work. UI/UX internship.
    """
    debug_match(jd2, "Frontend Intern")

    jd3 = """
    Android developer intern — Kotlin, Jetpack Compose, Firebase.
    """
    debug_match(jd3, "Android Intern")
