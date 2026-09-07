"""
Planning agent (Week 3): takes your top resume-matched jobs and automatically
schedules "apply to this job" events on your Google Calendar, slotted into
free time you actually have.

How it works:
1. Looks at your Google Calendar for the next N days to find busy periods
2. Finds free slots of at least `SLOT_DURATION_MINUTES` between your
   working hours
3. Takes your top-matched jobs (from Week 2) and creates one calendar event
   per job, each in its own free slot, with the job link in the event
   description
4. Prints what it scheduled so you can see it before checking your calendar

This only uses the official Google Calendar API - no automation that
bypasses your review, and every event it creates is clearly labeled so you
can delete/edit it like any normal calendar event.
"""

import sys
from datetime import datetime, timedelta, time, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from googleapiclient.discovery import build
from config.google_auth import get_calendar_service
from agents.matching_agent import (
    load_resume_text,
    collect_all_jobs,
    rank_jobs_by_resume_match,
)
from sentence_transformers import SentenceTransformer

# --- Settings you can tweak ---
LOOK_AHEAD_DAYS = 5          # how many days forward to search for free time
WORK_START_HOUR = 10         # earliest hour (24h format) to schedule a task
WORK_END_HOUR = 20           # latest hour to schedule a task
SLOT_DURATION_MINUTES = 30   # how long each "apply to job" task takes
TOP_N_JOBS_TO_SCHEDULE = 3   # only schedule your best-matched jobs
MIN_MATCH_SCORE = 50.0       # skip jobs below this relevance score


def get_busy_periods(service, days_ahead: int):
    """Returns a list of (start, end) datetime tuples for existing events."""
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    events_result = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    busy = []
    for event in events_result.get("items", []):
        start = event["start"].get("dateTime")
        end = event["end"].get("dateTime")
        if start and end:  # skip all-day events (no dateTime, just date)
            busy.append((
                datetime.fromisoformat(start),
                datetime.fromisoformat(end),
            ))
    return busy


def find_free_slots(busy_periods, days_ahead, slot_minutes, needed_slots):
    """
    Walks forward day by day, hour by hour, and returns a list of
    (start, end) datetime tuples that don't overlap any busy period.
    """
    IST = timezone(timedelta(hours=5, minutes=30))
    free_slots = []
    today = datetime.now(IST).date()
    now_ist = datetime.now(IST)

    for day_offset in range(days_ahead):
        if len(free_slots) >= needed_slots:
            break

        day = today + timedelta(days=day_offset)
        slot_start = datetime.combine(day, time(hour=WORK_START_HOUR), tzinfo=IST)
        day_end = datetime.combine(day, time(hour=WORK_END_HOUR), tzinfo=IST)

        while slot_start + timedelta(minutes=slot_minutes) <= day_end:
            slot_end = slot_start + timedelta(minutes=slot_minutes)

            overlaps = any(
                slot_start < busy_end and slot_end > busy_start
                for busy_start, busy_end in busy_periods
            )

            if not overlaps and slot_start > now_ist:
                free_slots.append((slot_start, slot_end))
                if len(free_slots) >= needed_slots:
                    break

            slot_start += timedelta(minutes=slot_minutes)

    return free_slots


def get_already_scheduled_titles(service, days_ahead: int) -> set:
    """
    Returns the set of job titles that already have an 'Apply: ...' event on
    the calendar, so running this script daily never creates duplicates.
    """
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    events = service.events().list(
        calendarId="primary", timeMin=time_min, timeMax=time_max,
        singleEvents=True, q="Apply:",
    ).execute().get("items", [])

    scheduled = set()
    for event in events:
        summary = event.get("summary", "")
        if summary.startswith("Apply: "):
            title_part = summary[len("Apply: "):]
            title_part = title_part.rsplit(" (", 1)[0]
            scheduled.add(title_part)
    return scheduled


def create_application_event(service, job: dict, start, end):
    event = {
        "summary": f"Apply: {job['title']} ({job['source']})",
        "description": (
            f"Match score: {job['match_score']}%\n"
            f"Link: {job.get('link', 'N/A')}\n\n"
            f"Auto-scheduled by career-agent."
        ),
        "start": {"dateTime": start.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": end.isoformat(), "timeZone": "Asia/Kolkata"},
    }
    return service.events().insert(calendarId="primary", body=event).execute()


if __name__ == "__main__":
    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Ranking jobs against your resume...")
    resume_text = load_resume_text()
    jobs = collect_all_jobs()
    ranked_jobs = rank_jobs_by_resume_match(jobs, resume_text, model)

    top_jobs = [j for j in ranked_jobs if j["match_score"] >= MIN_MATCH_SCORE]

    print("\nChecking your calendar for already-scheduled jobs...")
    calendar_service = get_calendar_service()
    already_scheduled = get_already_scheduled_titles(calendar_service, LOOK_AHEAD_DAYS)

    top_jobs = [j for j in top_jobs if j["title"] not in already_scheduled][:TOP_N_JOBS_TO_SCHEDULE]

    if not top_jobs:
        print("Nothing new to schedule — all qualifying jobs are already on your calendar.")
        sys.exit(0)

    print(f"\nTop {len(top_jobs)} job(s) selected for scheduling:")
    for j in top_jobs:
        print(f"  - {j['match_score']}% | {j['title']}")

    print("\nFinding free time slots...")
    busy = get_busy_periods(calendar_service, LOOK_AHEAD_DAYS)
    free_slots = find_free_slots(busy, LOOK_AHEAD_DAYS, SLOT_DURATION_MINUTES, len(top_jobs))

    if len(free_slots) < len(top_jobs):
        print(
            f"Only found {len(free_slots)} free slot(s) in the next "
            f"{LOOK_AHEAD_DAYS} days. Scheduling what fits."
        )

    print("\nScheduling application tasks...\n")
    for job, (start, end) in zip(top_jobs, free_slots):
        created = create_application_event(calendar_service, job, start, end)
        print(f"Scheduled: {job['title']}")
        print(f"  When: {start.strftime('%A %d %b, %I:%M %p')}")
        print(f"  Calendar link: {created.get('htmlLink')}\n")

    print("Done. Check your Google Calendar to see the scheduled tasks.")
