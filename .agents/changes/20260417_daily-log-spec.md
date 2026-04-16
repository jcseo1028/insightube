# Daily Log 기능 스펙

> 요약 요청 시 DB에 저장되는 내용을 경량 Daily Log로 기록하고,  
> 성공/실패 전 과정을 날짜별 텍스트 파일로도 남긴다.

## 배경

현재 요약 결과는 `history` 테이블에 전문(transcript, key_points 등)이 저장된다.  
사용자는 **일별 활동 요약**을 간단히 확인하고 싶어 하며,  
기존 history와 별도로 날짜 기준의 경량 로그가 필요하다.

또한 현재 로깅은 `logging.basicConfig(level=DEBUG)` 콘솔 출력과  
uvicorn stdout 리다이렉트(`logs/server.log`)뿐이므로,  
**요약 요청의 성공/실패를 날짜별 텍스트 파일로 기록**하여  
문제 발생 시 빠르게 원인을 추적할 수 있도록 한다.

## 현재 상태

| 항목 | 내용 |
|------|------|
| DB 저장 | `data/history.db` → `history` 테이블 |
| 저장 시점 | `POST /api/summarize`, `POST /summarize` 성공 후 fire-and-forget |
| 저장 내용 | video_id, url, title, channel, duration, thumbnail_url, one_line, key_points(JSON), keywords(JSON), transcript, detail_level, created_at |
| 로깅 | `logging.basicConfig(level=DEBUG)` → 콘솔 출력만. 파일 로깅 없음 |
| 로그 파일 | `logs/server.log` — uvicorn stdout/stderr 리다이렉트 전용 (앱 로깅과 무관) |

## 변경 범위

### 1. DB 스키마 — `daily_log` 테이블 추가

```sql
CREATE TABLE IF NOT EXISTS daily_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date        TEXT    NOT NULL,               -- YYYY-MM-DD (KST 기준)
    video_id    TEXT    NOT NULL,
    title       TEXT    NOT NULL DEFAULT '',
    channel     TEXT    NOT NULL DEFAULT '',
    one_line    TEXT    NOT NULL DEFAULT '',     -- 한줄 요약
    detail_level TEXT   NOT NULL DEFAULT 'normal',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_daily_log_date ON daily_log(date);
```

**설계 의도**
- history 대비 transcript, key_points, keywords, thumbnail_url, duration 제외 → 경량화
- `date` 컬럼으로 일별 조회 최적화 (인덱스)
- history와 1:1 관계가 아닌 독립 로그 (history 삭제와 무관하게 로그 보존)

### 2. 서비스 레이어 — `app/services/daily_log.py` 신규

| 함수 | 설명 |
|------|------|
| `init_db()` | daily_log 테이블/인덱스 생성 (앱 시작 시 호출) |
| `save(video_id, title, channel, one_line, detail_level)` | 로그 1건 삽입. `date`는 KST 기준 당일 자동 산출 |
| `get_by_date(date: str) → list[DailyLogItem]` | 특정 날짜의 로그 목록 반환 |
| `get_recent_days(days: int = 7) → list[DailyLogSummary]` | 최근 N일간 날짜별 요약 건수 + 목록 반환 |

### 3. 스키마 — `app/models/schemas.py` 추가

```python
class DailyLogItem(BaseModel):
    id: int
    video_id: str
    title: str
    channel: str
    one_line: str
    detail_level: str
    created_at: str

class DailyLogSummary(BaseModel):
    date: str               # YYYY-MM-DD
    count: int              # 해당일 요약 건수
    items: list[DailyLogItem]
```

### 4. 라우터 — `app/routers/daily_log.py` 신규

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| GET | `/api/daily-log?date=YYYY-MM-DD` | 특정 날짜 로그 조회 (미지정 시 오늘) | `{ success, data: DailyLogItem[] }` |
| GET | `/api/daily-log/recent?days=7` | 최근 N일 일별 요약 | `{ success, data: DailyLogSummary[] }` |

> HTMX 전용 엔드포인트는 1차에서는 제외하며, 필요 시 후속 작업으로 추가한다.

### 5. 저장 호출 — `app/routers/summarize.py` 수정

기존 `history.save()` 호출 직후에 `daily_log.save()` 를 동일하게 fire-and-forget으로 호출한다.

```python
# 기존
await history.save(...)

# 추가
await daily_log.save(
    video_id=video_id,
    title=metadata.title,
    channel=metadata.channel,
    one_line=result.one_line,
    detail_level=options.detail_level.value,
)
```

### 6. 앱 시작 — `app/main.py` 수정

`startup` 이벤트(또는 `lifespan`)에서 `daily_log.init_db()` 호출을 추가한다.

### 7. 파일 로깅 — `logs/daily/YYYY-MM-DD.log` 텍스트 로그

DB 로그와 별도로, 요약 요청의 **전체 라이프사이클**(성공·실패 모두)을  
날짜별 텍스트 파일에 기록한다.

#### 7-1. 파일 경로 및 포맷

```
logs/daily/2026-04-17.log
```

