# System

## Purpose
- InSighTube is a FastAPI web application that accepts a YouTube URL, extracts transcript text, generates a Korean AI summary, and returns the result through either JSON or server-rendered HTML.

## Current Boundaries
- Input sources: YouTube video URL plus summarize options.
- Processing scope: URL parsing, transcript retrieval, video metadata lookup, transcript truncation, LLM summarization, HTML/JSON response assembly.
- Output types: JSON API response and HTMX-rendered HTML partial.

## What Exists
- FastAPI app assembly in `app/main.py`
- Runtime settings loading and provider detection in `app/config.py`
- HTTP routes in `app/routers/summarize.py`
- YouTube integration in `app/services/youtube.py`
- LLM summarization in `app/services/summarizer.py`
- Pydantic schemas and custom exceptions in `app/models/`
- Jinja2 templates and static assets for the UI

## What Does Not Exist in Current Implementation
- Database or persistent storage
- User accounts or authentication
- Background workers or queues
- Multi-step workflow orchestration beyond request-time async calls
- External API surface beyond the current summarize endpoints
