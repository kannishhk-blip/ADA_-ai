"""
Tracks what ADA Agent did today — Gmail scans, calendar events, fresh jobs.

Stats are saved to data/daily_activity.json so the Daily Summary page
can show accurate numbers even after you restart the dashboard.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ACTIVITY_PATH = PROJECT_ROOT / "data" / "daily_activity.json"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _load_all() -> dict:
    if ACTIVITY_PATH.exists():
        try:
            return json.loads(ACTIVITY_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_all(data: dict) -> None:
    ACTIVITY_PATH.parent.mkdir(exist_ok=True)
    ACTIVITY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _today_record() -> dict:
    data = _load_all()
    key = _today()
    if key not in data:
        data[key] = {
            "date": key,
            "gmail_scanned": 0,
            "gmail_matches": 0,
            "remoteok_found": 0,
            "calendar_added": 0,
            "fresh_jobs": 0,
            "actions": [],
        }
    return data[key]


def _append_action(message: str) -> None:
    data = _load_all()
    record = _today_record()
    ts = datetime.now().strftime("%I:%M %p")
    record["actions"].insert(0, {"time": ts, "message": message})
    record["actions"] = record["actions"][:30]
    data[_today()] = record
    _save_all(data)


def record_gmail_scan(found: int, matches: int, scheduled: int) -> None:
    data = _load_all()
    record = _today_record()
    record["gmail_scanned"] += found
    record["gmail_matches"] += matches
    record["calendar_added"] += scheduled
    data[_today()] = record
    _save_all(data)
    _append_action(
        f"Checked Gmail — {found} alert(s), {matches} match(es), {scheduled} added to calendar"
    )


def record_remoteok_scan(found: int, scheduled: int) -> None:
    data = _load_all()
    record = _today_record()
    record["remoteok_found"] += found
    record["calendar_added"] += scheduled
    data[_today()] = record
    _save_all(data)
    _append_action(f"Fetched RemoteOK — {found} job(s), {scheduled} scheduled")


def record_fresh_jobs(count: int, scheduled: int = 0) -> None:
    data = _load_all()
    record = _today_record()
    record["fresh_jobs"] += count
    record["calendar_added"] += scheduled
    data[_today()] = record
    _save_all(data)
    _append_action(f"Job watcher — {count} new posting(s), {scheduled} calendar alert(s)")


def record_calendar_scheduled(count: int) -> None:
    if count <= 0:
        return
    data = _load_all()
    record = _today_record()
    record["calendar_added"] += count
    data[_today()] = record
    _save_all(data)
    _append_action(f"Scheduled {count} application block(s) on Google Calendar")


def get_today_stats() -> dict:
    """Return today's activity numbers for the dashboard."""
    data = _load_all()
    record = data.get(_today(), {})
    return {
        "date": _today(),
        "gmail_scanned": record.get("gmail_scanned", 0),
        "gmail_matches": record.get("gmail_matches", 0),
        "remoteok_found": record.get("remoteok_found", 0),
        "calendar_added": record.get("calendar_added", 0),
        "fresh_jobs": record.get("fresh_jobs", 0),
        "actions": record.get("actions", []),
    }


def count_calendar_events_today(calendar_service) -> int:
    """Count Apply / job-alert events created on Google Calendar today."""
    ist = timezone.utc  # we'll use local midnight via date comparison
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time()).astimezone()
    end = datetime.combine(today, datetime.max.time()).astimezone()

    try:
        events = (
            calendar_service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                q="Apply",
            )
            .execute()
            .get("items", [])
        )
        alert_events = (
            calendar_service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                singleEvents=True,
                q="NEW JOB ALERT",
            )
            .execute()
            .get("items", [])
        )
        return len(events) + len(alert_events)
    except Exception:
        return 0
