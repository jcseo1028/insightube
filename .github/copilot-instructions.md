# Copilot Instructions

Repository-wide rules for this codebase:

- Make minimal, localized changes. Edit the smallest viable surface in the existing module first.
- Do not refactor unrelated code, rename unrelated symbols, or reorganize files unless the task explicitly requires it.
- Do not scan the entire repository unless necessary. Start from the active file and the directly related files in `app/` or `tests/`.
- Follow the current architecture: FastAPI app assembly in `app/main.py`, HTTP handlers in `app/routers/`, domain schemas/exceptions in `app/models/`, integrations in `app/services/`, server-rendered UI in `app/templates/`, static assets in `app/static/`.
- Preserve existing contracts unless explicitly changed: current routes, request/response schemas, exception shapes, template expectations, and environment-variable behavior.
- Match existing naming, async usage, error-handling style, and Korean user-facing copy already present in the repository.
- Prefer incremental, testable modifications. When behavior changes, update or add the nearest relevant tests under `tests/` instead of broad rewrites.
- When uncertain, align with the existing implementation and patterns in neighboring code rather than introducing new abstractions, frameworks, or cross-cutting conventions.
- Keep JSON API behavior and HTMX/template behavior consistent with the current split implementation; do not collapse them into a new pattern unless explicitly requested.
- Persist finalized implementation decisions and notable change rationale into `.agents/changes/` as small, task-scoped records. Name files as `YYYYMMDD_title.md` (creation date + kebab-case title).
