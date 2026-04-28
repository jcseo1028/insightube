"""오늘의 독서 기능(reading) 단위/라우터 테스트."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.exceptions import (
    NoCompletedPagesError,
    NotionAuthError,
    NotionNotSharedError,
)
from app.models.schemas import SummaryResult
from app.services import notion as notion_service


# ──────────────────────────────────────────────
# 단위 테스트 — 파서/입력 빌더
# ──────────────────────────────────────────────


def _sample_page() -> dict[str, Any]:
    return {
        "id": "page-id-1",
        "url": "https://www.notion.so/page-id-1",
        "properties": {
            "도서명": {
                "type": "title",
                "title": [{"plain_text": "테스트 도서", "type": "text"}],
            },
            "저자/역자": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "홍길동", "type": "text"}],
            },
            "출판사": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "테스트출판", "type": "text"}],
            },
            "분류": {
                "type": "multi_select",
                "multi_select": [{"name": "IT"}, {"name": "자기 계발"}],
            },
            "독서 유형": {
                "type": "multi_select",
                "multi_select": [{"name": "종이책"}],
            },
            "평가 점수": {"type": "number", "number": 4.5},
            "기대 점수": {"type": "number", "number": 5},
            "읽기 시작": {"type": "date", "date": {"start": "2025-09-01"}},
            "읽기 종료": {"type": "date", "date": {"start": "2025-09-30"}},
            "메모": {
                "type": "rich_text",
                "rich_text": [{"plain_text": "이 책은 흥미로웠다", "type": "text"}],
            },
            "비고": {"type": "rich_text", "rich_text": []},
        },
    }


class TestNotionParsers:
    def test_extract_title(self) -> None:
        assert notion_service.extract_title(_sample_page()) == "테스트 도서"

    def test_extract_meta(self) -> None:
        meta = notion_service.extract_meta(_sample_page())
        assert meta.author == "홍길동"
        assert meta.publisher == "테스트출판"
        assert meta.categories == ["IT", "자기 계발"]
        assert meta.reading_types == ["종이책"]
        assert meta.rating == 4.5
        assert meta.expected == 5
        assert meta.start_date == "2025-09-01"
        assert meta.end_date == "2025-09-30"

    def test_build_summary_input_includes_attributes(self) -> None:
        text, fallback = notion_service.build_summary_input(
            _sample_page(), body_text="본문 내용입니다."
        )
        assert "테스트 도서" in text
        assert "홍길동" in text
        assert "이 책은 흥미로웠다" in text
        assert "본문 내용입니다." in text
        assert fallback is False

    def test_build_summary_input_uses_fallback_when_body_empty(self) -> None:
        text, fallback = notion_service.build_summary_input(_sample_page(), body_text="")
        assert fallback is True
        assert "테스트 도서" in text
        assert "이 책은 흥미로웠다" in text  # 메모가 컨텍스트에 포함됨

    def test_pick_random_completed_raises_when_empty(self) -> None:
        with pytest.raises(NoCompletedPagesError):
            notion_service.pick_random_completed([])

    def test_pick_random_completed_returns_one(self) -> None:
        pages = [_sample_page()]
        picked = notion_service.pick_random_completed(pages)
        assert picked["id"] == "page-id-1"


# ──────────────────────────────────────────────
# 라우터 테스트 — 의존성 모킹
# ──────────────────────────────────────────────


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _mock_summary() -> SummaryResult:
    return SummaryResult(
        one_line="테스트 한 줄 요약",
        key_points=["포인트1", "포인트2"],
        keywords=["키워드1"],
    )


class TestReadingRouter:
    def test_today_summary_success(self, client: TestClient) -> None:
        with patch(
            "app.routers.reading.notion_service.fetch_completed_pages",
            new=AsyncMock(return_value=[_sample_page()]),
        ), patch(
            "app.routers.reading.notion_service.fetch_page_block_text",
            new=AsyncMock(return_value="본문 텍스트"),
        ), patch(
            "app.routers.reading.summarize_transcript",
            new=AsyncMock(return_value=_mock_summary()),
        ):
            resp = client.get("/api/reading/today-summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        data = body["data"]
        assert data["page_id"] == "page-id-1"
        assert data["title"] == "테스트 도서"
        assert data["notion_url"].endswith("page-id-1")
        assert data["summary"]["one_line"] == "테스트 한 줄 요약"
        assert data["meta"]["author"] == "홍길동"
        assert data["used_fallback"] is False

    def test_today_summary_no_pages(self, client: TestClient) -> None:
        with patch(
            "app.routers.reading.notion_service.fetch_completed_pages",
            new=AsyncMock(return_value=[]),
        ):
            resp = client.get("/api/reading/today-summary")

        assert resp.status_code == 404
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "NO_COMPLETED_PAGES"

    def test_today_summary_not_shared(self, client: TestClient) -> None:
        with patch(
            "app.routers.reading.notion_service.fetch_completed_pages",
            new=AsyncMock(side_effect=NotionNotSharedError()),
        ):
            resp = client.get("/api/reading/today-summary")

        assert resp.status_code == 502
        body = resp.json()
        assert body["error"]["code"] == "NOTION_NOT_SHARED"

    def test_today_summary_auth_error(self, client: TestClient) -> None:
        with patch(
            "app.routers.reading.notion_service.fetch_completed_pages",
            new=AsyncMock(side_effect=NotionAuthError()),
        ):
            resp = client.get("/api/reading/today-summary")

        assert resp.status_code == 502
        assert resp.json()["error"]["code"] == "NOTION_AUTH_ERROR"

    def test_today_page_renders(self, client: TestClient) -> None:
        resp = client.get("/reading/today")
        assert resp.status_code == 200
        assert "오늘의 독서" in resp.text
        assert "/api/reading/today-summary" in resp.text
