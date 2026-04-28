# Change 0005 — 오늘의 독서 내용 랜덤 요약 팝업

## Status
- Implemented

## Goal
- 메인 화면에 오늘의 독서 내용 버튼을 추가한다.
- 특정 Notion 독서 DB(도서 목록)에서 `읽기 종료` 날짜가 채워진 페이지(=읽기 완료) 목록을 관리한다.
- 버튼 클릭 시 해당 페이지 중 1건을 랜덤 선택하여 요약하고, 결과를 새 팝업 창에서 보여준다.

## Background
- 현재 앱은 YouTube URL 기반 요약 플로우 중심이며, 독서 기록(노션 DB) 기반 랜덤 회고 기능이 없다.
- 사용자 요구는 "오늘 무엇을 읽었는지"를 가볍게 복기할 수 있는 1클릭 경험이다.
- 기존 아키텍처(라우터 + 서비스 + 템플릿/HTMX 분리)를 유지하면서 기능을 확장한다.

## Scope
- 메인 UI: 버튼 1개 추가, 클릭 시 팝업 오픈.
- Notion 연동: 지정 DB에서 읽기 완료 페이지 조회.
- 랜덤 선택: 후보 목록에서 1개 샘플링.
- 요약: 페이지 본문을 기존 요약기(LLM)로 요약.
- 표시: 팝업에서 제목/요약/메타데이터 렌더링.
- 실패 처리: 후보 없음, Notion API 실패, 요약 실패 시 사용자 친화 메시지 제공.

## Functional Specification

### 1) 메인 화면 버튼
- 위치: 기존 메인 요약 인터랙션 영역(사용자 입력 영역 인접).
- 라벨: 오늘의 독서 내용
- 동작:
  - 클릭 즉시 새 창 또는 팝업 오픈.
  - 팝업 URL에 전용 라우트 사용 (예: `/reading/today`).
  - 팝업 차단 이슈를 줄이기 위해 사용자 클릭 이벤트 내에서 `window.open` 실행.

### 2) Notion 독서 DB 페이지 관리
- 대상 DB: 환경변수로 지정한 Notion DB ID (`NOTION_READING_DB_ID`).
  - 실연동 확인된 DB 제목: `도서 목록`.
- 접근 토큰: 환경변수 (`NOTION_API_KEY`). 토큰/DB ID는 절대 코드/문서에 평문 포함 금지.
- 사전 조건:
  - 해당 DB가 Notion Integration과 명시적으로 연결(공유)되어 있어야 한다.
- 필터 조건:
  - 완료 판별 속성: `읽기 종료` (타입: `date`).
  - 완료 = 해당 날짜 속성이 비어 있지 않은 상태(`is_not_empty: true`).
  - 속성명은 환경변수(`NOTION_READING_DONE_PROPERTY`)로 오버라이드 가능 (기본: `읽기 종료`).
- Notion query 예시:
  ```json
  {
    "filter": {
      "property": "읽기 종료",
      "date": { "is_not_empty": true }
    }
  }
  ```
- 참고 DB 속성(실연동 기준):
  - `도서명`(title), `저자/역자`(rich_text), `출판사`(rich_text)
  - `분류`(multi_select), `독서 유형`(multi_select)
  - `읽기 시작`(date), `읽기 종료`(date), `보류 일자`(date), `등록일`(created_time)
  - `평가 점수`(number), `기대 점수`(number)
  - `메모`(rich_text), `비고`(rich_text)
- 관리 정책:
  - 요청 시점 실시간 조회를 기본으로 한다.
  - 후속 확장으로 캐시(예: 5분) 고려 가능.

### 3) 랜덤 선택 및 요약
- 후보 집합: 필터된 읽기 완료 페이지 리스트.
- 랜덤 선택: 균등 무작위 1건.
- 요약 입력 구성(우선순위):
  1. 속성 컨텍스트: 도서명, 저자/역자, 출판사, 분류, 독서 유형, 평가 점수, 기대 점수, 읽기 시작/종료, 메모, 비고.
  2. 페이지 본문 텍스트: `GET /v1/blocks/{page_id}/children`로 가져온 블록을 텍스트로 평탄화
     (지원 블록 예: `paragraph`, `heading_1~3`, `bulleted_list_item`, `numbered_list_item`, `quote`, `callout`, `to_do`, `bookmark`).
  3. 본문이 비어 있을 경우: 속성 컨텍스트(특히 `메모`, `비고`)만으로 요약 수행.
- 길이 제한:
  - LLM 입력 토큰 한도 고려, 본문 텍스트는 적정 상한(예: 12k chars) 내 절단.
- 요약 출력(최소):
  - 한 줄 요약
  - 핵심 포인트 목록
  - 키워드 목록
- 기존 summarize 품질 옵션(detail level)과의 정합:
  - 1차는 기본값 `normal` 고정.
  - 후속으로 팝업 내 옵션 선택 확장 가능.

