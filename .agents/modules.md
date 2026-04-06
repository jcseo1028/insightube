# Modules

## `app/main.py`
- Creates the FastAPI app.
- Mounts static files and configures Jinja2 templates.
- Registers the summarize router.
- Serves the index page.
- Defines exception handlers for URL, transcript, and summarization failures.
- Logs error outcomes at each exception handler.

## `app/config.py`
- Loads `.env`.
- Detects current LLM provider from `GITHUB_TOKEN` or `OPENAI_API_KEY`.
- Produces `Settings` with model, base URL, transcript length limit, and summary language.

## `app/routers/summarize.py`
- Owns the summarize endpoints.
- Parses request body or form inputs into current options shape.
- Orchestrates transcript fetch, metadata fetch, summarization, and response assembly.
- Logs request start, video_id, and completion with elapsed time for both API and HTMX paths.

## `app/services/youtube.py`
- Extracts YouTube video IDs from supported URL forms.
- Fetches transcript text with fallback to generated captions.
- Formats transcript into timestamped paragraphs.
- Fetches metadata with `yt-dlp`.

## `app/services/summarizer.py`
- Creates the current `ChatOpenAI` client from settings.
- Builds prompts based on detail level and output schema.
- Chooses short-text or long-text summarization path.
- Uses LangChain output parsing into `SummaryResult`.

## `app/models/schemas.py`
- Defines request, response, summary, metadata, option, and error schemas.
- Holds current option ranges and enum values.

## `app/models/exceptions.py`
- Defines repository-specific exceptions used by routes and services.

## `app/templates/`
- `base.html`: shell layout and CDN includes.
- `index.html`: input form and HTMX wiring.
- `partials/summary_result.html`: rendered result card and transcript copy UI.

## `app/static/`
- `js/app.js`: clipboard-based YouTube URL autofill helper.
- `css/style.css`: HTMX loading indicator styles.

## `tests/`
- Covers URL parsing, transcript/metadata behavior, summarize service behavior, form option parsing, and basic HTTP responses.

## `scripts/`
- `start-server.vbs`: VBS wrapper — `WScript.Shell.Run` with window style 0, hides the entire process tree (no console window appears).
- `run_server.py`: Python server launcher with auto-restart loop (max 10 consecutive failures within 60 s). Spawns uvicorn via `subprocess.run()` with `CREATE_NO_WINDOW` flag. Logs to `logs/server.log`.
- `start-server.ps1`: original PowerShell launcher retained for manual use / debugging.
- `setup-task.ps1`: registers or unregisters the `InSighTube-Server` Windows Task Scheduler task. Launch chain: `wscript.exe` → VBS → `pythonw.exe` → `run_server.py` → uvicorn.
