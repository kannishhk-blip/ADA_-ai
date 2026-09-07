"""
Call agent (Week 5): places a phone call using Twilio and speaks a message
using text-to-speech - no recording needed, Twilio generates the voice.

Uses the same .env credentials as whatsapp_agent.py.

Run directly to place a test call:
    python -m agents.call_agent
"""

import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from twilio.rest import Client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER")

# Twilio needs a "from" number capable of voice calls. On the free trial,
# Twilio gives you one free phone number automatically - find it under
# Twilio Console > Phone Numbers > Manage > Active Numbers, and put it here:
TWILIO_VOICE_FROM = os.getenv("TWILIO_VOICE_FROM")


def make_call_with_message(to_number: str, spoken_message: str):
    """
    Places a phone call and speaks the given message using Twilio's
    built-in text-to-speech (no audio file needed).

    Args:
        to_number: Number to call, e.g. "+91XXXXXXXXXX"
        spoken_message: What Twilio should say when the call connects

    Returns:
        The Twilio call SID
    """
    if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_VOICE_FROM]):
        raise EnvironmentError(
            "Missing Twilio credentials. Check TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_VOICE_FROM are set in your .env file."
        )

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # TwiML (Twilio Markup Language) tells Twilio what to do on the call.
    # <Say> makes Twilio speak the text aloud using text-to-speech.
    twiml = f"<Response><Say>{escape(spoken_message)}</Say></Response>"

    call = client.calls.create(
        from_=TWILIO_VOICE_FROM,
        to=to_number,
        twiml=twiml,
    )
    return call.sid


if __name__ == "__main__":
    if not MY_PHONE_NUMBER:
        print("Set MY_PHONE_NUMBER in your .env file first (e.g. +91XXXXXXXXXX).")
        sys.exit(1)

    test_message = "Hello. This is a test call from your career agent project."
    print(f"Calling {MY_PHONE_NUMBER}...")

    try:
        sid = make_call_with_message(MY_PHONE_NUMBER, test_message)
        print(f"Call placed successfully. Call SID: {sid}")
        print("Your phone should ring in a few seconds.")
    except Exception as e:
        print(f"Failed to place call: {e}")
