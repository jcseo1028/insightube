"""히스토리 서비스 및 라우터 테스트."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import history as history_service


# --- 테스트용 DB 격리 ---


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 히스토리 테스트에서 임시 DB 파일을 사용한다."""
    db_path = tmp_path / "test_history.db"
    monkeypatch.setattr(history_service, "DB_PATH", db_path)
    asyncio.get_event_loop().run_until_complete(history_service.init_db())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- DB 서비스 단위 테스트 ---


class TestHistoryService:
    """history_service CRUD 테스트."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _sample_kwargs(self, **overrides) -> dict:
        defaults = {
            "video_id": "abc123",
            "url": "https://www.youtube.com/watch?v=abc123",
            "title": "테스트 영상",
            "channel": "테스트 채널",
            "duration": "10:00",
            "thumbnail_url": "https://img.youtube.com/vi/abc123/maxresdefault.jpg",
            "one_line": "테스트 한 줄 요약입니다.",
            "key_points": ["포인트1", "포인트2"],
            "keywords": ["키워드1", "키워드2"],
            "transcript": "테스트 자막 텍스트",
            "detail_level": "normal",
        }
        defaults.update(overrides)
        return defaults

    def test_save_returns_int_id(self) -> None:
        """save()는 정수 id를 반환한다."""
        row_id = self._run(history_service.save(**self._sample_kwargs()))
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_get_by_id_returns_saved_data(self) -> None:
        """get_by_id()로 저장된 데이터를 정확히 조회한다."""
        row_id = self._run(history_service.save(**self._sample_kwargs()))
        item = self._run(history_service.get_by_id(row_id))

        assert item is not None
        assert item["video_id"] == "abc123"
        assert item["title"] == "테스트 영상"
        assert item["one_line"] == "테스트 한 줄 요약입니다."
        assert item["key_points"] == ["포인트1", "포인트2"]
        assert item["keywords"] == ["키워드1", "키워드2"]
        assert item["detail_level"] == "normal"

    def test_get_by_id_returns_none_for_missing(self) -> None:
        """존재하지 않는 id는 None을 반환한다."""
        item = self._run(history_service.get_by_id(9999))
        assert item is None

    def test_list_recent_returns_newest_first(self) -> None:
        """list_recent()는 최신 순으로 반환한다."""
        self._run(history_service.save(**self._sample_kwargs(title="첫번째")))
        self._run(history_service.save(**self._sample_kwargs(title="두번째")))
        self._run(history_service.save(**self._sample_kwargs(title="세번째")))

        items = self._run(history_service.list_recent(limit=10))
        assert len(items) == 3
        assert items[0]["title"] == "세번째"
        assert items[2]["title"] == "첫번째"

    def test_list_recent_respects_limit(self) -> None:
        """limit 파라미터가 결과 수를 제한한다."""
        for i in range(5):
            self._run(history_service.save(**self._sample_kwargs(title=f"영상{i}")))

        items = self._run(history_service.list_recent(limit=2))
        assert len(items) == 2

    def test_list_recent_excludes_transcript(self) -> None:
        """list_recent 결과에는 transcript 컬럼이 포함되지 않는다."""
        self._run(history_service.save(**self._sample_kwargs()))
        items = self._run(history_service.list_recent(limit=1))
        assert "transcript" not in items[0]

    def test_delete_by_id_removes_record(self) -> None:
        """delete_by_id()로 레코드가 삭제된다."""
        row_id = self._run(history_service.save(**self._sample_kwargs()))
        deleted = self._run(history_service.delete_by_id(row_id))
        assert deleted is True
        assert self._run(history_service.get_by_id(row_id)) is None

    def test_delete_by_id_returns_false_for_missing(self) -> None:
        """존재하지 않는 id 삭제 시 False를 반환한다."""
        deleted = self._run(history_service.delete_by_id(9999))
        assert deleted is False


# --- 라우터 테스트 ---


class TestHistoryRouter:
    """히스토리 HTMX/API 라우터 테스트."""

    def _seed(self, **overrides) -> int:
        defaults = {
            "video_id": "xyz789",
            "url": "https://www.youtube.com/watch?v=xyz789",
            "title": "라우터 테스트 영상",
            "channel": "채널",
            "duration": "5:00",
            "thumbnail_url": "https://img.youtube.com/vi/xyz789/maxresdefault.jpg",
            "one_line": "라우터 테스트 요약",
            "key_points": ["포인트A"],
            "keywords": ["키워드A"],
            "transcript": "라우터 테스트 자막",
            "detail_level": "brief",
        }
        defaults.update(overrides)
        return asyncio.get_event_loop().run_until_complete(
            history_service.save(**defaults),
        )

    def test_api_list_history_returns_200(self, client: TestClient) -> None:
        """GET /api/history는 200과 목록을 반환한다."""
        self._seed()
        resp = client.get("/api/history")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) >= 1

    def test_api_get_history_returns_detail(self, client: TestClient) -> None:
        """GET /api/history/{id}는 상세 데이터를 반환한다."""
        row_id = self._seed()
        resp = client.get(f"/api/history/{row_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["video_id"] == "xyz789"

    def test_api_get_history_404(self, client: TestClient) -> None:
        """존재하지 않는 id는 404를 반환한다."""
        resp = client.get("/api/history/99999")
        assert resp.status_code == 404

    def test_api_delete_history(self, client: TestClient) -> None:
        """DELETE /api/history/{id}는 삭제 후 200을 반환한다."""
        row_id = self._seed()
        resp = client.delete(f"/api/history/{row_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        # 삭제 확인
        assert client.get(f"/api/history/{row_id}").status_code == 404

    def test_htmx_history_panel_returns_html(self, client: TestClient) -> None:
        """GET /history/panel은 HTML 파셜을 반환한다."""
        self._seed()
        resp = client.get("/history/panel")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "라우터 테스트 영상" in resp.text

    def test_htmx_history_detail_returns_summary_html(self, client: TestClient) -> None:
        """GET /history/{id}는 summary_result.html 파셜을 반환한다."""
        row_id = self._seed()
        resp = client.get(f"/history/{row_id}")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "라우터 테스트 요약" in resp.text

    def test_htmx_history_detail_404(self, client: TestClient) -> None:
        """존재하지 않는 히스토리의 HTMX 상세는 404이다."""
        resp = client.get("/history/99999")
        assert resp.status_code == 404
