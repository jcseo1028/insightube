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

## Definition of Done

코드 변경이 발생한 모든 작업은 종료 전에 반드시 아래를 수행한다:

1. `.agents/` 문서(system, modules, pipeline, contracts, rules) 중 영향 범위를 갱신한다.
2. README.md에 사용자 관점 영향(설치, 실행, 설정, 기능)이 있으면 반영한다.
3. 의존성 파일(있는 경우)을 갱신한다.
4. 최종 보고 시 문서 반영 여부를 함께 보고한다.
