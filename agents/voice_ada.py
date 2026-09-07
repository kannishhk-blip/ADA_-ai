"""
Voice Ada (Week 5 extension): listens through your microphone for "Ada" as
a wake word, then processes whatever you say after it as a command - same
commands as ada_assistant.py (open apps, send messages, make calls), just
spoken instead of typed.

Setup:
    pip install SpeechRecognition pyaudio

    If pyaudio fails to install on Windows, run this instead:
        pip install pipwin
        pipwin install pyaudio

How it works:
1. Your microphone stays "listening" in short bursts
2. Each burst gets converted to text using Google's free speech-recognition
   web service (no API key needed for basic/personal use)
3. If the text contains "ada", everything after that word is treated as
   a command and passed to the same logic as ada_assistant.py

Run:
    python -m agents.voice_ada
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import speech_recognition as sr
from agents.ada_assistant import process_command

WAKE_WORD = "ada"


def extract_command_after_wake_word(heard_text: str) -> str:
    """
    'hey ada open insta' -> 'open insta'
    'ada send hi to mom' -> 'send hi to mom'
    """
    text_lower = heard_text.lower()
    idx = text_lower.find(WAKE_WORD)
    if idx == -1:
        return ""
    return heard_text[idx + len(WAKE_WORD):].strip()


def listen_once(recognizer: sr.Recognizer, microphone: sr.Microphone) -> str:
    """Listens for one phrase and returns the recognized text (or '' on failure)."""
    with microphone as source:
        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=8)
        except sr.WaitTimeoutError:
            return ""

    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return ""  # couldn't understand the audio
    except sr.RequestError as e:
        print(f"Speech recognition service error: {e}")
        return ""


if __name__ == "__main__":
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    print("Voice Ada is listening. Say 'Ada' followed by a command.")
    print("Examples: 'Ada open instagram', 'Hey Ada send hi to my gf'")
    print("Press Ctrl+C to stop.\n")

    print("Calibrating for background noise, stay quiet for a second...")
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    print("Ready. Listening...\n")

    try:
        while True:
            heard = listen_once(recognizer, microphone)
            if not heard:
                continue

            print(f"Heard: \"{heard}\"")

            if WAKE_WORD in heard.lower():
                command = extract_command_after_wake_word(heard)
                if command:
                    print(f"Command: \"{command}\"")
                    try:
                        process_command(command)
                    except Exception as e:
                        print(f"Something went wrong: {e}")
                else:
                    print("Heard the wake word but no command after it - try again.")
                print()
    except KeyboardInterrupt:
        print("\nVoice Ada stopped.")
