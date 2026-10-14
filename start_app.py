"""Launch Notes Bridge in standalone App mode.

Cross-platform desktop launcher: checks if server.py is running on port 7892,
starts it in the background if needed, and launches a dedicated standalone
frameless app window using Edge or Chrome (falling back to default browser).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PORT = 7892
URL = f"http://localhost:{PORT}"


def is_running() -> bool:
    try:
        with urllib.request.urlopen(f"{URL}/api/notes", timeout=1) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    if not is_running():
        if sys.platform == "win32":
            pythonw = Path(sys.executable).parent / "pythonw.exe"
            exe = str(pythonw) if pythonw.exists() else sys.executable
            subprocess.Popen(
                [exe, str(PROJECT_DIR / "server.py"), str(PORT)],
                cwd=str(PROJECT_DIR),
            )
        else:
            subprocess.Popen(
                [sys.executable, str(PROJECT_DIR / "server.py"), str(PORT)],
                cwd=str(PROJECT_DIR),
            )
        time.sleep(1)

    app_opened = False
    if sys.platform == "win32":
        edge_paths = [
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in edge_paths:
            if os.path.exists(p):
                subprocess.Popen([p, f"--app={URL}", "--window-size=920,880"])
                app_opened = True
                break

    if not app_opened:
        webbrowser.open(URL)


if __name__ == "__main__":
    main()
