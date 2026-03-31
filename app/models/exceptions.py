"""커스텀 예외 클래스 정의."""

from __future__ import annotations


class InvalidURLError(Exception):
    """유효하지 않은 YouTube URL일 때 발생하는 예외."""

    def __init__(self, message: str = "유효하지 않은 YouTube URL입니다.") -> None:
        self.message = message
        super().__init__(self.message)


class TranscriptNotFoundError(Exception):
    """자막을 찾을 수 없을 때 발생하는 예외."""

    def __init__(self, message: str = "자막을 사용할 수 없는 영상입니다.") -> None:
        self.message = message
        super().__init__(self.message)


class SummarizationError(Exception):
    """AI 요약 처리 중 오류가 발생했을 때의 예외."""

    def __init__(self, message: str = "요약 처리 중 오류가 발생했습니다.") -> None:
        self.message = message
        super().__init__(self.message)
