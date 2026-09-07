"""
Meeting reminder agent (Week 5): scans your Google Calendar for meetings
starting soon and calls your phone with a spoken reminder - so you never
miss a meeting even if you're away from your laptop.

Works with ANY meeting on your Google Calendar (Teams, Zoom, Google Meet,
or plain events) since it doesn't need a separate Microsoft/Teams login -
it just reads whatever is already on your calendar.

Intended to be run periodically (e.g. every 5-10 minutes) via Windows Task
Scheduler, so it can catch meetings as they approach. Each run only calls
once per meeting (tracked in a local file) so you don't get repeat calls.

Run directly to check right now:
    python -m agents.meeting_reminder_agent
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.google_auth import get_calendar_service
from agents.call_agent import make_call_with_message, MY_PHONE_NUMBER

# How far ahead to look for meetings, and how close counts as "call me now"
REMINDER_WINDOW_MINUTES = 10
CALLED_LOG_PATH = PROJECT_ROOT / "data" / "already_called_meetings.json"


def load_already_called() -> set:
    if CALLED_LOG_PATH.exists():
        return set(json.loads(CALLED_LOG_PATH.read_text()))
    return set()


def save_already_called(called_ids: set):
    CALLED_LOG_PATH.parent.mkdir(exist_ok=True)
    CALLED_LOG_PATH.write_text(json.dumps(list(called_ids)))


def get_upcoming_meetings(service, window_minutes: int):
    """Returns calendar events starting within the next `window_minutes`."""
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(minutes=window_minutes)).isoformat()

    events = service.events().list(
        calendarId="primary",
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
    ).execute().get("items", [])

    # Skip our own "Apply: ..." job-application tasks - those aren't meetings
    return [e for e in events if not e.get("summary", "").startswith("Apply: ")]


def build_reminder_message(event: dict) -> str:
    title = event.get("summary", "your meeting")
    start_raw = event["start"].get("dateTime")
    start_time = datetime.fromisoformat(start_raw).strftime("%I:%M %p") if start_raw else "soon"

    link = ""
    location = event.get("location", "")
    if "http" in location:
        link = " A meeting link is in your calendar invite."
    elif event.get("hangoutLink"):
        link = " A Google Meet link is in your calendar invite."

    return (
        f"Reminder. You have a meeting, {title}, starting at {start_time}."
        f"{link} Please check your calendar."
    )


if __name__ == "__main__":
    if not MY_PHONE_NUMBER:
        print("Set MY_PHONE_NUMBER in your .env file first.")
        sys.exit(1)

    print("Checking calendar for upcoming meetings...")
    service = get_calendar_service()
    meetings = get_upcoming_meetings(service, REMINDER_WINDOW_MINUTES)

    if not meetings:
        print(f"No meetings starting in the next {REMINDER_WINDOW_MINUTES} minutes.")
        sys.exit(0)

    already_called = load_already_called()
    new_calls = 0

    for event in meetings:
        event_id = event["id"]
        if event_id in already_called:
            continue  # already reminded about this one

        message = build_reminder_message(event)
        print(f"Calling {MY_PHONE_NUMBER} about: {event.get('summary')}")

        try:
            make_call_with_message(MY_PHONE_NUMBER, message)
            already_called.add(event_id)
            new_calls += 1
        except Exception as e:
            print(f"Failed to call for '{event.get('summary')}': {e}")

    save_already_called(already_called)
    print(f"Done. Placed {new_calls} new reminder call(s).")
