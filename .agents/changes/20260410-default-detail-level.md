# Change 0005 — 기본 요약 상세도 `상세`로 변경

## Status
- Implemented

## Goal
- 초기 화면에서 사용자가 별도 선택을 하지 않아도 `상세(detailed)` 요약이 실행되도록 기본값을 변경한다.
- UI, 폼 파싱, 스키마 기본값, 문서가 같은 기본 동작을 가리키도록 맞춘다.

## Scope
- 요약 옵션 라디오 버튼의 기본 선택값을 `detailed`로 변경.
- `SummarizeOptions` 기본 상세도를 `DetailLevel.DETAILED`로 변경.
- 폼 데이터에 `detail_level`이 없거나 잘못된 경우 fallback을 `detailed`로 변경.
- 히스토리 관련 기본 문자열/DB 스키마 기본값을 `detailed`로 정렬.
- 관련 테스트와 README 문구를 현재 동작에 맞게 갱신.

## Files touched
- `app/templates/index.html` — 상세도 라디오 기본 선택값을 `상세`로 변경
- `app/models/schemas.py` — `SummarizeOptions`, 히스토리 스키마 기본 상세도 변경
- `app/routers/summarize.py` — 폼 파싱 기본값 및 invalid fallback 변경
- `app/routers/history.py` — 잘못된 히스토리 상세도 fallback 변경
- `app/services/history.py` — 신규 DB 생성 시 `detail_level` 기본값 변경
- `tests/test_summarize_router.py` — 기본/fallback 기대값을 `detailed`로 갱신
- `README.md` — 기본 상세도 설명 업데이트

## Notes
- 기존 SQLite 테이블은 `CREATE TABLE IF NOT EXISTS` 특성상 자동 마이그레이션되지 않는다.
- 다만 현재 저장 경로에서는 요약 옵션의 `detail_level`을 명시적으로 저장하므로, 신규 요약 저장 동작에는 이번 기본값 변경이 그대로 반영된다.

## Acceptance criteria
- 첫 화면에서 `상세`가 기본 선택되어 보인다.
- 폼에 `detail_level`이 없으면 `detailed`로 처리된다.
- 잘못된 `detail_level` 입력은 `detailed`로 fallback 된다.
- README와 구현 기본값이 서로 일치한다.