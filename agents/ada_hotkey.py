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

Setup:
    pip install keyboard requests

Run (keep this running in the background):
    python -m agents.ada_hotkey

See the "Autostart" note at the bottom of this file to have this launch
automatically every time you log into Windows.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

import keyboard
import requests

HOTKEY = "ctrl+alt+a"
DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_PORT = 8501

# Windows ships Edge at this path on virtually every install.
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# Window size for the small popup app window (width, height in pixels)
WINDOW_SIZE = "900,760"  # wide enough that Streamlit's sidebar doesn't auto-collapse

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

    # Wait for it to actually come up before opening the window
    for _ in range(30):  # up to ~15 seconds
        if is_dashboard_running():
            print("Dashboard is up.")
            return
        time.sleep(0.5)
    print("Dashboard is taking a while to start - opening the window anyway.")


def open_app_window():
    """Opens (or refocuses) the small chromeless Ada app window."""
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
        print(
            "Could not find Edge at the expected path:\n  " + EDGE_PATH +
            "\nIf your Edge is installed somewhere else, edit EDGE_PATH at "
            "the top of this file to match."
        )
        sys.exit(1)

    print(f"Ada Hotkey is running. Press {HOTKEY.upper()} anywhere to open Ada.")
    print("Press Ctrl+C in this terminal to stop.\n")

    keyboard.add_hotkey(HOTKEY, open_app_window)
    keyboard.wait()  # keeps the script running, listening forever

"""
-------------------------------------------------------------------------
AUTOSTART (optional) - make Ada Hotkey launch automatically when Windows
starts, so Ctrl+Alt+A always works without you manually running a command:

1. Press Win+R, type: shell:startup, press Enter
   (this opens your Windows Startup folder)
2. Right-click inside that folder -> New -> Shortcut
3. For the location, enter:
     pythonw -m agents.ada_hotkey
   (pythonw instead of python hides the console window)
4. Set "Start in" to your project folder: D:\\Twillo\\career-agent
5. Save

Now Ada Hotkey starts silently every time you log into Windows, and the
first Ctrl+Alt+A press will start the dashboard + open the app window.
-------------------------------------------------------------------------
"""
