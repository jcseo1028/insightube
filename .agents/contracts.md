# Contracts

## Routes

- `GET /`
  - Returns the main HTML page.
- `POST /api/summarize`
  - Request body: `SummarizeRequest`
  - Response: `SummarizeResponse`
- `POST /summarize`
  - Request body: form fields `url`, `detail_level`, `max_key_points`, `max_keywords`, `include_transcript`
  - Response: HTML partial for HTMX
  - Response header: `HX-Trigger: historyUpdated`
- `GET /api/history`
  - Query: `limit` (optional, default 20, max 100)
  - Response: `{ success: true, data: HistoryListItem[] }`
- `GET /api/history/{id}`
  - Response: `{ success: true, data: HistoryDetail }` or 404
- `DELETE /api/history/{id}`
  - Response: `{ success: true }` or 404
- `GET /history/panel`
  - Response: HTML partial (history list for side panel)
- `GET /history/{id}`
  - Response: HTML partial (reuses `summary_result.html`) or 404 HTML fragment

## Request Models

### `SummarizeRequest`

- `url: str`
- `options: SummarizeOptions` (defaulted if omitted)

### `SummarizeOptions`

- `detail_level`: `brief | normal | detailed` (default: `detailed`)
- `max_key_points`: integer, 3 to 15
- `max_keywords`: integer, 3 to 10
- `include_transcript`: boolean

## Form Parsing Behavior

- Invalid or missing `detail_level` falls back to `detailed`.
- Invalid `max_key_points` falls back to `7`; parsed values are clamped to 3..15.
- Invalid `max_keywords` falls back to `5`; parsed values are clamped to 3..10.
- `include_transcript` is true only when the form value is `on`.

## HTMX Error Rendering Contract

- For `HX-Request` summarize flows, domain errors return HTML fragments with status `200` so the result panel is always replaced with a visible message block.
- JSON API (`/api/summarize`) error status codes remain unchanged (`400/404/500`).

## Policy-Blocked Retry Contract

- On repeated policy-blocked attempts for the same `video_id`, summarize router retries once with `detail_level=brief`.
- If fallback succeeds, persisted `detail_level` is `brief`.

## Response Models

### `SummaryResult`

- `one_line: str`
- `key_points: list[str]`
- `keywords: list[str]`

### `SummarizeData`

- `video_id: str`
- `title: str`
- `channel: str`
- `duration: str`
- `thumbnail_url: str`
- `summary: SummaryResult`
- `transcript: str`

## Response Assembly Behavior

- If metadata lookup fails, `title`, `channel`, and `duration` default to empty strings.
- If metadata lookup fails, `thumbnail_url` falls back to `https://img.youtube.com/vi/{video_id}/maxresdefault.jpg`.
- If transcript inclusion is disabled, `transcript` is returned as an empty string.

### `SummarizeResponse`

- `success: bool`
- `data: SummarizeData | None`
- `error: ErrorDetail | None`

### `ErrorDetail`

- `code: str`
- `message: str`

## History Models

### `HistoryListItem`

- `id: int`
- `video_id: str`
- `url: str`
- `title: str`
- `channel: str`
- `duration: str`
- `thumbnail_url: str`
- `one_line: str`
- `detail_level: str` (default when absent: `detailed`)
- `created_at: str`

### `HistoryDetail`

- All fields from `HistoryListItem` plus:
- `key_points: list[str]`
- `keywords: list[str]`
- `transcript: str`

## Daily Log Routes

- `GET /api/daily-log`
  - Query: `date` (optional, default: today KST, format: `YYYY-MM-DD`)
  - Response: `{ success: true, data: DailyLogItem[] }`
- `GET /api/daily-log/recent`
  - Query: `days` (optional, default 7, max 90)
  - Response: `{ success: true, data: DailyLogSummary[] }`

## Daily Log Models

### `DailyLogItem`

- `id: int`
- `video_id: str`
- `title: str`
- `channel: str`
- `one_line: str`
- `detail_level: str`
- `created_at: str`

### `DailyLogSummary`

- `date: str` (YYYY-MM-DD)
- `count: int`
- `items: list[DailyLogItem]`

## Reading (Notion) Routes

- `GET /reading/today`
  - Response: HTML popup page that fetches `/api/reading/today-summary` on load.
- `GET /api/reading/today-summary`
  - Response: `{ success: true, data: ReadingSummaryData }` on success.
  - On error: `{ success: false, error: { code, message } }` with status `404` (NO_COMPLETED_PAGES) or `502` (Notion 관련 오류) or `500` (UNEXPECTED_ERROR).

## Reading Models

### `ReadingPageMeta`

- `author: str`
- `publisher: str`
- `categories: list[str]`
- `reading_types: list[str]`
- `rating: float | None`
- `expected: float | None`
- `start_date: str`
- `end_date: str`

### `ReadingBonkkaejeokSummary`

- `one_line: str` — 책 전체를 관통하는 한 문장 요약.
- `seen: list[str]` — 책에서 본 사실/핵심 인용/표현.
- `realized: list[str]` — 깨달은 점/통찰/생각의 전환.
- `applied: list[str]` — 일상/업무/행동에 적용할 구체적 실천.
- `keywords: list[str]` — 기억 환기용 키워드.

### `ReadingSummaryData`

- `page_id: str`
- `title: str`
- `notion_url: str`
- `meta: ReadingPageMeta`
- `summary: ReadingBonkkaejeokSummary`
- `used_fallback: bool` (true when both 본깨적 sections 및 body blocks were empty)

## Error Codes

- `INVALID_URL`
- `TRANSCRIPT_NOT_FOUND`
- `SUMMARIZATION_ERROR`
- `NOT_FOUND` (history)
- `NO_COMPLETED_PAGES`
- `NOTION_AUTH_ERROR`
- `NOTION_NOT_SHARED`
- `NOTION_RATE_LIMIT`
- `NOTION_SCHEMA_MISMATCH`
- `UNEXPECTED_ERROR`

## Current URL Support

- `youtube.com/watch?v=...`
- `youtu.be/...`
- `youtube.com/embed/...`

## Configuration Contract

- One of these must be set:
  - `GITHUB_TOKEN`
  - `OPENAI_API_KEY`
- Optional settings:
  - `LLM_MODEL`
  - `MAX_TRANSCRIPT_LENGTH`
  - `SUMMARY_LANGUAGE`
- Reading 기능 사용 시 필수:
  - `NOTION_API_KEY` — Notion Integration secret.
  - `NOTION_READING_DB_ID` — 대상 독서 DB ID.
- Reading 기능 선택:
  - `NOTION_READING_DONE_PROPERTY` — 완료 판별용 date 속성명 (기본: `읽기 종료`).
