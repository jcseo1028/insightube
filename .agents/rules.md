# Rules

## Operational Rules
- Change the smallest viable surface first. Keep edits local to the active module unless expansion is required.
- Do not refactor unrelated code, rename unrelated symbols, or reorganize files without an explicit task need.
- Preserve existing contracts by default: routes, schema shapes, exception behavior, template expectations, and environment-variable behavior.
- Follow established structure and naming before introducing anything new.
- Reuse existing patterns from neighboring code before adding new abstractions, helpers, or layers.
- Keep JSON API behavior and HTMX/template behavior consistent with the current split implementation.
- Prefer small, reviewable, testable modifications over broad rewrites.
- When behavior changes, update the nearest relevant tests under `tests/`.
- Record finalized implementation decisions and notable rationale in `.agents/changes/`.

## Current Repository Constraints
- No persistence layer should be assumed.
- No authentication or user model should be assumed.
- No background job system should be assumed.
- Do not introduce new architectural layers unless the task explicitly requires them.
