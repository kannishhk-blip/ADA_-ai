"""
WhatsApp agent (Week 5): sends a WhatsApp message using Twilio's API.

Setup required (one-time):
1. Sign up at https://www.twilio.com/try-twilio
2. Copy your Account SID and Auth Token from the Twilio Console
3. Connect your own WhatsApp to Twilio's sandbox (Messaging > Try it out >
   Send a WhatsApp message - send the join code shown to the sandbox number)
4. Put these in your .env file (never in this code file):
     TWILIO_ACCOUNT_SID=...
     TWILIO_AUTH_TOKEN=...
     TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
     MY_PHONE_NUMBER=+91XXXXXXXXXX

Run directly to send a test message:
    python -m agents.whatsapp_agent
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from twilio.rest import Client

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")
MY_PHONE_NUMBER = os.getenv("MY_PHONE_NUMBER")


def send_whatsapp_message(to_number: str, message: str):
    """
    Sends a WhatsApp message via Twilio.

    Args:
        to_number: Recipient's number, e.g. "+91XXXXXXXXXX"
        message: The text to send

    Returns:
        The Twilio message SID (a unique ID for the sent message)
    """
    if not all([ACCOUNT_SID, AUTH_TOKEN, WHATSAPP_FROM]):
        raise EnvironmentError(
            "Missing Twilio credentials. Check that TWILIO_ACCOUNT_SID, "
            "TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM are set in your .env file."
        )

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    sent = client.messages.create(
        from_=WHATSAPP_FROM,
        to=f"whatsapp:{to_number}",
        body=message,
    )
    return sent.sid


if __name__ == "__main__":
    if not MY_PHONE_NUMBER:
        print("Set MY_PHONE_NUMBER in your .env file first (e.g. +91XXXXXXXXXX).")
        sys.exit(1)

    test_message = "Hey! This is career-agent testing WhatsApp integration."
    print(f"Sending test WhatsApp message to {MY_PHONE_NUMBER}...")

    try:
        sid = send_whatsapp_message(MY_PHONE_NUMBER, test_message)
        print(f"Sent successfully. Message SID: {sid}")
        print("Check your WhatsApp - the message should arrive within seconds.")
    except Exception as e:
        print(f"Failed to send: {e}")
