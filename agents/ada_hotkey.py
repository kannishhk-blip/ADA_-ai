"""
Ada Hotkey: Multi-Hotkey Listener (Native Windows RegisterHotKey Edition).
Supports Ctrl+Alt+A, Ctrl+Shift+A, Win+Shift+A, and Alt+Shift+A.
Pops open the Ada dashboard in Edge App Mode instantly when pressed.
"""

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time
from pathlib import Path
import webbrowser

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_PORT = 8501

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_A = 0x41  # Virtual key code for 'A'

# Register multiple hotkey combinations so at least one is guaranteed to work!
HOTKEYS = [
    (101, MOD_CONTROL | MOD_ALT, "Ctrl + Alt + A"),
    (102, MOD_CONTROL | MOD_SHIFT, "Ctrl + Shift + A"),
    (103, MOD_WIN | MOD_SHIFT, "Win + Shift + A"),
    (104, MOD_ALT | MOD_SHIFT, "Alt + Shift + A"),
]

_streamlit_process = None


def is_dashboard_running() -> bool:
    try:
        requests.get(DASHBOARD_URL, timeout=1)
        return True
    except requests.exceptions.RequestException:
        return False


def start_dashboard_in_background():
    """Launches the Streamlit dashboard headlessly if not running."""
    global _streamlit_process
    print("Starting Ada dashboard server in background...")
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
            print("Dashboard is online.")
            return
        time.sleep(0.5)


def open_app_window():
    """Opens (or refocuses) the Ada app window."""
    print("\nHOTKEY TRIGGERED! Opening Ada App Window...")
    if not is_dashboard_running():
        start_dashboard_in_background()

    try:
        subprocess.Popen("cmd /c start msedge --app=http://localhost:8501 --window-size=900,760", shell=True)
    except Exception as exc:
        print(f"Edge launch notice: {exc}, opening browser...")
        webbrowser.open(DASHBOARD_URL)


def run_hotkey_listener():
    user32 = ctypes.windll.user32

    registered_keys = []
    for hk_id, modifiers, label in HOTKEYS:
        user32.UnregisterHotKey(None, hk_id)
        if user32.RegisterHotKey(None, hk_id, modifiers | MOD_NOREPEAT, VK_A) or \
           user32.RegisterHotKey(None, hk_id, modifiers, VK_A):
            registered_keys.append((hk_id, label))
        else:
            print(f"Note: {label} is in use by another system application.")

    if not registered_keys:
        print("Error: Could not register any hotkeys.")
        sys.exit(1)

    print("==========================================================")
    print(" ADA GLOBAL HOTKEY LISTENER ACTIVE (Win32 Engine)")
    print(" Press any of the following shortcuts anywhere on Windows:")
    for _, label in registered_keys:
        print(f"   -> [{label}]")
    print("==========================================================")
    sys.stdout.flush()

    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                open_app_window()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        print("\nStopping hotkey listener...")
    finally:
        for hk_id, _, _ in HOTKEYS:
            user32.UnregisterHotKey(None, hk_id)


if __name__ == "__main__":
    run_hotkey_listener()
