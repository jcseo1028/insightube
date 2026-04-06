# Change 0002 — Windows startup auto-run for server

## Status
- Implemented

## Goal
- Start the existing FastAPI server automatically on this Windows machine when the computer boots.

## Why this is safe
- Operational and isolated from application logic.
- Does not require route, schema, template, service, or summarization changes.
- Reuses the current server entrypoint and local virtual environment.

## Current architecture references
- App entrypoint is `app.main:app`.
- Current manual run command is `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`.
- The project is currently run from a local Windows virtual environment in the repository root.

## Scope
- Add minimal Windows-specific startup support around the existing server command.
- Prefer a small PowerShell helper and a small setup/registration script or equivalent minimal setup artifact.
- Keep the working directory at the repository root.
- Update startup documentation in `README.md` only as needed.

## Expected behavior to preserve
- The application entrypoint remains `app.main:app`.
- Existing manual startup continues to work.
- No API, template, schema, or exception contract changes.
- No application feature changes.

## Files to touch
- `README.md`
- Prefer one or two small Windows-focused setup scripts only if needed for reliable startup.

## Out of scope
- Linux or macOS auto-start support.
- Converting the app into a Windows service.
- Deployment redesign, containerization, or reverse proxy setup.
- Application code changes unrelated to startup.

## Acceptance criteria
- A Windows startup path exists that launches the existing app automatically on boot.
- The startup path uses the repository virtual environment and repository root.
- Manual startup instructions remain valid.
- No app contracts or runtime behavior change beyond startup automation.

## Copilot Agent instructions
- Keep this change operational and minimal.
- Reuse the current run command unless a small adjustment is strictly required for startup reliability.
- Avoid changing app code unless startup support cannot be added without it.
- Record the finalized implementation details in `.agents/changes/`.

## Implemented result
- Added `scripts/start-server.vbs`: VBS wrapper — `WScript.Shell.Run` with window style 0 makes the entire process tree invisible (no console window).
- Added `scripts/run_server.py`: Python server launcher with auto-restart loop (max 10 consecutive failures within 60 s, 5 s delay). Uses `CREATE_NO_WINDOW` (`0x08000000`) flag on `subprocess.run()` so the child `python.exe` also creates no console. Logs to `logs/server.log`.
- Added `scripts/start-server.ps1`: original PowerShell launcher (retained for manual/debugging use).
- Added `scripts/setup-task.ps1`: registers/unregisters `InSighTube-Server` Windows Task Scheduler task (AtLogOn trigger, Limited RunLevel).
- Updated `README.md` with auto-start and crash recovery instructions.
- No application code changes. All existing contracts preserved.

### Launch chain
```
Task Scheduler (AtLogOn)
  → wscript.exe  start-server.vbs      (VBS: Run ..., 0, False — hidden window)
    → pythonw.exe  run_server.py        (no console host)
      → python.exe -m uvicorn ...       (CREATE_NO_WINDOW — no console created)
```
