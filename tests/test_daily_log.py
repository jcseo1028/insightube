"""Daily Log 서비스 및 라우터 테스트."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import daily_log as daily_log_service


# --- 테스트용 DB 격리 ---


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 Daily Log 테스트에서 임시 DB를 사용한다."""
    db_path = tmp_path / "test_history.db"
    monkeypatch.setattr(daily_log_service, "DB_PATH", db_path)
    asyncio.get_event_loop().run_until_complete(daily_log_service.init_db())


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- DB 서비스 단위 테스트 ---


class TestDailyLogService:
    """daily_log_service CRUD 테스트."""

    def _run(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    def _sample_kwargs(self, **overrides) -> dict:
        defaults = {
            "video_id": "abc123",
            "title": "테스트 영상",
            "channel": "테스트 채널",
            "one_line": "테스트 한 줄 요약입니다.",
            "detail_level": "normal",
        }
        defaults.update(overrides)
        return defaults

    def test_save_returns_int_id(self) -> None:
        """save()는 정수 id를 반환한다."""
        row_id = self._run(daily_log_service.save(**self._sample_kwargs()))
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_get_by_date_returns_saved_items(self) -> None:
        """저장한 항목이 get_by_date()로 조회된다."""
        self._run(daily_log_service.save(**self._sample_kwargs()))
        self._run(daily_log_service.save(**self._sample_kwargs(video_id="xyz789")))

        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
        items = self._run(daily_log_service.get_by_date(today))

        assert len(items) == 2
        assert items[0]["video_id"] in ("abc123", "xyz789")

    def test_get_by_date_default_today(self) -> None:
        """date 미지정 시 오늘 날짜로 조회한다."""
        self._run(daily_log_service.save(**self._sample_kwargs()))
        items = self._run(daily_log_service.get_by_date())
        assert len(items) == 1

    def test_get_recent_days(self) -> None:
        """get_recent_days()는 날짜별 그룹핑된 결과를 반환한다."""
        self._run(daily_log_service.save(**self._sample_kwargs()))
        self._run(daily_log_service.save(**self._sample_kwargs(video_id="xyz789")))
        result = self._run(daily_log_service.get_recent_days(7))

        assert len(result) >= 1
        assert result[0]["count"] == 2
        assert len(result[0]["items"]) == 2

    def test_get_by_date_empty(self) -> None:
        """저장된 항목이 없는 날짜는 빈 리스트를 반환한다."""
        items = self._run(daily_log_service.get_by_date("2000-01-01"))
        assert items == []


# --- 파일 로깅 테스트 ---


class TestDailyLogFileLogging:
    """파일 로깅 함수 테스트."""

    @pytest.fixture(autouse=True)
    def _reset_file_logger(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """테스트마다 파일 로거를 초기화한다."""
        monkeypatch.setattr(daily_log_service, "LOG_DIR", tmp_path)
        monkeypatch.setattr(daily_log_service, "_file_logger", None)
        yield
        # 핸들러 정리
        if daily_log_service._file_logger:
            for h in daily_log_service._file_logger.handlers[:]:
                h.close()
                daily_log_service._file_logger.removeHandler(h)
            daily_log_service._file_logger = None

    def test_log_request_creates_file(self, tmp_path: Path) -> None:
        """log_request() 호출 시 로그 파일이 생성된다."""
        daily_log_service.log_request(url="https://youtu.be/abc123")
        log_file = tmp_path / "daily.log"
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "REQUEST" in content
        assert "youtu.be/abc123" in content

    def test_log_request_with_video_id(self, tmp_path: Path) -> None:
        """video_id 지정 시 '추출 완료' 메시지가 기록된다."""
        daily_log_service.log_request(url="https://youtu.be/abc123", video_id="abc123")
        content = (tmp_path / "daily.log").read_text(encoding="utf-8")
        assert "abc123 추출 완료" in content

    def test_log_success(self, tmp_path: Path) -> None:
        """log_success()는 SUCCESS 이벤트를 기록한다."""
        daily_log_service.log_success(
            video_id="abc123",
            title="파이썬 강좌",
            channel="테스트",
            detail_level="normal",
            elapsed=3.82,
        )
        content = (tmp_path / "daily.log").read_text(encoding="utf-8")
        assert "SUCCESS" in content
        assert "abc123" in content
        assert "3.82" in content

    def test_log_failure(self, tmp_path: Path) -> None:
        """log_failure()는 FAIL_* 이벤트를 기록한다."""
        daily_log_service.log_failure(
            "FAIL_TRANSCRIPT", video_id="xyz789", error_msg="자막 없음"
        )
        content = (tmp_path / "daily.log").read_text(encoding="utf-8")
        assert "FAIL_TRANSCRIPT" in content
        assert "xyz789" in content
        assert "자막 없음" in content


# --- 라우터 테스트 ---


class TestDailyLogRouter:
    """Daily Log API 엔드포인트 테스트."""

    def test_get_daily_log_today(self, client: TestClient) -> None:
        """GET /api/daily-log는 오늘 날짜의 로그를 반환한다."""
        self._save_sample()
        resp = client.get("/api/daily-log")
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["data"]) == 1

    def test_get_daily_log_specific_date(self, client: TestClient) -> None:
        """날짜를 지정하면 해당 날짜 로그만 반환한다."""
        resp = client.get("/api/daily-log", params={"date": "2000-01-01"})
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_get_recent_daily_log(self, client: TestClient) -> None:
        """GET /api/daily-log/recent는 최근 N일 요약을 반환한다."""
        self._save_sample()
        resp = client.get("/api/daily-log/recent", params={"days": 7})
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)

    @staticmethod
    def _save_sample() -> None:
        asyncio.get_event_loop().run_until_complete(
            daily_log_service.save(
                video_id="abc123",
                title="테스트",
                channel="채널",
                one_line="요약",
                detail_level="normal",
            )
        )
