# Change 0003 — Add request monitoring logs

## Status
- Implemented

## Goal
- Add minimal logs that make it easier to observe server behavior for client summarize requests.

## Why this is safe
- Small, isolated observability change.
- Fits the current FastAPI + router/service structure.
- Can be added without changing API responses, templates, schemas, or summarization behavior.

## Current architecture references
- Logging is initialized in `app/main.py`.
- Request orchestration for summarize flows lives in `app/routers/summarize.py`.
- Current error handling is centralized in FastAPI exception handlers in `app/main.py`.

## Scope
- Add focused logs around summarize request handling.
- Prefer logging request start, request end, error outcome, and basic timing.
- Keep logs at the app or router boundary; do not spread logging across unrelated modules.

## Expected behavior to preserve
- Existing routes and response shapes remain unchanged.
- Existing exception handlers remain the source of error responses.
- No transcript body, API keys, or other sensitive values are logged.
- No template or UI behavior changes.

## Suggested fields to log
- request path
- request type (`/api/summarize` or `/summarize`)
- request mode (JSON or HTMX when detectable)
- video ID after successful parsing
- success or failure outcome
- elapsed time

## Files to touch
- Prefer minimal edits in:
  - `app/main.py`
  - `app/routers/summarize.py`
- Add or update tests only if there is already a nearby low-cost pattern for log verification.

## Out of scope
- Structured logging framework replacement.
- Centralized tracing, metrics, or external monitoring integrations.
- Logging transcript content or full request payloads.
- Refactoring request flow for logging convenience.

## Acceptance criteria
- Summarize requests emit useful start/end or success/failure logs.
- Error cases are observable without changing current error contracts.
- Sensitive request content is not logged.
- The change remains small and reviewable.

## Copilot Agent instructions
- Keep logging localized to current request boundaries.
- Reuse the existing logger setup before introducing new logging patterns.
- Prefer a minimal implementation that improves observability without altering contracts.
- Record the finalized implementation details in `.agents/changes/`.

## Implemented result
- `app/routers/summarize.py`: added `logger`, `time` imports; request start/video_id/completion+elapsed logs for both `api_summarize` and `htmx_summarize`.
- `app/main.py`: added warning/error logs in each exception handler with path and message.
- No route, schema, template, or response contract changes.
- All 26 existing tests pass.