### 4) 팝업 화면
- 전용 템플릿 렌더링(서버 렌더링 + 기존 스타일 재사용).
- 표시 항목(실제 DB 속성 매핑):
  - 도서명 → 제목
  - 저자/역자 → 부제
  - 출판사 → 보조 정보
  - 분류, 독서 유형 → 태그(multi_select 옵션 칩)
  - 평가 점수, 기대 점수 → 부가 정보
  - 읽기 시작 ~ 읽기 종료 → 기간 표시
  - 요약 결과(한 줄 / 핵심 포인트 / 키워드)
  - 원문 링크(Notion 페이지 `url`)
- 상태 UI:
  - 로딩 상태
  - 데이터 없음 상태(읽기 완료 페이지 없음)
  - 본문 비어있음(속성 기반 요약으로 대체했음을 표시)
  - 오류 상태(조회 실패/요약 실패)

## API/Route Contract (Proposed)

### Page route
- `GET /reading/today`
- 설명: 팝업 초기 페이지 렌더링.

### Data route
- `GET /api/reading/today-summary`
- 설명: 읽기 완료 페이지 목록 조회 → 랜덤 선택 → 요약 결과 반환.
- 성공 응답 예시:
```json
{
  "success": true,
  "data": {
    "page_id": "...",
    "title": "자기신뢰",
    "notion_url": "https://www.notion.so/...",
    "meta": {
      "author": "...",
      "publisher": "...",
      "categories": ["인문"],
      "reading_types": ["종이책"],
      "rating": 4,
      "expected": 5,
      "start_date": "2025-08-01",
      "end_date": "2025-09-07"
    },
    "summary": {
      "one_line": "...",
      "key_points": ["...", "..."],
      "keywords": ["...", "..."]
    },
    "used_fallback": false
  }
}
```
- 실패 응답 예시:
```json
{
  "success": false,
  "error": {
    "code": "NO_COMPLETED_PAGES",
    "message": "읽기 완료된 독서 페이지가 없습니다."
  }
}
```

## Error Cases
- `NO_COMPLETED_PAGES`: 필터 결과 0건(`읽기 종료`가 비어 있지 않은 페이지 없음).
- `NOTION_AUTH_ERROR`: 토큰 오류/권한 없음.
- `NOTION_NOT_SHARED`: DB가 Integration과 공유되지 않음(404 object_not_found).
- `NOTION_RATE_LIMIT`: Notion API 제한.
- `NOTION_SCHEMA_MISMATCH`: `읽기 종료` 속성 미존재 또는 타입이 `date`가 아님.
- `SUMMARY_FAILED`: LLM 요약 실패.
- `UNEXPECTED_ERROR`: 기타 예외.

## Non-Functional Requirements
- 사용자 체감 응답시간 목표: 5초 이내(네트워크/LLM 상태에 따라 변동 가능).
- 예외 발생 시 기존 메인 페이지 기능에 영향 주지 않음.
- 로그에는 page_id, 처리시간, 실패 코드 중심으로 기록하고 본문 전체는 저장하지 않음.

## Implementation Impact (Planned)
- `app/services/notion.py` (신규 또는 확장):
  - DB 쿼리, 완료 페이지 필터링, 페이지 본문 파싱.
- `app/services/summarizer.py` (기존):
  - 독서 텍스트 입력 경로 재사용/보강.
- `app/routers/reading.py` (신규):
  - 팝업 페이지 라우트 + 데이터 API.
- `app/main.py` (수정):
  - reading 라우터 등록.
- `app/templates/index.html` (수정):
  - 메인 버튼 추가.
- `app/templates/reading_popup.html` (신규):
  - 팝업 결과 템플릿.
- `app/static/js/app.js` (수정):
  - 버튼 클릭 시 팝업 오픈 로직.
- `tests/test_reading.py` (신규):
  - 후보 없음/성공/실패 분기 테스트.

## Environment Variables (Planned)
- `NOTION_API_KEY` : Notion integration secret.
- `NOTION_READING_DB_ID` : 독서 DB ID.
- `NOTION_READING_DONE_PROPERTY` : 완료 판별용 날짜 속성명 (기본: `읽기 종료`, 타입은 반드시 `date`).

## Acceptance Criteria
- 메인 화면에서 오늘의 독서 내용 버튼을 확인할 수 있다.
- 버튼 클릭 시 새 팝업이 열리고, 읽기 완료 페이지 중 랜덤 1건 요약이 표시된다.
- 읽기 완료 페이지가 없으면 명확한 안내 문구를 표시한다.
- Notion/요약 오류 발생 시 사용자에게 오류 상태를 표시하고 앱이 중단되지 않는다.
- 기존 YouTube 요약 플로우 및 history/daily-log 기능 계약은 유지된다.

## Out of Scope
- Notion 페이지 생성/수정 기능.
- 랜덤 선택 이력 기반 중복 회피 알고리즘.
- 개인별 맞춤 추천/난이도 조절.
- 멀티 DB 동시 조회.
