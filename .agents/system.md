# System

## Purpose
- InSighTube is a FastAPI web application that accepts a YouTube URL, extracts transcript text, generates a Korean AI summary, and returns the result through either JSON or server-rendered HTML.

## Current Boundaries
- Input sources: YouTube video URL plus summarize options.
- Processing scope: URL parsing, transcript retrieval, video metadata lookup, transcript truncation, LLM summarization, HTML/JSON response assembly.
- Output types: JSON API response and HTMX-rendered HTML partial.

## What Exists
- FastAPI app assembly in `app/main.py` with lifespan-based DB initialization
- Runtime settings loading and provider detection in `app/config.py`
- HTTP routes in `app/routers/summarize.py` and `app/routers/history.py`
- YouTube integration in `app/services/youtube.py`
- LLM summarization in `app/services/summarizer.py`
- History persistence in `app/services/history.py` (SQLite + aiosqlite)
- Daily Log persistence and file logging in `app/services/daily_log.py`
- Pydantic schemas and custom exceptions in `app/models/`
- Jinja2 templates and static assets for the UI (2-column layout with history side panel)
- Request monitoring logs at router and exception-handler boundaries
- Windows auto-start scripts in `scripts/` (Task Scheduler + crash recovery loop)
- Server output log at `logs/server.log`
- Daily activity logs at `logs/daily/` (date-rotated text files)
- History database at `data/history.db`
- Daily Log table in `data/history.db` (`daily_log`)

## What Does Not Exist in Current Implementation
- User accounts or authentication
- Background workers or queues
- Multi-step workflow orchestration beyond request-time async calls
- External API surface beyond the current summarize and history endpoints
