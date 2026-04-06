"""InSighTube server launcher with auto-restart on crash.

Designed to be run via pythonw.exe (no console window).
Task Scheduler calls: pythonw.exe scripts/run_server.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_ROOT / "venv" / "Scripts" / "python.exe"

# Windows: subprocess 에서 콘솔 창이 생성되지 않도록 하는 플래그
_CREATE_NO_WINDOW = 0x0800_0000 if os.name == "nt" else 0
LOG_FILE = PROJECT_ROOT / "logs" / "server.log"
RESTART_DELAY_SEC = 5
MAX_CONSECUTIVE_FAILURES = 10
STABLE_UPTIME_SEC = 60


def _log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def main() -> None:
    failures = 0

    while failures < MAX_CONSECUTIVE_FAILURES:
        _log("Server starting...")
        start = time.monotonic()

        proc = subprocess.run(
            [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app",
             "--host", "0.0.0.0", "--port", "8000"],
            cwd=str(PROJECT_ROOT),
            stdout=open(LOG_FILE, "a", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            creationflags=_CREATE_NO_WINDOW,
        )

        uptime = time.monotonic() - start
        _log(f"Server exited (code={proc.returncode}, uptime={uptime:.1f}s)")

        if uptime > STABLE_UPTIME_SEC:
            failures = 0
        else:
            failures += 1

        if failures < MAX_CONSECUTIVE_FAILURES:
            _log(f"Restarting in {RESTART_DELAY_SEC}s... "
                 f"(consecutive failures: {failures}/{MAX_CONSECUTIVE_FAILURES})")
            time.sleep(RESTART_DELAY_SEC)

    _log(f"Max consecutive failures reached ({MAX_CONSECUTIVE_FAILURES}). Stopping.")


if __name__ == "__main__":
    main()
