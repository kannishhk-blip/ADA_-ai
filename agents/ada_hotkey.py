"""
Ada Hotkey (Native Windows RegisterHotKey Edition):
Listens for Ctrl+Alt+A anywhere on Windows using native Win32 User32 RegisterHotKey API.
Pops open the Ada dashboard in Edge App Mode instantly when pressed.
"""

import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DASHBOARD_URL = "http://localhost:8501"
DASHBOARD_PORT = 8501
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WINDOW_SIZE = "900,760"

# Win32 Constants
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_NOREPEAT = 0x4000
VK_A = 0x41  # Virtual key code for 'A'
HOTKEY_ID = 101

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
    """Opens (or refocuses) the small chromeless Ada app window."""
    print("\nHOTKEY TRIGGERED! Opening Ada App Window...")
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


def run_hotkey_listener():
    if not Path(EDGE_PATH).exists():
        print(f"Could not find Edge at expected path: {EDGE_PATH}")
        sys.exit(1)

    user32 = ctypes.windll.user32

    # Unregister hotkey first if previously registered
    user32.UnregisterHotKey(None, HOTKEY_ID)

    # Register Ctrl + Alt + A (MOD_CONTROL | MOD_ALT | MOD_NOREPEAT, 'A')
    modifiers = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
    if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, VK_A):
        modifiers = MOD_CONTROL | MOD_ALT
        if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, VK_A):
            print("Error: Hotkey Ctrl+Alt+A is already in use by another application.")
            return

    print("==========================================================")
    print(" ADA GLOBAL HOTKEY ACTIVE (Win32 Native Engine)")
    print(" Press [Ctrl] + [Alt] + [A] anywhere on Windows to launch Ada!")
    print("==========================================================")
    sys.stdout.flush()

    try:
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                open_app_window()
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except KeyboardInterrupt:
        print("\nStopping hotkey listener...")
    finally:
        user32.UnregisterHotKey(None, HOTKEY_ID)


if __name__ == "__main__":
    run_hotkey_listener()
