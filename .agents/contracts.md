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

## Request Models
### `SummarizeRequest`
- `url: str`
- `options: SummarizeOptions` (defaulted if omitted)

### `SummarizeOptions`
- `detail_level`: `brief | normal | detailed`
- `max_key_points`: integer, 3 to 15
- `max_keywords`: integer, 3 to 10
- `include_transcript`: boolean

## Form Parsing Behavior
- Invalid or missing `detail_level` falls back to `normal`.
- Invalid `max_key_points` falls back to `7`; parsed values are clamped to 3..15.
- Invalid `max_keywords` falls back to `5`; parsed values are clamped to 3..10.
- `include_transcript` is true only when the form value is `on`.

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

## Error Codes
- `INVALID_URL`
- `TRANSCRIPT_NOT_FOUND`
- `SUMMARIZATION_ERROR`

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
