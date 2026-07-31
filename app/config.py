"""환경 변수 및 설정 관리 모듈."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv

# .env 파일 로드
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMProvider(str, Enum):
    """LLM 제공자 유형."""

    GITHUB = "github"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


@dataclass(frozen=True)
class Settings:
    """애플리케이션 설정.

    Attributes:
        llm_provider: LLM 제공자 (github 또는 openai).
        llm_api_key: LLM API 키 (GITHUB_TOKEN 또는 OPENAI_API_KEY).
        llm_base_url: LLM API 호출 베이스 URL.
        llm_model: 사용할 LLM 모델명.
        max_transcript_length: 자막 텍스트 최대 길이.
        summary_language: 요약 결과 언어.
    """

    llm_provider: LLMProvider
    llm_api_key: str
    llm_base_url: str | None
    llm_model: str
    max_transcript_length: int
    summary_language: str
    notion_api_key: str
    notion_reading_db_id: str
    notion_reading_done_property: str


def _detect_provider() -> tuple[LLMProvider, str, str | None]:
    """환경 변수를 확인하여 LLM Provider를 자동 감지한다.

    Returns:
        (provider, api_key, base_url) 튜플.

    Raises:
        RuntimeError: 지원하는 LLM API 키가 하나도 설정되지 않은 경우.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    if anthropic_key:
        return LLMProvider.ANTHROPIC, anthropic_key, None

    if openai_key:
        return LLMProvider.OPENAI, openai_key, None

    if github_token:
        # GitHub Models는 2026-07-30 은퇴. 자동 감지는 유지하되 동작은 보장하지 않음.
        return (
            LLMProvider.GITHUB,
            github_token,
            "https://models.inference.ai.azure.com",
        )

    raise RuntimeError(
        "LLM API 키가 설정되지 않았습니다. "
        "ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 환경 변수를 설정해주세요."
    )


def get_settings() -> Settings:
    """애플리케이션 설정을 생성하여 반환한다.

    Returns:
        Settings 인스턴스.
    """
    provider, api_key, base_url = _detect_provider()

    default_model = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.GITHUB: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-sonnet-4-5",
    }[provider]

    return Settings(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=base_url,
        llm_model=os.getenv("LLM_MODEL", default_model),
        max_transcript_length=int(os.getenv("MAX_TRANSCRIPT_LENGTH", "50000")),
        summary_language=os.getenv("SUMMARY_LANGUAGE", "ko"),
        notion_api_key=os.getenv("NOTION_API_KEY", "").strip(),
        notion_reading_db_id=os.getenv("NOTION_READING_DB_ID", "").strip(),
        notion_reading_done_property=os.getenv(
            "NOTION_READING_DONE_PROPERTY", "읽기 종료"
        ).strip(),
    )
