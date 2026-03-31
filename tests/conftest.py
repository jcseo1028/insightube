"""pytest 공통 fixture."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import SummaryResult, VideoMetadata


@pytest.fixture
def client() -> TestClient:
    """FastAPI 테스트 클라이언트 fixture."""
    return TestClient(app)


@pytest.fixture
def mock_transcript() -> str:
    """테스트용 자막 데이터 fixture."""
    return (
        "안녕하세요. 오늘은 파이썬에 대해 알아보겠습니다. "
        "파이썬은 1991년 귀도 반 로섬이 만든 프로그래밍 언어입니다. "
        "간결한 문법과 다양한 라이브러리가 특징입니다. "
        "웹 개발, 데이터 분석, 인공지능 등 다양한 분야에서 사용됩니다. "
        "특히 초보자가 배우기 쉬운 언어로 유명합니다."
    )


@pytest.fixture
def mock_video_metadata() -> VideoMetadata:
    """테스트용 영상 메타데이터 fixture."""
    return VideoMetadata(
        title="파이썬 기초 강좌",
        channel="코딩 채널",
        duration="15:30",
        thumbnail_url="https://img.youtube.com/vi/test123/maxresdefault.jpg",
    )


@pytest.fixture
def mock_summary_result() -> SummaryResult:
    """테스트용 요약 결과 fixture."""
    return SummaryResult(
        one_line="파이썬의 특징과 활용 분야를 소개하는 영상입니다.",
        key_points=[
            "파이썬은 1991년 귀도 반 로섬이 개발한 프로그래밍 언어이다",
            "간결한 문법과 풍부한 라이브러리가 강점이다",
            "웹 개발, 데이터 분석, AI 등 다양한 분야에서 활용된다",
        ],
        keywords=["파이썬", "프로그래밍", "초보자"],
    )
