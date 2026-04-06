# Pipeline

## Request Paths
- `GET /` renders the main page.
- `POST /api/summarize` accepts JSON and returns `SummarizeResponse`.
- `POST /summarize` accepts form data and returns the `partials/summary_result.html` template.

## Current Runtime Flow
1. Receive a YouTube URL and optional summarize settings.
2. Parse and validate the video ID with `extract_video_id()`.
3. Load runtime settings with `get_settings()`.
4. In parallel:
   - fetch transcript via `get_transcript()`
   - fetch metadata via `get_video_metadata()`
5. Truncate transcript to `max_transcript_length` if needed.
6. Summarize transcript with `summarize_transcript()`.
7. Build response payload or template context.
8. Return JSON for API clients or HTML partial for HTMX requests.

## Transcript Flow
- Preferred languages are Korean then English.
- If direct transcript lookup fails, generated transcripts are attempted.
- Transcript text is formatted into timestamped paragraphs.

## Summarization Flow
- Short transcript: single structured summary call.
- Long transcript: split into chunks, summarize chunks, then reduce to final structured result.
- GitHub Models requests are concurrency-limited in the map phase.

## Error Flow
- `InvalidURLError` -> 400
- `TranscriptNotFoundError` -> 404
- `SummarizationError` -> 500
- Exception handlers return HTML fragments when the request includes `HX-Request`, and JSON error payloads otherwise.
- All errors are logged at the exception handler boundary with path and message.

## Observability
- Summarize requests log: request start, video_id extraction, completion with elapsed time.
- Logs are tagged `[API]` or `[HTMX]` per request path.
- Error handlers log at WARNING (`InvalidURLError`, `TranscriptNotFoundError`) or ERROR (`SummarizationError`) level.

## Server Lifecycle (Windows)
- Task Scheduler (AtLogOn) → `wscript.exe` → `start-server.vbs` → `pythonw.exe` → `run_server.py` → uvicorn.
- `start-server.vbs`: VBS wrapper with window style 0 — no console window appears.
- `run_server.py`: auto-restart loop (max 10 consecutive failures within 60 s). Uses `CREATE_NO_WINDOW` subprocess flag.
- `setup-task.ps1`: registers/unregisters the scheduled task.
- `start-server.ps1`: retained for manual use / debugging.
- Server stdout/stderr is written to `logs/server.log`.
