"""
Fresh job watcher (extension): detects jobs that are NEW since the last time
this script ran - from BOTH RemoteOK (public API) and your Gmail LinkedIn/
Naukri alerts - scores them against your resume immediately, and creates an
instant Google Calendar alert (popup notification) for high-scoring matches.
This is your closest safe substitute for "notify me the moment a matching
LinkedIn job appears."

Only reads LinkedIn/Naukri content through your own inbox (the official
Gmail API) - never scrapes or logs into LinkedIn directly. LinkedIn has no
public API for individual developers, and scraping/auto-applying there
violates their Terms of Service and risks your account being banned. This
script gets you the same real-world benefit (being an early applicant)
through safe, ToS-compliant sources instead.

Designed to be run frequently (e.g. every 3-5 minutes) via Windows Task
Scheduler, so it can catch new postings/alerts shortly after they appear.

Run once manually to test:
    python -m agents.fresh_job_watcher
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sentence_transformers import SentenceTransformer, util

from agents.matching_agent import load_resume_text
from agents.remoteok_ingest import fetch_remoteok_jobs
from agents.gmail_ingest import fetch_gmail_jobs
from agents.planning_agent import get_calendar_service

SEEN_JOBS_PATH = PROJECT_ROOT / "data" / "seen_jobs.json"
ALERT_THRESHOLD = 50.0  # only alert for genuinely strong matches, not just "new"


def load_seen_job_links() -> set:
    if SEEN_JOBS_PATH.exists():
        return set(json.loads(SEEN_JOBS_PATH.read_text()))
    return set()


def save_seen_job_links(links: set):
    SEEN_JOBS_PATH.parent.mkdir(exist_ok=True)
    SEEN_JOBS_PATH.write_text(json.dumps(list(links)))


def get_all_current_jobs() -> list:
    """
    Combines RemoteOK listings and Gmail LinkedIn/Naukri alerts into one
    unified list, each with a consistent shape: title, company/source,
    link (or gmail message id, used as the "seen" key), and searchable text.
    """
    combined = []

    for job in fetch_remoteok_jobs(max_results=50):
        combined.append({
            "title": job["title"],
            "company": job["company"],
            "link": job["link"],
            "seen_key": job["link"],
            "search_text": f"{job['title']} {' '.join(job.get('tags', []))}",
        })

    for job in fetch_gmail_jobs():
        combined.append({
            "title": job["title"],
            "company": job.get("source", "Gmail alert"),
            "link": job.get("link", ""),
            "seen_key": f"gmail:{job.get('message_id', job['title'])}",
            "search_text": f"{job['title']} {job.get('description', '')}",
        })

    return combined


def score_job(model, resume_embedding, job: dict) -> float:
    job_embedding = model.encode(job["search_text"], convert_to_tensor=True)
    return round(util.cos_sim(resume_embedding, job_embedding).item() * 100, 1)


def create_instant_alert_event(service, job: dict):
    """
    Creates a short calendar event starting right now, with a popup
    reminder set to fire immediately - this makes Google Calendar show
    a notification banner/popup on your phone and laptop within a minute,
    same as any other calendar reminder.
    """
    now = datetime.now(timezone.utc)
    start = now
    end = now + timedelta(minutes=15)

    link_line = f"Link: {job['link']}\n\n" if job.get("link") else ""

    event = {
        "summary": f"NEW JOB ALERT ({job['match_score']}%): {job['title']}",
        "description": (
            f"Source: {job['company']}\n"
            f"Match score: {job['match_score']}%\n"
            f"{link_line}"
            f"Posted recently - apply soon while it's fresh."
        ),
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Kolkata"},
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 0},  # popup right at event start (now)
            ],
        },
    }
    return service.events().insert(calendarId="primary", body=event).execute()


def run_job_watch_check(status_callback=None):
    """
    Runs one full check: finds new jobs/alerts, scores them, creates calendar
    alerts for strong matches. Returns a summary dict so callers (like the
    dashboard) can display results without needing to read terminal output.

    status_callback: optional function(str) called with progress messages,
    e.g. a Streamlit st.write, so the UI can show live progress.
    """
    def status(msg):
        if status_callback:
            status_callback(msg)

    status("Checking for brand-new job postings and Gmail alerts...")
    seen_links = load_seen_job_links()
    current_jobs = get_all_current_jobs()
    new_jobs = [j for j in current_jobs if j["seen_key"] not in seen_links]

    if not new_jobs:
        status("No new postings or alerts since last check.")
        return {"new_count": 0, "alerts": []}

    status(f"Found {len(new_jobs)} brand-new item(s). Scoring against resume...")

    model = SentenceTransformer("all-MiniLM-L6-v2")
    resume_text = load_resume_text()
    resume_embedding = model.encode(resume_text, convert_to_tensor=True)

    strong_matches = []
    for job in new_jobs:
        job["match_score"] = score_job(model, resume_embedding, job)
        if job["match_score"] >= ALERT_THRESHOLD:
            strong_matches.append(job)

    alerts_created = []
    if strong_matches:
        status(f"{len(strong_matches)} strong new match(es) found - creating calendar alerts...")
        calendar_service = get_calendar_service()
        for job in strong_matches:
            try:
                created = create_instant_alert_event(calendar_service, job)
                job["calendar_link"] = created.get("htmlLink")
                alerts_created.append(job)
                status(f"  Alert created: {job['title']} ({job['match_score']}%)")
            except Exception as e:
                status(f"  Failed to create alert for {job['title']}: {e}")
    else:
        status("New postings/alerts found, but none scored above the alert threshold.")

    seen_links.update(j["seen_key"] for j in new_jobs)
    save_seen_job_links(seen_links)
    status("Done.")

    return {"new_count": len(new_jobs), "alerts": alerts_created}


if __name__ == "__main__":
    result = run_job_watch_check(status_callback=print)
    if result["new_count"] == 0:
        sys.exit(0)

