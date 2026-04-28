# Modules

## `app/main.py`

- Creates the FastAPI app with lifespan-based startup (DB initialization).
- Mounts static files and configures Jinja2 templates.
- Registers the summarize, history, daily_log, and reading routers.
- Serves the index page.
- Defines exception handlers for URL, transcript, and summarization failures.
- Logs error outcomes at each exception handler and writes failure events to daily log files.

## `app/config.py`

- Loads `.env`.
- Detects current LLM provider from `GITHUB_TOKEN` or `OPENAI_API_KEY`.
- Produces `Settings` with model, base URL, transcript length limit, summary language, and Notion reading DB settings (`NOTION_API_KEY`, `NOTION_READING_DB_ID`, `NOTION_READING_DONE_PROPERTY`).

## `app/routers/summarize.py`

- Owns the summarize endpoints.
- Parses request body or form inputs into current options shape.
- Missing or invalid form `detail_level` currently falls back to `detailed`.
- Orchestrates transcript fetch, metadata fetch, summarization, and response assembly.
- Saves result to history DB after successful summarization.
- Saves lightweight record to daily_log DB and writes file log events (request, success, failure).
- HTMX response triggers `historyUpdated` event for side panel refresh.
- Logs request start, video_id, and completion with elapsed time for both API and HTMX paths.

## `app/routers/history.py`

- Owns the history CRUD endpoints (JSON API + HTMX partials).
- `GET /api/history` — recent history list.
- `GET /api/history/{id}` — single history detail.
- `DELETE /api/history/{id}` — delete history.
- `GET /history/panel` — side panel HTML partial.
- `GET /history/{id}` — renders history detail using `summary_result.html`.

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

## `app/services/history.py`

- Manages SQLite history DB via aiosqlite.
- `init_db()` — creates table and index on startup.
- `save()` — inserts a summarization result, returns row id.
- `list_recent()` — returns recent items without transcript (side panel).
- `get_by_id()` — returns full record with parsed key_points/keywords.
- `delete_by_id()` — removes a record.
- DB file: `data/history.db`.

## `app/services/daily_log.py`

- Manages the `daily_log` SQLite table in `data/history.db` via aiosqlite.
- `init_db()` — creates table and date index on startup.
- `save()` — inserts a lightweight log entry (video_id, title, channel, one_line, detail_level).
- `get_by_date()` — returns log items for a specific date (default: today KST).
- `get_recent_days()` — returns date-grouped summaries for the last N days.
- File logging via `TimedRotatingFileHandler` to `logs/daily/`.
- `log_request()`, `log_success()`, `log_failure()` — write structured text events.

## `app/routers/daily_log.py`

- Owns the daily log read endpoints (JSON API only, no HTMX partials yet).
- `GET /api/daily-log` — returns log items for a specific date.
- `GET /api/daily-log/recent` — returns date-grouped summaries.

## `app/routers/reading.py`

- Owns the today's reading endpoints (Notion 독서 DB 기반).
- `GET /reading/today` — popup page (server-rendered template).
- `GET /api/reading/today-summary` — randomly picks one completed page from Notion DB and returns a summary.
- Maps domain Notion exceptions (`NoCompletedPagesError`, `NotionAuthError`, `NotionNotSharedError`, `NotionRateLimitError`, `NotionSchemaMismatchError`) to JSON error payloads.

## `app/services/notion.py`

- Calls Notion API via `httpx.AsyncClient`.
- `fetch_completed_pages()` — queries the reading DB filtered by `읽기 종료` date `is_not_empty`.
- `fetch_page_block_text()` — flattens the first level of page block children into plain text.
- `extract_title()`, `extract_meta()` — parse title and metadata properties (저자/역자, 출판사, 분류, 독서 유형, 평가/기대 점수, 읽기 시작/종료).
- `build_summary_input()` — combines attribute context, 메모, 비고, and body text into LLM input. Marks `used_fallback=True` when body is empty.
- `pick_random_completed()` — returns a random page; raises `NoCompletedPagesError` when empty.
- Translates HTTP status / Notion error codes into domain exceptions in `app/models/exceptions.py`.

## `app/models/schemas.py`

- Defines request, response, summary, metadata, option, error, and history schemas.
- Holds current option ranges and enum values.
- `SummarizeOptions.detail_level` defaults to `detailed`.
- `HistoryListItem` — lightweight history item for side panel.
- `HistoryDetail` — full history item with key_points/keywords/transcript.
- `DailyLogItem` — lightweight daily log entry.
- `DailyLogSummary` — date-grouped daily log with count and items.
- `ReadingPageMeta`, `ReadingSummaryData`, `ReadingSummaryResponse` — Notion 독서 페이지 요약 응답용.

## `app/models/exceptions.py`

- Defines repository-specific exceptions used by routes and services.
- Notion 연동용: `NotionError`, `NotionAuthError`, `NotionNotSharedError`, `NotionRateLimitError`, `NotionSchemaMismatchError`, `NoCompletedPagesError`.

## `app/templates/`

- `base.html`: shell layout with 2-column (main + sidebar) structure and CDN includes.
- `index.html`: input form, HTMX wiring, history side panel integration, and "오늘의 독서 내용" 버튼.
- `partials/summary_result.html`: rendered result card and transcript copy UI.
- `partials/history_panel.html`: side panel history list (loaded via HTMX).
- `reading_popup.html`: 오늘의 독서 팝업(랜덤 한 권 요약 결과 표시).

## `app/static/`

- `js/app.js`: clipboard-based YouTube URL autofill helper, plus `openReadingToday()` which opens `/reading/today` in a new window.
- `css/style.css`: HTMX loading indicator styles.

## `tests/`

- Covers URL parsing, transcript/metadata behavior, summarize service behavior, form option parsing, basic HTTP responses, history CRUD, history router endpoints, daily log DB CRUD, daily log file logging, daily log router endpoints, and Notion 독서 파서/라우터(`test_reading.py`).

## `scripts/`

- `start-server.vbs`: VBS wrapper — `WScript.Shell.Run` with window style 0, hides the entire process tree (no console window appears).
- `run_server.py`: Python server launcher with auto-restart loop (max 10 consecutive failures within 60 s). Spawns uvicorn via `subprocess.run()` with `CREATE_NO_WINDOW` flag. Logs to `logs/server.log`.
- `start-server.ps1`: original PowerShell launcher retained for manual use / debugging.
- `setup-task.ps1`: registers or unregisters the `InSighTube-Server` Windows Task Scheduler task. Launch chain: `wscript.exe` → VBS → `pythonw.exe` → `run_server.py` → uvicorn.
