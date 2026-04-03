"""YouTube 서비스 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exceptions import InvalidURLError, TranscriptNotFoundError
from app.services.youtube import extract_video_id, get_transcript, get_video_metadata


# ===== extract_video_id 테스트 =====


class TestExtractVideoId:
    """extract_video_id 함수 테스트."""

    def test_standard_url(self) -> None:
        """표준 youtube.com/watch?v= URL에서 ID를 추출한다."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_url(self) -> None:
        """youtu.be/ 단축 URL에서 ID를 추출한다."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_embed_url(self) -> None:
        """youtube.com/embed/ URL에서 ID를 추출한다."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_extra_params(self) -> None:
        """추가 파라미터가 포함된 URL에서도 ID를 추출한다."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_without_https(self) -> None:
        """프로토콜 없는 URL에서도 ID를 추출한다."""
        url = "www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_empty_string_raises(self) -> None:
        """빈 문자열은 InvalidURLError를 발생시킨다."""
        with pytest.raises(InvalidURLError):
            extract_video_id("")

    def test_none_raises(self) -> None:
        """None은 InvalidURLError를 발생시킨다."""
        with pytest.raises(InvalidURLError):
            extract_video_id("")

    def test_invalid_domain_raises(self) -> None:
        """YouTube가 아닌 도메인은 InvalidURLError를 발생시킨다."""
        with pytest.raises(InvalidURLError):
            extract_video_id("https://www.example.com/watch?v=dQw4w9WgXcQ")

    def test_malformed_url_raises(self) -> None:
        """잘못된 형식의 URL은 InvalidURLError를 발생시킨다."""
        with pytest.raises(InvalidURLError):
            extract_video_id("this is not a url")


# ===== get_transcript 테스트 =====


class TestGetTranscript:
    """get_transcript 함수 테스트."""

    @pytest.mark.asyncio
    async def test_successful_transcript(self) -> None:
        """정상적으로 자막을 추출한다."""
        mock_snippet_1 = MagicMock()
        mock_snippet_1.text = "안녕하세요"
        mock_snippet_1.start = 0.0
        mock_snippet_2 = MagicMock()
        mock_snippet_2.text = "오늘의 영상입니다"
        mock_snippet_2.start = 5.0
        mock_transcript = [mock_snippet_1, mock_snippet_2]

        with patch("app.services.youtube.YouTubeTranscriptApi") as MockApi:
            mock_instance = MockApi.return_value
            mock_instance.fetch.return_value = mock_transcript

            result = await get_transcript("test_video_id")

            assert "안녕하세요" in result
            assert "오늘의 영상입니다" in result

    @pytest.mark.asyncio
    async def test_no_transcript_raises(self) -> None:
        """자막이 없으면 TranscriptNotFoundError를 발생시킨다."""
        from youtube_transcript_api._errors import NoTranscriptFound

        with patch("app.services.youtube.YouTubeTranscriptApi") as MockApi:
            mock_instance = MockApi.return_value
            mock_instance.fetch.side_effect = NoTranscriptFound(
                "test_video_id", ["ko", "en"], {}
            )
            mock_instance.list.side_effect = Exception("No transcripts")

            with pytest.raises(TranscriptNotFoundError):
                await get_transcript("test_video_id")


# ===== get_video_metadata 테스트 =====


class TestGetVideoMetadata:
    """get_video_metadata 함수 테스트."""

    @pytest.mark.asyncio
    async def test_successful_metadata(self) -> None:
        """정상적으로 메타데이터를 추출한다."""
        mock_info = {
            "title": "테스트 영상",
            "channel": "테스트 채널",
            "duration": 930,  # 15:30
            "thumbnail": "https://img.youtube.com/vi/test/maxresdefault.jpg",
        }

        with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl_instance = MagicMock()
            mock_ydl_instance.extract_info.return_value = mock_info
            mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
            mock_ydl_instance.__exit__ = MagicMock(return_value=False)
            mock_ydl_cls.return_value = mock_ydl_instance

            result = await get_video_metadata("test_video_id")

            assert result is not None
            assert result.title == "테스트 영상"
            assert result.channel == "테스트 채널"
            assert result.duration == "15:30"

    @pytest.mark.asyncio
    async def test_metadata_failure_returns_none(self) -> None:
        """메타데이터 추출 실패 시 None을 반환한다."""
        with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
            mock_ydl_cls.side_effect = Exception("Network error")

            result = await get_video_metadata("test_video_id")

            assert result is None
