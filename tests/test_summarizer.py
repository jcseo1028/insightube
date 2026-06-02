"""요약 서비스 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exceptions import SummarizationError
from app.models.schemas import SummaryResult
from app.services.summarizer import summarize_transcript


class TestSummarizeTranscript:
    """summarize_transcript 함수 테스트."""

    @pytest.mark.asyncio
    async def test_short_text_summarization(self, mock_transcript: str) -> None:
        """짧은 텍스트를 Stuff 방식으로 요약한다."""
        expected = SummaryResult(
            one_line="파이썬의 특징과 활용 분야를 소개하는 영상입니다.",
            key_points=[
                "파이썬은 1991년 귀도 반 로섬이 개발",
                "간결한 문법과 풍부한 라이브러리",
                "웹, 데이터 분석, AI 등 다양한 분야 활용",
            ],
            keywords=["파이썬", "프로그래밍", "초보자"],
        )

        with patch("app.services.summarizer._create_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm

            with patch("app.services.summarizer._summarize_short", new_callable=AsyncMock) as mock_short:
                mock_short.return_value = expected

                result = await summarize_transcript(mock_transcript)

                assert result.one_line == expected.one_line
                assert len(result.key_points) == 3
                assert len(result.keywords) == 3

    @pytest.mark.asyncio
    async def test_summarization_error_handling(self) -> None:
        """요약 오류 시 SummarizationError를 발생시킨다."""
        with patch("app.services.summarizer._create_llm") as mock_llm_factory:
            mock_llm_factory.side_effect = Exception("LLM connection failed")

            with pytest.raises(SummarizationError):
                await summarize_transcript("테스트 텍스트")

    @pytest.mark.asyncio
    async def test_output_structure(self, mock_summary_result: SummaryResult) -> None:
        """요약 결과가 올바른 구조를 갖는지 검증한다."""
        assert hasattr(mock_summary_result, "one_line")
        assert hasattr(mock_summary_result, "key_points")
        assert hasattr(mock_summary_result, "keywords")
        assert isinstance(mock_summary_result.key_points, list)
        assert isinstance(mock_summary_result.keywords, list)
        assert 1 <= len(mock_summary_result.key_points) <= 7
        assert 1 <= len(mock_summary_result.keywords) <= 5

    @pytest.mark.asyncio
    async def test_content_filter_retry_with_sanitized_transcript(self) -> None:
        """콘텐츠 필터 오류 시 민감 표현 마스킹 후 1회 재시도한다."""
        expected = SummaryResult(
            one_line="민감한 주제를 다루는 영상의 핵심을 요약했습니다.",
            key_points=["핵심 주제", "주요 맥락"],
            keywords=["핵심", "맥락"],
        )

        with patch("app.services.summarizer._create_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm

            with patch("app.services.summarizer._summarize_short", new_callable=AsyncMock) as mock_short:
                mock_short.side_effect = [
                    Exception("Error code: 400 content_filter"),
                    expected,
                ]

                result = await summarize_transcript("자해 충동이 들 때 대처법")

                assert result == expected
                assert mock_short.await_count == 2
                retried_transcript = mock_short.await_args_list[1].args[1]
                assert "[민감 내용]" in retried_transcript

    @pytest.mark.asyncio
    async def test_content_filter_without_maskable_term_raises_summarization_error(self) -> None:
        """마스킹할 표현이 없으면 정책 차단 메시지로 종료한다."""
        with patch("app.services.summarizer._create_llm") as mock_llm_factory:
            mock_llm = MagicMock()
            mock_llm_factory.return_value = mock_llm

            with patch("app.services.summarizer._summarize_short", new_callable=AsyncMock) as mock_short:
                mock_short.side_effect = Exception("Error code: 400 content_filter")

                with pytest.raises(SummarizationError) as exc_info:
                    await summarize_transcript("안녕하세요 반갑습니다")

                assert "콘텐츠 정책 필터" in str(exc_info.value)
                assert mock_short.await_count == 1


class TestSummarizeAPI:
    """요약 API 엔드포인트 테스트."""

    def test_invalid_url_returns_400(self, client) -> None:
        """잘못된 URL로 요청하면 400을 반환한다."""
        response = client.post(
            "/api/summarize",
            json={"url": "https://www.example.com/not-youtube"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_URL"

    def test_empty_url_returns_400(self, client) -> None:
        """빈 URL로 요청하면 400을 반환한다."""
        response = client.post(
            "/api/summarize",
            json={"url": ""},
        )
        assert response.status_code == 400

    def test_main_page_returns_200(self, client) -> None:
        """메인 페이지가 정상 응답한다."""
        response = client.get("/")
        assert response.status_code == 200
        assert "InSighTube" in response.text
