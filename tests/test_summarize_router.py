"""요약 라우터 옵션 파싱 테스트."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.models.exceptions import SummarizationError
from app.models.schemas import DetailLevel
from app.models.schemas import SummarizeOptions, SummaryResult
from app.routers.summarize import (
    _parse_options_from_form,
    _policy_block_counts,
    _summarize_with_policy_fallback,
)


class TestParseOptionsFromForm:
    """_parse_options_from_form 함수 테스트."""

    def test_defaults_when_values_are_missing(self) -> None:
        """값이 없으면 현재 기본값을 사용한다."""
        result = _parse_options_from_form({})

        assert result.detail_level == DetailLevel.DETAILED
        assert result.max_key_points == 7
        assert result.max_keywords == 5
        assert result.include_transcript is False

    def test_invalid_detail_level_falls_back_to_detailed(self) -> None:
        """잘못된 상세도 값은 detailed로 처리한다."""
        result = _parse_options_from_form({"detail_level": "unknown"})

        assert result.detail_level == DetailLevel.DETAILED

    def test_max_key_points_is_clamped_to_valid_range(self) -> None:
        """주요 포인트 수는 3..15 범위로 제한한다."""
        low_result = _parse_options_from_form({"max_key_points": "1"})
        high_result = _parse_options_from_form({"max_key_points": "99"})

        assert low_result.max_key_points == 3
        assert high_result.max_key_points == 15

    def test_invalid_max_key_points_falls_back_to_default(self) -> None:
        """잘못된 주요 포인트 수는 기본값 7로 처리한다."""
        result = _parse_options_from_form({"max_key_points": "invalid"})

        assert result.max_key_points == 7

    def test_max_keywords_is_clamped_to_valid_range(self) -> None:
        """키워드 수는 3..10 범위로 제한한다."""
        low_result = _parse_options_from_form({"max_keywords": "1"})
        high_result = _parse_options_from_form({"max_keywords": "99"})

        assert low_result.max_keywords == 3
        assert high_result.max_keywords == 10

    def test_invalid_max_keywords_falls_back_to_default(self) -> None:
        """잘못된 키워드 수는 기본값 5로 처리한다."""
        result = _parse_options_from_form({"max_keywords": None})

        assert result.max_keywords == 5

    def test_include_transcript_is_true_only_for_on(self) -> None:
        """include_transcript는 on일 때만 True이다."""
        enabled = _parse_options_from_form({"include_transcript": "on"})
        disabled = _parse_options_from_form({"include_transcript": "off"})
        missing = _parse_options_from_form({})

        assert enabled.include_transcript is True
        assert disabled.include_transcript is False
        assert missing.include_transcript is False


class TestPolicyFallback:
    """정책 차단 반복 시 brief 폴백 동작 테스트."""

    @pytest.mark.asyncio
    async def test_repeated_policy_block_retries_with_brief(self) -> None:
        video_id = "video123"
        _policy_block_counts.clear()
        _policy_block_counts[video_id] = 1

        expected = SummaryResult(
            one_line="간단 요약 결과",
            key_points=["포인트"],
            keywords=["키워드"],
        )
        options = SummarizeOptions(detail_level=DetailLevel.DETAILED)

        with patch("app.routers.summarize.summarize_transcript", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.side_effect = [
                SummarizationError("콘텐츠 정책 필터에 의해 요약이 차단되었습니다."),
                expected,
            ]

            summary, used_options, used_fallback = await _summarize_with_policy_fallback(
                video_id,
                "테스트 자막",
                options,
            )

            assert summary == expected
            assert used_fallback is True
            assert used_options.detail_level == DetailLevel.BRIEF
            assert mock_summarize.await_count == 2

    @pytest.mark.asyncio
    async def test_first_policy_block_does_not_retry(self) -> None:
        video_id = "video456"
        _policy_block_counts.clear()
        options = SummarizeOptions(detail_level=DetailLevel.DETAILED)

        with patch("app.routers.summarize.summarize_transcript", new_callable=AsyncMock) as mock_summarize:
            mock_summarize.side_effect = SummarizationError("콘텐츠 정책 필터에 의해 요약이 차단되었습니다.")

            with pytest.raises(SummarizationError):
                await _summarize_with_policy_fallback(video_id, "테스트 자막", options)

            assert mock_summarize.await_count == 1
            assert _policy_block_counts[video_id] == 1
