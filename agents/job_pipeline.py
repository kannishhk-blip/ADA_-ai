"""
Job pipeline — connects ingestion, resume matching, and Google Calendar.

Used by the dashboard so button clicks actually:
  1. Fetch jobs (Gmail / RemoteOK)
  2. Score them against your resume
  3. Show titles + links in the UI
  4. Auto-schedule apply-time blocks on Google Calendar
"""

from __future__ import annotations

import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.activity_tracker import (
    record_gmail_scan,
    record_remoteok_scan,
)
from agents.gmail_ingest import fetch_gmail_jobs
from agents.matching_agent import (
    MODEL_NAME,
    load_resume_text,
    rank_jobs_by_resume_match,
)
from agents.planning_agent import (
    LOOK_AHEAD_DAYS,
    SLOT_DURATION_MINUTES,
    create_application_event,
    find_free_slots,
    get_already_scheduled_titles,
    get_busy_periods,
)
from agents.remoteok_ingest import fetch_remoteok_jobs
from config.google_auth import get_calendar_service


def remoteok_to_jobs() -> list[dict]:
    """Normalize RemoteOK API results into our job dict format."""
    jobs = []
    for job in fetch_remoteok_jobs():
        jobs.append(
            {
                "title": job["title"],
                "source": f"RemoteOK - {job['company']}",
                "link": job["link"],
                "description": " ".join(job.get("tags", [])),
            }
        )
    return jobs


def rank_jobs(jobs: list[dict], model: SentenceTransformer | None = None) -> list[dict]:
    """Score and sort jobs against data/resume.txt."""
    if not jobs:
        return []

    if model is None:
        model = SentenceTransformer(MODEL_NAME)

    resume_text = load_resume_text()
    return rank_jobs_by_resume_match(jobs, resume_text, model)


def schedule_jobs(
    ranked_jobs: list[dict],
    *,
    min_score: float,
    top_n: int,
    calendar_service=None,
) -> list[dict]:
    """
    Create Google Calendar events for top unmatched jobs.

    Returns a list of result dicts:
      {job, start, end, calendar_link, status}
    """
    if not ranked_jobs:
        return []

    calendar_service = calendar_service or get_calendar_service()
    already = get_already_scheduled_titles(calendar_service, LOOK_AHEAD_DAYS)

    candidates = [
        job
        for job in ranked_jobs
        if job.get("match_score", 0) >= min_score and job["title"] not in already
    ][:top_n]

    if not candidates:
        return []

    busy = get_busy_periods(calendar_service, LOOK_AHEAD_DAYS)
    slots = find_free_slots(busy, LOOK_AHEAD_DAYS, SLOT_DURATION_MINUTES, len(candidates))

    results = []
    for job, (start, end) in zip(candidates, slots):
        created = create_application_event(calendar_service, job, start, end)
        results.append(
            {
                "job": job,
                "start": start,
                "end": end,
                "calendar_link": created.get("htmlLink", ""),
                "status": "scheduled",
            }
        )
    return results


def run_gmail_pipeline(*, min_score: float = 50.0, top_n: int = 3) -> dict:
    """
    Check Gmail job alerts → rank → schedule on calendar.

    Returns summary dict for the dashboard to display.
    """
    jobs = fetch_gmail_jobs()
    model = SentenceTransformer(MODEL_NAME)
    ranked = rank_jobs(jobs, model=model)
    scheduled = schedule_jobs(ranked, min_score=min_score, top_n=top_n)
    done = [r for r in scheduled if r.get("status") == "scheduled"]
    matches = [j for j in ranked if j.get("match_score", 0) >= min_score]
    record_gmail_scan(len(jobs), len(matches), len(done))

    return {
        "source": "Gmail",
        "found": len(jobs),
        "ranked_jobs": ranked,
        "scheduled": done,
        "message": _build_message("Gmail", jobs, scheduled),
    }


def run_remoteok_pipeline(*, min_score: float = 50.0, top_n: int = 3) -> dict:
    """Fetch RemoteOK listings → rank → schedule on calendar."""
    jobs = remoteok_to_jobs()
    model = SentenceTransformer(MODEL_NAME)
    ranked = rank_jobs(jobs, model=model)
    scheduled = schedule_jobs(ranked, min_score=min_score, top_n=top_n)
    done = [r for r in scheduled if r.get("status") == "scheduled"]
    record_remoteok_scan(len(jobs), len(done))

    return {
        "source": "RemoteOK",
        "found": len(jobs),
        "ranked_jobs": ranked,
        "scheduled": done,
        "message": _build_message("RemoteOK", jobs, scheduled),
    }


def run_full_pipeline(*, min_score: float = 50.0, top_n: int = 3) -> dict:
    """Gmail + RemoteOK combined pipeline."""
    jobs = fetch_gmail_jobs() + remoteok_to_jobs()
    model = SentenceTransformer(MODEL_NAME)
    ranked = rank_jobs(jobs, model=model)
    scheduled = schedule_jobs(ranked, min_score=min_score, top_n=top_n)
    done = [r for r in scheduled if r.get("status") == "scheduled"]
    gmail_jobs = [j for j in jobs if "gmail" in j.get("source", "").lower()]
    gmail_count = len(gmail_jobs)
    gmail_matches = [
        j for j in ranked
        if "gmail" in j.get("source", "").lower()
        and j.get("match_score", 0) >= min_score
    ]
    gmail_scheduled = [
        item for item in done
        if "gmail" in item["job"].get("source", "").lower()
    ]
    remote_scheduled = len(done) - len(gmail_scheduled)

    if gmail_count:
        record_gmail_scan(gmail_count, len(gmail_matches), len(gmail_scheduled))
    remote_count = len(jobs) - gmail_count
    if remote_count > 0:
        record_remoteok_scan(remote_count, remote_scheduled)

    return {
        "source": "All sources",
        "found": len(jobs),
        "ranked_jobs": ranked,
        "scheduled": done,
        "message": _build_message("All sources", jobs, scheduled),
    }


def _build_message(source: str, jobs: list[dict], scheduled: list[dict]) -> str:
    scheduled_count = sum(1 for item in scheduled if item.get("status") == "scheduled")
    if not jobs:
        return f"No jobs found from {source}."
    if scheduled_count:
        return f"Found {len(jobs)} job(s) from {source}. Scheduled {scheduled_count} on your Google Calendar."
    return f"Found {len(jobs)} job(s) from {source}. None new to schedule (already on calendar or below match threshold)."
