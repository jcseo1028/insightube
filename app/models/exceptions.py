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


class NotionError(Exception):
    """Notion API 연동 중 발생하는 예외 베이스 클래스."""

    code: str = "NOTION_ERROR"

    def __init__(self, message: str = "Notion API 호출 중 오류가 발생했습니다.") -> None:
        self.message = message
        super().__init__(self.message)


class NotionAuthError(NotionError):
    """Notion API 인증 실패."""

    code = "NOTION_AUTH_ERROR"

    def __init__(self, message: str = "Notion API 인증에 실패했습니다.") -> None:
        super().__init__(message)


class NotionNotSharedError(NotionError):
    """대상 DB가 Integration과 공유되지 않은 경우."""

    code = "NOTION_NOT_SHARED"

    def __init__(
        self,
        message: str = "Notion DB가 Integration과 공유되어 있지 않습니다.",
    ) -> None:
        super().__init__(message)


class NotionRateLimitError(NotionError):
    """Notion API 호출 제한 초과."""

    code = "NOTION_RATE_LIMIT"

    def __init__(self, message: str = "Notion API 호출 제한을 초과했습니다.") -> None:
        super().__init__(message)


class NotionSchemaMismatchError(NotionError):
    """완료 판별 속성이 없거나 타입이 date가 아님."""

    code = "NOTION_SCHEMA_MISMATCH"

    def __init__(
        self,
        message: str = "Notion DB 스키마가 예상과 다릅니다 (date 속성 필요).",
    ) -> None:
        super().__init__(message)


class NoCompletedPagesError(NotionError):
    """읽기 완료 페이지가 0건일 때 발생."""

    code = "NO_COMPLETED_PAGES"

    def __init__(
        self, message: str = "읽기 완료된 독서 페이지가 없습니다."
    ) -> None:
        super().__init__(message)
