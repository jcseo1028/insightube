# Reading Bonkkaejeok 3-Card Summary

## Status
- Implemented

## Context
- 기존 "오늘의 독서 내용" 기능은 YouTube와 동일한 `summarize_transcript`/`SummaryResult` (한 줄 + key_points + keywords) 구조를 그대로 사용했다.
- 실제 Notion 독서 DB의 모든 페이지가 `heading_2` "**본 것 / 깨달은 것 / 적용할 것**" (본깨적) 구조를 일관되게 사용하고 있어, 이 사용자 작성 노트를 기억 환기에 더 효과적으로 활용할 필요가 있었다.

## Decision
- 독서 요약 결과를 본깨적 3섹션 구조로 분리하고, 팝업 UI도 3-카드 형태로 변경한다.

## Changes
- `app/services/notion.py`
  - `fetch_page_blocks(page_id)` 추가 — 1단계 자식 블록 원본 리스트 반환.
  - `blocks_to_text(blocks)` 추가 — 블록 리스트를 평문으로 평탄화 (`_MAX_BODY_CHARS=12000`).
  - `extract_bonkkaejeok_sections(blocks)` 추가 — `heading_2` 기준으로 본/깨/적 3섹션을 dict로 분리. 공백 무시("본것" 등).
  - `extract_seen_section_text(blocks)` 추가 — (하위 호환) "본 것" 단독 추출.
  - `fetch_page_block_text(page_id)` — `fetch_page_blocks` + `blocks_to_text` 조합으로 단순화.
  - `build_summary_input(page, body_text, seen_text="", sections=None)` — 본깨적 섹션이 있으면 ⭐ 강조 헤더로 우선 포함하고 전체 본문은 보조 자료로 첨부. 본깨적/본문 모두 비면 `used_fallback=True`.
- `app/services/summarizer.py`
  - `summarize_reading(notes, *, max_items=5, max_keywords=5)` 추가 — 독서 전용 분류 프롬프트 + `PydanticOutputParser`로 `ReadingBonkkaejeokSummary` 반환.
- `app/models/schemas.py`
  - `ReadingBonkkaejeokSummary` 신규 (`one_line / seen / realized / applied / keywords`).
  - `ReadingSummaryData.summary` 타입을 `SummaryResult` → `ReadingBonkkaejeokSummary`로 교체.
- `app/routers/reading.py`
  - `summarize_transcript` 호출을 `summarize_reading`로 교체. 본깨적 섹션을 추출해 입력에 포함.
- `app/templates/reading_popup.html`
  - 본깨적 3-카드(👁 본 것 / 💡 깨달은 것 / 🎯 적용할 것) 그리드 + 한 줄 요약 강조 박스 + 키워드 카드.
  - 폭 `max-w-5xl` 확장.
- `app/static/js/app.js`
  - 팝업 창 크기 `1080×900`로 확장.
- 테스트
  - `tests/test_reading.py`: `extract_bonkkaejeok_sections`, `build_summary_input(sections=...)` 검증, `_mock_summary()`를 `ReadingBonkkaejeokSummary`로 교체, 라우터 mock 패치를 `summarize_reading`로 변경.

## Validation
- 전체 테스트: 69 passed.
- 서버 재시작 후 `/api/reading/today-summary`가 `ReadingBonkkaejeokSummary` JSON을 반환함을 확인.

## Notes
- 독서 노트 작성 가이드는 README의 "독서 DB 페이지 구조 (권장)" 섹션 참조.
- 본깨적 섹션이 비어 있을 경우 LLM이 페이지 본문에서 추정해 채우며, 본문도 비면 속성(메모/비고 등)만으로 요약하고 fallback 배너를 표시한다.
