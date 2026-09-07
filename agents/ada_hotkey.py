"""
Ada Hotkey v2 (Week 5 extension): press Ctrl+Alt+A anywhere on your desktop
to pop open the Ada dashboard as a small, chromeless app window - like
ChatGPT's or Gemini's desktop launcher - instead of a full browser tab.

What it does when you press the hotkey:
1. Makes sure the Streamlit dashboard is running in the background
   (starts it automatically the first time, headless - no extra tab opens)
2. Opens a small "app mode" window (using Edge, built into Windows) pointed
   at the dashboard - no address bar, no tabs, just the app, titled
   "ADA Agent" - and brings it to the front if it's already open
"""

import subprocess
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

HOTKEY = "ctrl+alt+a"
DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_PORT = 8501

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WINDOW_SIZE = "900,760"

_streamlit_process = None


def is_dashboard_running() -> bool:
    try:
        requests.get(DASHBOARD_URL, timeout=1)
        return True
    except requests.exceptions.RequestException:
        return False


def start_dashboard_in_background():
    """Launches the Streamlit dashboard headlessly (no browser tab opens)."""
    global _streamlit_process
    print("Starting Ada dashboard in the background...")
    _streamlit_process = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            str(PROJECT_ROOT / "agents" / "dashboard.py"),
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
            "--server.port", str(DASHBOARD_PORT),
        ],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):
        if is_dashboard_running():
            print("Dashboard is up.")
            return
        time.sleep(0.5)
    print("Dashboard is taking a while to start - opening the window anyway.")


def open_app_window():
    """Opens (or refocuses) the small chromeless Ada app window."""
    print("Hotkey triggered! Opening Ada desktop window...")
    if not is_dashboard_running():
        start_dashboard_in_background()

    subprocess.Popen(
        [
            EDGE_PATH,
            f"--app={DASHBOARD_URL}",
            f"--window-size={WINDOW_SIZE}",
            "--window-position=480,120",
        ]
    )


if __name__ == "__main__":
    if not Path(EDGE_PATH).exists():
        print(f"Could not find Edge at expected path: {EDGE_PATH}")
        sys.exit(1)

    print(f"Ada Hotkey is running. Press {HOTKEY.upper()} anywhere to open Ada.")
    print("Press Ctrl+C in this terminal to stop.\n")

    try:
        from pynput import keyboard as pynput_keyboard
        with pynput_keyboard.GlobalHotKeys({
            '<ctrl>+<alt>+a': open_app_window,
            '<ctrl>+<alt>+A': open_app_window,
        }) as h:
            h.join()
    except Exception as exc:
        print(f"pynput fallback: {exc}")
        import keyboard
        keyboard.add_hotkey(HOTKEY, open_app_window)
        keyboard.wait()
