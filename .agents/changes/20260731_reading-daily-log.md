# Reading Daily File-Log 통합

## Context

- 지금까지 오늘의 독서 내용 요약 결과는 웹 팝업과 콘솔 로거(`logger`)에만 남았고, `logs/daily/*.log` 스트림에는 흔적이 없었음.
- 사용자가 하루 활동을 daily log 파일에서 모니터링하는 흐름과 일치하지 않아, 요청/성공/실패 이벤트가 함께 남도록 요청.

## Decision

- 파일 daily log(`logs/daily/*.log`)에만 이벤트를 추가하고, DB `daily_log` 테이블(YouTube 전용 스키마: `video_id NOT NULL`)은 건드리지 않음.
- 이벤트 태그:
  - `READING_REQ` — 요청 진입.
  - `READING_OK` — 성공 (`page_id`, `title`, `used_fallback`, `elapsed`).
  - `READING_FAIL_EMPTY` / `READING_FAIL_NOTION` / `READING_FAIL_UNEXPECTED` — 실패 사유별.
- 포맷은 기존 `[HH:MM:SS] STATUS | key=value | …` 스타일을 따름.

## Scope of Changes

- `app/services/daily_log.py`
  - `log_reading_request()`, `log_reading_success(page_id, title, used_fallback, elapsed)`, `log_reading_failure(status, page_id?, error_msg, elapsed?)` 신규.
- `app/routers/reading.py`
  - `api_today_reading_summary()` 진입 시 `log_reading_request()`.
  - 성공 시 `log_reading_success()`.
  - `NoCompletedPagesError` / `NotionError` / `Exception` 핸들러에서 `log_reading_failure()` (elapsed 포함).
- `.agents/modules.md`, `.agents/pipeline.md`: reading flow에 daily 파일 로깅 명시.

## Non-Scope

- DB 저장 미포함 (스키마 확장 없이 최소 변경 유지).
- 신규 API/뷰 없음.

## Verification

- 74/74 pytest 통과.
- 팝업 재요청 후 `logs/daily/*.log` 에 `READING_REQ` / `READING_OK` 라인이 순서대로 남는 것을 육안 확인 (사용자 후속).

## Status

Implemented.
