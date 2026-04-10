# Change 0004 — History 기능 추가

## Status
- Implemented

## Goal
- 요약할 때마다 YouTube URL과 요약 결과를 DB에 저장한다.
- 검색 페이지 사이드 패널에 최근 요약 히스토리를 보여준다.
- 히스토리 항목 클릭 시 해당 요약 내용을 다시 표시한다.

## Scope
- SQLite + aiosqlite 기반 로컬 DB 추가.
- History CRUD 서비스 및 라우터 신규 생성.
- 기존 summarize 라우터에 저장 사이드 이펙트 삽입.
- 2-컬럼 레이아웃 전환 및 히스토리 사이드 패널 추가.
- HTMX 이벤트(`historyUpdated`)로 패널 자동 갱신.

## Files touched
- `requirements.txt` — `aiosqlite>=0.20.0` 추가
- `app/services/history.py` — **신규** DB 서비스 (init, save, list, get, delete)
- `app/models/schemas.py` — `HistoryListItem`, `HistoryDetail` 스키마 추가
- `app/routers/history.py` — **신규** (JSON API + HTMX partials)
- `app/routers/summarize.py` — 요약 후 `history_service.save()` 호출 + `HX-Trigger` 헤더
- `app/main.py` — history 라우터 등록, `on_event("startup")` → `lifespan` 전환, DB init
- `app/templates/base.html` — 2-컬럼 레이아웃 (main + sidebar)
- `app/templates/index.html` — `{% block sidebar %}` 히스토리 패널 통합
- `app/templates/partials/history_panel.html` — **신규** 사이드 패널 목록 파셜
- `tests/test_history.py` — **신규** DB CRUD 8 + 라우터 7 = 15 테스트

## DB schema
```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL, url TEXT NOT NULL,
    title TEXT DEFAULT '', channel TEXT DEFAULT '', duration TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '', one_line TEXT NOT NULL,
    key_points TEXT NOT NULL, keywords TEXT NOT NULL,
    transcript TEXT DEFAULT '', detail_level TEXT DEFAULT 'normal',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
```

## Data flow
```
POST /summarize → 요약 파이프라인 → history.save() → HX-Trigger: historyUpdated
사이드 패널 hx-trigger="load, historyUpdated from:body" → GET /history/panel
클릭 → GET /history/{id} → #summary-result에 hx-swap
```

## Acceptance criteria
- 요약 완료 시 DB에 자동 저장된다.
- 사이드 패널에 최근 요약 목록이 표시된다.
- 히스토리 항목 클릭 시 요약 결과가 메인 영역에 표시된다.
- 기존 요약 API 응답 스키마/동작에 변경 없다.
- 히스토리 저장 실패 시 요약 응답에 영향 없다.
- 41개 테스트 전체 통과.