**로그 포맷** (한 줄 = 한 이벤트):
```
[HH:MM:SS] STATUS | video_id=VIDEO_ID | title=TITLE | detail=DETAIL_LEVEL | elapsed=1.23s | message
```

**이벤트 종류:**

| STATUS | 시점 | 기록 내용 |
|--------|------|-----------|
| `REQUEST` | 요약 요청 수신 | url, 추출된 video_id |
| `SUCCESS` | 요약 완료 | video_id, title, channel, detail_level, 소요시간 |
| `FAIL_URL` | URL 파싱 실패 | 입력 url, 에러 메시지 |
| `FAIL_TRANSCRIPT` | 자막 추출 실패 | video_id, 에러 메시지 |
| `FAIL_SUMMARY` | LLM 요약 실패 | video_id, 에러 메시지, 소요시간 |
| `FAIL_UNKNOWN` | 예상치 못한 오류 | 가능한 모든 컨텍스트, traceback 요약 |

**예시:**
```
[14:32:01] REQUEST  | url=https://youtu.be/abc123
[14:32:01] REQUEST  | video_id=abc123 추출 완료
[14:32:05] SUCCESS  | video_id=abc123 | title=파이썬 강좌 | detail=normal | elapsed=3.82s
[14:35:12] REQUEST  | url=https://youtu.be/xyz789
[14:35:12] FAIL_TRANSCRIPT | video_id=xyz789 | 자막을 찾을 수 없습니다 (lang=ko)
```

#### 7-2. 구현 위치 — `app/services/daily_log.py` 에 파일 로깅 함수 추가

| 함수 | 설명 |
|------|------|
| `_get_file_logger() → logging.Logger` | 날짜별 `RotatingFileHandler` 기반 로거 반환. `logs/daily/` 디렉터리 자동 생성 |
| `log_request(url, video_id=None)` | REQUEST 이벤트 기록 |
| `log_success(video_id, title, channel, detail_level, elapsed)` | SUCCESS 이벤트 기록 |
| `log_failure(status, video_id=None, url=None, error_msg="", elapsed=None)` | FAIL_* 이벤트 기록 |

**설계 의도:**
- Python `logging` 모듈의 `TimedRotatingFileHandler` 활용 → 날짜 전환 자동 처리
- DB 저장과 독립 — DB 쓰기 실패해도 파일 로그는 남음
- 동기 I/O (`logging` 기본 동작) — 로그 쓰기는 경량이므로 async 불필요

#### 7-3. 호출 시점 — `app/routers/summarize.py` 수정

```python
# 요청 수신 직후
daily_log.log_request(url=url)

# video_id 추출 후
daily_log.log_request(url=url, video_id=video_id)

# 요약 성공 시 (기존 history.save() 근처)
daily_log.log_success(
    video_id=video_id, title=metadata.title,
    channel=metadata.channel, detail_level=options.detail_level.value,
    elapsed=elapsed,
)

# 각 예외 핸들러에서
daily_log.log_failure("FAIL_URL", url=url, error_msg=str(e))
daily_log.log_failure("FAIL_TRANSCRIPT", video_id=video_id, error_msg=str(e))
daily_log.log_failure("FAIL_SUMMARY", video_id=video_id, error_msg=str(e), elapsed=elapsed)
```

> `[API]` / `[HTMX]` 양쪽 핸들러 모두에 동일하게 적용한다.

## 영향 범위

| 파일 | 변경 유형 |
|------|-----------|
| `app/services/daily_log.py` | **신규** — DB 초기화/CRUD + 파일 로깅 함수 |
| `app/routers/daily_log.py` | **신규** — API 엔드포인트 |
| `app/models/schemas.py` | **수정** — DailyLogItem, DailyLogSummary 추가 |
| `app/routers/summarize.py` | **수정** — daily_log.save() + 파일 로깅 호출 추가 |
| `app/main.py` | **수정** — daily_log 라우터 등록, init_db() 호출 |
| `logs/daily/` | **신규** — 날짜별 `.log` 파일 자동 생성 |
| `tests/test_daily_log.py` | **신규** — 서비스/라우터/파일 로깅 테스트 |
| `.gitignore` | **수정** — `logs/daily/*.log` 패턴 추가 (필요 시) |

## 기존 계약 영향

- **기존 API/라우트 변경 없음** — history 엔드포인트, summarize 응답 스키마 불변
- **history 테이블 변경 없음** — 독립 테이블로 추가
- **summarize 응답 지연 영향 없음** — DB는 fire-and-forget, 파일 로깅은 동기지만 경량
- **기존 콘솔 로깅 유지** — `logging.basicConfig` 설정 변경 없음, 별도 로거 사용

## 미포함 (후속 검토)

- Daily Log UI (HTMX 패널 / 별도 페이지)
- 일별 통계 집계 (총 요약 시간, 채널별 빈도 등)
- 로그 보존 기간 정책 (자동 삭제 / 아카이브)
- daily_log ↔ history 간 연결(history_id FK) 여부
- 파일 로그 자동 정리 (N일 이후 삭제 / 압축)
- 에러 알림 연동 (연속 실패 시 알림 등)
