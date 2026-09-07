"""
Ada assistant (Week 5 extension): a Siri-style command interface.

Type a command like:
    Ada, send hi to my gf
    Ada, message mom saying I'll be late
    Ada, call dad

...and it figures out WHO to contact (using your contacts.json) and WHAT
to send/say, then uses whatsapp_agent.py / call_agent.py to actually do it.

Setup:
1. Edit data/contacts.json - replace the placeholder numbers with real
   phone numbers for people you want to message/call by nickname.
   Format: "nickname": "+91XXXXXXXXXX"

Run interactively:
    python -m agents.ada_assistant

Or run a single command directly:
    python -m agents.ada_assistant "send hi to my gf"
"""

import json
import re
import subprocess
import sys
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.whatsapp_agent import send_whatsapp_message
from agents.call_agent import make_call_with_message

CONTACTS_PATH = PROJECT_ROOT / "data" / "contacts.json"
APPS_PATH = PROJECT_ROOT / "data" / "apps.json"

# Words that signal "this is a call" vs "this is a message"
CALL_KEYWORDS = ["call", "phone", "ring"]
MESSAGE_KEYWORDS = ["send", "message", "text", "whatsapp", "tell", "say"]
OPEN_KEYWORDS = ["open", "launch", "start"]


def load_apps() -> dict:
    if not APPS_PATH.exists():
        return {}
    return json.loads(APPS_PATH.read_text())


def find_app_in_text(text: str, apps: dict):
    """Finds which known app/website is mentioned in an 'open ...' command."""
    text_lower = text.lower()
    for name, info in apps.items():
        if re.search(rf"\b{re.escape(name.lower())}\b", text_lower):
            return name, info
    return None, None


def open_app_or_site(name: str, info: dict):
    if info["type"] == "url":
        print(f"Opening {name} in your browser...")
        webbrowser.open(info["target"])
    elif info["type"] == "app":
        print(f"Launching {name}...")
        subprocess.Popen(info["target"], shell=True)


def load_contacts() -> dict:
    if not CONTACTS_PATH.exists():
        raise FileNotFoundError(
            f"No contacts file found at {CONTACTS_PATH}. Create it first."
        )
    return json.loads(CONTACTS_PATH.read_text())


def find_contact_in_text(text: str, contacts: dict):
    """Finds which known contact nickname is mentioned in the command."""
    text_lower = text.lower()
    for nickname, number in contacts.items():
        # Matches "gf", "my gf", "to gf", etc. - just checks the word appears
        if re.search(rf"\b{re.escape(nickname.lower())}\b", text_lower):
            return nickname, number
    return None, None


def extract_message_text(text: str, nickname: str) -> str:
    """
    Pulls out the actual message content from a command like:
    "send hi to my gf" -> "hi"
    "message mom saying I'll be late" -> "I'll be late"
    """
    text_lower = text.lower()

    # Pattern: "... saying <message>" or "... that <message>"
    match = re.search(r"(?:saying|that)\s+(.+)", text_lower)
    if match:
        return match.group(1).strip()

    # Pattern: "send <message> to <nickname>"
    match = re.search(rf"(?:send|message|text|tell)\s+(.+?)\s+to\s+(?:my\s+)?{re.escape(nickname.lower())}", text_lower)
    if match:
        return match.group(1).strip()

    # Fallback: strip known command words and the contact name, use what's left
    words_to_remove = CALL_KEYWORDS + MESSAGE_KEYWORDS + [nickname.lower(), "my", "to"]
    words = [w for w in text_lower.split() if w not in words_to_remove]
    return " ".join(words).strip() or "Hello from Ada."


def process_command(command: str):
    command_lower = command.lower()

    # Check "open X" commands first (opening WhatsApp/Instagram/etc.)
    if any(word in command_lower for word in OPEN_KEYWORDS):
        apps = load_apps()
        app_name, app_info = find_app_in_text(command, apps)
        if app_name:
            open_app_or_site(app_name, app_info)
            return
        else:
            print(f"I don't know how to open that yet. Known apps: {list(apps.keys())}")
            print(f"Add new ones to {APPS_PATH}")
            return

    contacts = load_contacts()
    nickname, number = find_contact_in_text(command, contacts)

    if not nickname:
        print(f"I don't recognize anyone in that command. Known contacts: {list(contacts.keys())}")
        print(f"Add new people to {CONTACTS_PATH}")
        return

    is_call = any(word in command_lower for word in CALL_KEYWORDS) and \
              not any(word in command_lower for word in ["message", "text", "whatsapp"])

    if is_call:
        message = extract_message_text(command, nickname) or "Hello, this is Ada calling on behalf of Kannishhkram."
        print(f"Calling {nickname} ({number})...")
        sid = make_call_with_message(number, message)
        print(f"Call placed. SID: {sid}")
    else:
        message = extract_message_text(command, nickname)
        print(f"Sending WhatsApp to {nickname} ({number}): \"{message}\"")
        sid = send_whatsapp_message(number, message)
        print(f"Message sent. SID: {sid}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single command passed directly: python -m agents.ada_assistant "send hi to my gf"
        process_command(" ".join(sys.argv[1:]))
    else:
        # Interactive mode
        print("Ada assistant ready. Type a command, or 'quit' to exit.")
        print("Examples: 'send hi to my gf', 'call mom', 'message dad saying running late'\n")
        while True:
            command = input("Ada, ").strip()
            if command.lower() in ("quit", "exit"):
                break
            if not command:
                continue
            try:
                process_command(command)
            except Exception as e:
                print(f"Something went wrong: {e}")
            print()
