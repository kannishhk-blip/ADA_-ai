"""
Daily summary for ADA Agent — what happened today at a glance.

Shows Gmail matches, calendar events added, and fresh job postings.
Used by the dashboard Daily Summary page and the summary button.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.activity_tracker import count_calendar_events_today, get_today_stats
from agents.gmail_ingest import fetch_gmail_jobs
from agents.job_pipeline import rank_jobs, remoteok_to_jobs
from agents.matching_agent import load_resume_text
from config.google_auth import get_calendar_service
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


def build_daily_summary(*, min_score: float = 50.0) -> dict:
    """
    Build a rich summary dict for the dashboard UI.

    Combines saved activity stats + a live scan for current top matches.
    """
    stats = get_today_stats()
    today_label = datetime.now().strftime("%A, %d %B %Y")

    # Live snapshot of current matches (not re-scheduling)
    gmail_jobs = fetch_gmail_jobs()
    remote_jobs = remoteok_to_jobs()
    all_jobs = gmail_jobs + remote_jobs

    ranked = []
    if all_jobs:
        try:
            model = SentenceTransformer(MODEL_NAME)
            ranked = rank_jobs(all_jobs, model=model)
        except FileNotFoundError:
            ranked = [{**j, "match_score": 0} for j in all_jobs]

    gmail_matches = [j for j in ranked if "gmail" in j.get("source", "").lower()]
    strong_gmail = [j for j in gmail_matches if j.get("match_score", 0) >= min_score]

    calendar_today = 0
    try:
        calendar_today = count_calendar_events_today(get_calendar_service())
    except Exception:
        calendar_today = stats["calendar_added"]

    return {
        "date_label": today_label,
        "gmail_alerts_today": stats["gmail_scanned"] or len(gmail_jobs),
        "gmail_matches_today": stats["gmail_matches"] or len(strong_gmail),
        "calendar_added_today": max(stats["calendar_added"], calendar_today),
        "fresh_jobs_today": stats["fresh_jobs"],
        "remoteok_found_today": stats["remoteok_found"],
        "top_matches": ranked[:5],
        "gmail_matches": strong_gmail[:5],
        "activity_log": stats["actions"],
        "summary_text": (
            f"Today ADA Agent found {stats['gmail_matches'] or len(strong_gmail)} Gmail match(es), "
            f"spotted {stats['fresh_jobs']} fresh job(s), and added "
            f"{max(stats['calendar_added'], calendar_today)} event(s) to your calendar."
        ),
    }


if __name__ == "__main__":
    summary = build_daily_summary()
    print(f"\nADA Agent — Daily Summary ({summary['date_label']})\n")
    print(f"  Gmail alerts checked : {summary['gmail_alerts_today']}")
    print(f"  Gmail matches        : {summary['gmail_matches_today']}")
    print(f"  Fresh jobs spotted   : {summary['fresh_jobs_today']}")
    print(f"  Added to calendar    : {summary['calendar_added_today']}")
    print(f"\n{summary['summary_text']}\n")
