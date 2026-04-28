"""Notion 독서 DB 연동 서비스.

- 지정된 Notion DB(`도서 목록`)에서 `읽기 종료` 날짜가 채워진 페이지를
  '읽기 완료'로 간주한다.
- 페이지 속성 + 본문 블록을 텍스트로 평탄화하여 LLM 요약 입력으로 사용한다.
"""

from __future__ import annotations

import logging
import random
from typing import Any

import httpx

from app.config import get_settings
from app.models.exceptions import (
    NoCompletedPagesError,
    NotionAuthError,
    NotionError,
    NotionNotSharedError,
    NotionRateLimitError,
    NotionSchemaMismatchError,
)
from app.models.schemas import ReadingPageMeta

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# LLM 입력 시 본문 텍스트 길이 상한 (대략적인 안전 한도)
_MAX_BODY_CHARS = 12000


def _build_headers() -> dict[str, str]:
    """Notion API 호출용 공통 헤더를 구성한다."""
    settings = get_settings()
    if not settings.notion_api_key:
        raise NotionAuthError("NOTION_API_KEY 환경변수가 설정되지 않았습니다.")
    return {
        "Authorization": f"Bearer {settings.notion_api_key}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }


def _raise_for_status(resp: httpx.Response) -> None:
    """Notion 응답 상태 코드를 도메인 예외로 변환한다."""
    if resp.is_success:
        return

    status = resp.status_code
    try:
        payload = resp.json()
    except Exception:
        payload = {"message": resp.text}
    code = (payload.get("code") or "").lower()
    message = payload.get("message") or "Notion API 오류가 발생했습니다."

    if status == 401 or code == "unauthorized":
        raise NotionAuthError(message)
    if status == 404 or code == "object_not_found":
        raise NotionNotSharedError(
            "Notion DB를 찾을 수 없습니다. Integration이 해당 DB와 공유되어 있는지 확인하세요."
        )
    if status == 429 or code == "rate_limited":
        raise NotionRateLimitError(message)
    if status == 400 and "validation" in code:
        # 속성명/타입 불일치 등
        raise NotionSchemaMismatchError(message)
    raise NotionError(f"Notion API 오류 (status={status}): {message}")


# ──────────────────────────────────────────────
# DB 조회
# ──────────────────────────────────────────────


async def fetch_completed_pages() -> list[dict[str, Any]]:
    """읽기 완료된(`읽기 종료` date가 채워진) 페이지 전체 목록을 반환한다.

    Returns:
        Notion API의 page 객체 리스트.

    Raises:
        NotionAuthError, NotionNotSharedError, NotionRateLimitError,
        NotionSchemaMismatchError, NotionError
    """
    settings = get_settings()
    if not settings.notion_reading_db_id:
        raise NotionError("NOTION_READING_DB_ID 환경변수가 설정되지 않았습니다.")

    headers = _build_headers()
    url = f"{NOTION_API_BASE}/databases/{settings.notion_reading_db_id}/query"

    body: dict[str, Any] = {
        "filter": {
            "property": settings.notion_reading_done_property,
            "date": {"is_not_empty": True},
        },
        "page_size": 100,
    }

    results: list[dict[str, Any]] = []
    next_cursor: str | None = None

    async with httpx.AsyncClient(timeout=20.0) as client:
        while True:
            payload = dict(body)
            if next_cursor:
                payload["start_cursor"] = next_cursor
            resp = await client.post(url, headers=headers, json=payload)
            _raise_for_status(resp)
            data = resp.json()
            results.extend(data.get("results", []))
            if data.get("has_more"):
                next_cursor = data.get("next_cursor")
                if not next_cursor:
                    break
            else:
                break

    return results


async def fetch_page_block_text(page_id: str) -> str:
    """페이지 본문 블록을 텍스트로 평탄화하여 반환한다.

    1단계 자식 블록만 처리한다(과도한 재귀 호출 회피).
    """
    headers = _build_headers()
    url = f"{NOTION_API_BASE}/blocks/{page_id}/children?page_size=100"

    lines: list[str] = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        cursor: str | None = None
        while True:
            full_url = url
            if cursor:
                full_url = f"{url}&start_cursor={cursor}"
            resp = await client.get(full_url, headers=headers)
            _raise_for_status(resp)
            data = resp.json()
            for block in data.get("results", []):
                line = _block_to_text(block)
                if line:
                    lines.append(line)
            if data.get("has_more"):
                cursor = data.get("next_cursor")
                if not cursor:
                    break
            else:
                break

    text = "\n".join(lines).strip()
    if len(text) > _MAX_BODY_CHARS:
        text = text[:_MAX_BODY_CHARS]
    return text


# ──────────────────────────────────────────────
# 파서
# ──────────────────────────────────────────────


def _rich_text_plain(rich: list[dict[str, Any]] | None) -> str:
    if not rich:
        return ""
    return "".join(item.get("plain_text", "") for item in rich)


def _block_to_text(block: dict[str, Any]) -> str:
    """Notion 블록 1건을 평문 텍스트로 변환한다."""
    btype = block.get("type", "")
    payload = block.get(btype, {}) or {}

    if btype in (
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "quote",
        "callout",
        "to_do",
        "toggle",
    ):
        text = _rich_text_plain(payload.get("rich_text"))
        if btype == "bulleted_list_item":
            return f"- {text}" if text else ""
        if btype == "numbered_list_item":
            return f"1. {text}" if text else ""
        if btype.startswith("heading_"):
            level = btype.split("_")[1]
            return f"{'#' * int(level)} {text}" if text else ""
        if btype == "to_do":
            checked = payload.get("checked", False)
            mark = "[x]" if checked else "[ ]"
            return f"{mark} {text}" if text else ""
        return text

    if btype == "bookmark":
        url = payload.get("url", "")
        caption = _rich_text_plain(payload.get("caption"))
        return f"[bookmark] {caption or url}".strip()

    return ""


def extract_meta(page: dict[str, Any]) -> ReadingPageMeta:
    """Notion 페이지 객체에서 표시용 메타데이터를 추출한다."""
    props = page.get("properties", {}) or {}

    def _rich(prop_name: str) -> str:
        prop = props.get(prop_name) or {}
        return _rich_text_plain(prop.get("rich_text"))

    def _multi(prop_name: str) -> list[str]:
        prop = props.get(prop_name) or {}
        return [opt.get("name", "") for opt in (prop.get("multi_select") or []) if opt.get("name")]

    def _number(prop_name: str) -> float | None:
        prop = props.get(prop_name) or {}
        return prop.get("number")

    def _date_start(prop_name: str) -> str:
        prop = props.get(prop_name) or {}
        date_val = prop.get("date") or {}
        return date_val.get("start") or ""

    return ReadingPageMeta(
        author=_rich("저자/역자"),
        publisher=_rich("출판사"),
        categories=_multi("분류"),
        reading_types=_multi("독서 유형"),
        rating=_number("평가 점수"),
        expected=_number("기대 점수"),
        start_date=_date_start("읽기 시작"),
        end_date=_date_start("읽기 종료"),
    )


def extract_title(page: dict[str, Any]) -> str:
    """페이지의 도서명(title) 속성을 평문으로 반환한다."""
    props = page.get("properties", {}) or {}
    # title 타입은 속성명이 가변적일 수 있어 type으로 탐색
    for prop in props.values():
        if prop.get("type") == "title":
            return _rich_text_plain(prop.get("title"))
    return ""


def build_summary_input(page: dict[str, Any], body_text: str) -> tuple[str, bool]:
    """LLM 요약 입력 텍스트를 구성한다.

    Returns:
        (input_text, used_fallback)
        used_fallback: 본문이 비어 속성 컨텍스트만으로 구성한 경우 True.
    """
    title = extract_title(page)
    meta = extract_meta(page)
    props = page.get("properties", {}) or {}
    memo = _rich_text_plain((props.get("메모") or {}).get("rich_text"))
    note = _rich_text_plain((props.get("비고") or {}).get("rich_text"))

    parts: list[str] = []
    parts.append(f"# 도서명: {title or '(제목 없음)'}")
    if meta.author:
        parts.append(f"- 저자/역자: {meta.author}")
    if meta.publisher:
        parts.append(f"- 출판사: {meta.publisher}")
    if meta.categories:
        parts.append(f"- 분류: {', '.join(meta.categories)}")
    if meta.reading_types:
        parts.append(f"- 독서 유형: {', '.join(meta.reading_types)}")
    if meta.rating is not None:
        parts.append(f"- 평가 점수: {meta.rating}")
    if meta.expected is not None:
        parts.append(f"- 기대 점수: {meta.expected}")
    if meta.start_date or meta.end_date:
        parts.append(f"- 독서 기간: {meta.start_date} ~ {meta.end_date}")
    if memo:
        parts.append(f"\n## 메모\n{memo}")
    if note:
        parts.append(f"\n## 비고\n{note}")

    used_fallback = False
    if body_text:
        parts.append("\n## 본문\n" + body_text)
    else:
        used_fallback = True

    return "\n".join(parts), used_fallback


# ──────────────────────────────────────────────
# 랜덤 선택
# ──────────────────────────────────────────────


def pick_random_completed(pages: list[dict[str, Any]]) -> dict[str, Any]:
    """완료 페이지 목록에서 무작위 1건을 반환한다.

    Raises:
        NoCompletedPagesError: pages가 비어 있는 경우.
    """
    if not pages:
        raise NoCompletedPagesError()
    return random.choice(pages)
