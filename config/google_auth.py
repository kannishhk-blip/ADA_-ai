"""
Google OAuth helper for Gmail + Google Calendar (Desktop app flow).

=============================================================================
MANUAL SETUP — do this once in Google Cloud Console before running this file
=============================================================================

1. Go to https://console.cloud.google.com/ and create a new project
   (e.g. "career-agent").

2. Enable APIs for that project:
   - Gmail API          → https://console.cloud.google.com/apis/library/gmail.googleapis.com
   - Google Calendar API → https://console.cloud.google.com/apis/library/calendar-json.googleapis.com

3. Configure the OAuth consent screen:
   - APIs & Services → OAuth consent screen
   - User type: External (fine for personal projects)
   - Add your Gmail address under "Test users" so you can sign in while
     the app is in "Testing" mode
   - Add scopes later is OK; this script requests them at login time

4. Create OAuth credentials:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON file and save it as:
       config/credentials.json

5. Run this module once to complete the browser login:
       python config/google_auth.py

   A token.json file will be saved next to credentials.json so future runs
   reuse your session without opening the browser again.

=============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Folder where this file lives — credentials.json and token.json go here.
CONFIG_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

# Scopes define what our app is allowed to do on your Google account.
# Week 1 only reads Gmail; later weeks will compose mail and manage Calendar.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
]


def get_credentials() -> Credentials:
    """
    Load saved OAuth credentials, or run the browser login flow on first use.

    Returns:
        Valid google.oauth2.credentials.Credentials object.

    Raises:
        FileNotFoundError: If credentials.json has not been downloaded yet.
    """
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"\nMissing OAuth client file: {CREDENTIALS_FILE}\n\n"
            "Download it from Google Cloud Console (Desktop OAuth client) and "
            "save it as config/credentials.json.\n"
            "See the setup comments at the top of config/google_auth.py.\n"
        )

    creds: Credentials | None = None

    # Reuse token from a previous login if it still exists.
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # Refresh expired tokens automatically, or start a fresh login.
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            # Token was revoked, expired, or Google rejected it (invalid_grant).
            # Delete it and ask the user to sign in again in the browser.
            if TOKEN_FILE.exists():
                TOKEN_FILE.unlink()
            creds = _run_browser_login()
    else:
        creds = _run_browser_login()

    # Persist token so the next script run skips the browser step.
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds


def _run_browser_login() -> Credentials:
    """Open the browser for a new Google Desktop OAuth login."""
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    return flow.run_local_server(port=0)


def get_gmail_service():
    """Build an authenticated Gmail API client."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def get_calendar_service():
    """Build an authenticated Google Calendar API client (used in Week 3+)."""
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


if __name__ == "__main__":
    print("Starting Google OAuth login (Gmail + Calendar)...")
    print(f"Looking for credentials at: {CREDENTIALS_FILE}\n")

    try:
        gmail = get_gmail_service()
        profile = gmail.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress", "unknown")

        print("Success! You are authenticated.")
        print(f"  Gmail account : {email}")
        print(f"  Token saved to: {TOKEN_FILE}")
        print("\nYou can now run: python agents/gmail_ingest.py")
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\nAuthentication failed: {exc}", file=sys.stderr)
        print(
            "Check that Gmail API and Calendar API are enabled, and that your "
            "email is listed as a test user on the OAuth consent screen.",
            file=sys.stderr,
        )
        sys.exit(1)
