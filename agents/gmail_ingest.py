"""
Gmail job-alert ingestion — Week 1 proof that we can pull real job data.

Uses the official Gmail API (not scraping) to search your inbox for recent
job-alert emails from LinkedIn and Naukri. We only READ messages; nothing
is sent or modified.

Run directly:
    python agents/gmail_ingest.py
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

# Allow imports from the project root (config/, utils/, etc.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.google_auth import get_gmail_service

# Gmail search query — edit senders here if your alerts come from different addresses.
# "newer_than:7d" limits results to the last 7 days (Gmail's built-in search syntax).
JOB_ALERT_QUERY = (
    "(from:jobalerts-noreply@linkedin.com OR from:linkedin.com "
    'OR from:alert@naukri.com OR from:naukri.com subject:"job") '
    "newer_than:7d"
)

# How many messages to fetch per API call (Gmail max is 500).
MAX_RESULTS = 25

# Job-board URLs we try to pull out of alert email bodies.
JOB_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?(?:linkedin\.com/(?:jobs/view|comm/jobs/view)[^\s\"'<>]+|"
    r"naukri\.com/[^\s\"'<>]+|"
    r"indeed\.com/[^\s\"'<>]+)",
    re.IGNORECASE,
)


def _decode_header(value: str | None) -> str:
    """Return a safe string for printing (Gmail headers can be missing)."""
    return (value or "").strip() or "(no subject)"


def _get_header(headers: list[dict], name: str) -> str | None:
    """Find a header value by name (e.g. 'Subject', 'From')."""
    name_lower = name.lower()
    for header in headers:
        if header.get("name", "").lower() == name_lower:
            return header.get("value")
    return None


def _decode_body_data(data: str) -> str:
    """Gmail body data is base64url-encoded."""
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _collect_body_text(payload: dict) -> str:
    """Walk MIME parts and concatenate all text/html content."""
    if not payload:
        return ""

    mime_type = payload.get("mimeType", "")
    body = payload.get("body", {})
    data = body.get("data")
    text = ""

    if data and mime_type in ("text/plain", "text/html"):
        text = _decode_body_data(data)

    for part in payload.get("parts", []) or []:
        text += " " + _collect_body_text(part)

    return text


def extract_job_link(message: dict) -> str:
    """
    Pull the first job-posting URL from a Gmail alert message.
    Falls back to opening the email in Gmail if no job URL is found.
    """
    payload = message.get("payload", {})
    blob = " ".join(
        [
            message.get("snippet", "") or "",
            _collect_body_text(payload),
        ]
    )

    match = JOB_URL_PATTERN.search(blob)
    if match:
        return match.group(0).rstrip(").,;\"'")

    message_id = message.get("id")
    if message_id:
        return f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
    return ""


def message_to_job(message: dict) -> dict:
    """Convert a Gmail API message into our standard job dict."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    subject = _decode_header(_get_header(headers, "Subject"))
    sender = _decode_header(_get_header(headers, "From"))
    snippet = (message.get("snippet") or "").replace("\n", " ").strip()
    link = extract_job_link(message)

    source = "Gmail alert"
    if "linkedin" in sender.lower():
        source = "Gmail - LinkedIn"
    elif "naukri" in sender.lower():
        source = "Gmail - Naukri"

    return {
        "title": subject,
        "source": source,
        "link": link,
        "description": snippet,
        "message_id": message.get("id", ""),
    }


def fetch_gmail_jobs(query: str = JOB_ALERT_QUERY, max_results: int = MAX_RESULTS) -> list[dict]:
    """Fetch Gmail alerts and return normalized job dicts (no printing)."""
    service = get_gmail_service()
    messages = fetch_job_alert_messages(service, query=query, max_results=max_results)
    return [message_to_job(message) for message in messages]


def fetch_job_alert_messages(service, query: str = JOB_ALERT_QUERY, max_results: int = MAX_RESULTS):
    """
    Search Gmail and return full message objects for matching job alerts.

    Args:
        service: Authenticated Gmail API service from google_auth.get_gmail_service().
        query: Gmail search string (same syntax as the Gmail search box).
        max_results: Maximum number of messages to retrieve.

    Returns:
        List of Gmail message resource dicts (with payload headers and snippet).
    """
    list_response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )

    message_refs = list_response.get("messages", [])
    if not message_refs:
        return []

    messages = []
    for ref in message_refs:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        messages.append(msg)

    return messages


def print_job_alerts(messages: list[dict]) -> None:
    """Pretty-print subject, sender, and snippet for each message."""
    if not messages:
        print("No job-alert emails found in the last 7 days.")
        print(f"Search query used: {JOB_ALERT_QUERY}")
        print(
            "Tip: Make sure you are subscribed to LinkedIn / Naukri job alerts "
            "and that those emails arrived in the last week."
        )
        return

    print(f"Found {len(messages)} job-alert email(s):\n")
    print("-" * 72)

    for index, message in enumerate(messages, start=1):
        payload = message.get("payload", {})
        headers = payload.get("headers", [])

        subject = _decode_header(_get_header(headers, "Subject"))
        sender = _decode_header(_get_header(headers, "From"))
        snippet = (message.get("snippet") or "").replace("\n", " ").strip()

        print(f"[{index}] Subject : {subject}")
        print(f"     From    : {sender}")
        print(f"     Snippet : {snippet}")
        print("-" * 72)


def ingest_job_alerts() -> list[dict]:
    """
    Main entry point: authenticate, search, print, and return raw messages.

    Returns:
        List of Gmail message dicts (empty list if none found).
    """
    service = get_gmail_service()
    messages = fetch_job_alert_messages(service)
    print_job_alerts(messages)
    return messages


if __name__ == "__main__":
    # Windows consoles often use cp1252; Gmail snippets may contain Unicode.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    print("Gmail job-alert ingestion — Week 1 test\n")

    try:
        ingest_job_alerts()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        print("\nRun first: python config/google_auth.py", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nError while fetching Gmail messages: {exc}", file=sys.stderr)
        sys.exit(1)
