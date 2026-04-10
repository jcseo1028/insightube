"""Pydantic 요청/응답 스키마 정의."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class DetailLevel(str, Enum):
    """요약 상세도 수준."""

    BRIEF = "brief"      # 간단: 핵심만
    NORMAL = "normal"    # 보통: 기본값
    DETAILED = "detailed"  # 상세: 풍부한 설명


class SummarizeOptions(BaseModel):
    """요약 옵션 설정."""

    detail_level: DetailLevel = Field(
        default=DetailLevel.NORMAL,
        description="요약 상세도 수준 (brief/normal/detailed)",
    )
    max_key_points: int = Field(
        default=7,
        ge=3,
        le=15,
        description="최대 주요 포인트 수 (3~15)",
    )
    max_keywords: int = Field(
        default=5,
        ge=3,
        le=10,
        description="최대 키워드 수 (3~10)",
    )
    include_transcript: bool = Field(
        default=True,
        description="전체 스크립트 포함 여부",
    )


class SummarizeRequest(BaseModel):
    """요약 요청 스키마."""

    url: str = Field(..., description="YouTube 영상 URL")
    options: SummarizeOptions = Field(
        default_factory=SummarizeOptions,
        description="요약 옵션",
    )


class VideoMetadata(BaseModel):
    """YouTube 영상 메타데이터."""

    title: str = Field(default="", description="영상 제목")
    channel: str = Field(default="", description="채널명")
    duration: str = Field(default="", description="영상 길이 (MM:SS)")
    thumbnail_url: str = Field(default="", description="썸네일 URL")


class SummaryResult(BaseModel):
    """AI 요약 결과."""

    one_line: str = Field(..., description="한 줄 핵심 요약")
    key_points: list[str] = Field(..., description="주요 포인트 목록")
    keywords: list[str] = Field(..., description="키워드 태그 목록")


class SummarizeData(BaseModel):
    """요약 응답 데이터."""

    video_id: str
    title: str = ""
    channel: str = ""
    duration: str = ""
    thumbnail_url: str = ""
    summary: SummaryResult
    transcript: str = Field(default="", description="전체 자막 텍스트")


class ErrorDetail(BaseModel):
    """에러 상세 정보."""

    code: str
    message: str


class SummarizeResponse(BaseModel):
    """요약 API 응답."""

    success: bool
    data: SummarizeData | None = None
    error: ErrorDetail | None = None


# --- 히스토리 스키마 ---


class HistoryListItem(BaseModel):
    """히스토리 목록용 간략 항목."""

    id: int
    video_id: str
    url: str
    title: str = ""
    channel: str = ""
    duration: str = ""
    thumbnail_url: str = ""
    one_line: str
    detail_level: str = "normal"
    created_at: str


class HistoryDetail(BaseModel):
    """히스토리 상세 항목 (요약 전체 포함)."""

    id: int
    video_id: str
    url: str
    title: str = ""
    channel: str = ""
    duration: str = ""
    thumbnail_url: str = ""
    one_line: str
    key_points: list[str]
    keywords: list[str]
    transcript: str = ""
    detail_level: str = "normal"
    created_at: str
