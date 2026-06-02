# 2026-06-02 Content Filter Fallback

## Why
- 일부 YouTube 자막이 Azure OpenAI 콘텐츠 정책(`content_filter`, `ResponsibleAIPolicyViolation`)에 걸려 요약이 반복 실패함.

## What Changed
- `app/services/summarizer.py`
  - 콘텐츠 필터 오류 감지 헬퍼 추가 (`_is_content_filter_error`).
  - 정책 민감 표현(자해/자살 관련) 최소 마스킹 헬퍼 추가 (`_sanitize_transcript_for_policy`).
  - 필터 감지 시 마스킹 후 1회 자동 재시도 로직 추가.
  - 재시도도 실패하거나 마스킹 불가 시 사용자 친화적 `SummarizationError` 메시지로 종료.
- `tests/test_summarizer.py`
  - 콘텐츠 필터 재시도 성공 케이스 테스트 추가.
  - 마스킹 불가 시 정책 차단 에러 반환 테스트 추가.

## Notes
- API 스키마/라우트 계약 변경 없음.
- 요약 품질을 유지하기 위해 전체 삭제 대신 최소 치환 방식 사용.

## Follow-up (UI + Repeated Block Fallback)
- `app/main.py`
  - HTMX 요청(`HX-Request`) 에러를 상태코드 200의 HTML 블록으로 반환해 화면 결과 영역에서 즉시 보이도록 개선.
  - 정책 차단 메시지는 전용 타이틀/안내 문구로 분기.
- `app/routers/summarize.py`
  - 동일 `video_id`의 정책 차단 실패 횟수를 메모리에서 추적.
  - 2회째 정책 차단부터 `detail_level=brief`로 1회 폴백 재시도.
- `app/templates/partials/summary_result.html`
  - brief 폴백 적용 시 사용자에게 자동 전환 안내 배너 표시.
- Tests
  - `tests/test_summarize_router.py`: 정책 반복 차단 brief 폴백 케이스 추가.
  - `tests/test_summarizer.py`: HTMX 에러 HTML 렌더링(200) 케이스 추가.
