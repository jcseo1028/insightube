"""요약 라우터 옵션 파싱 테스트."""

from __future__ import annotations

from app.models.schemas import DetailLevel
from app.routers.summarize import _parse_options_from_form


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
