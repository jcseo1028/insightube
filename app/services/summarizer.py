"""LangChain 기반 AI 요약 서비스."""

from __future__ import annotations

import asyncio
import logging
import re

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings, LLMProvider
from app.models.schemas import (
    DetailLevel,
    ReadingBonkkaejeokSummary,
    SummarizeOptions,
    SummaryResult,
)
from app.models.exceptions import SummarizationError

logger = logging.getLogger(__name__)

# GitHub Models 동시 요청 제한 (UserConcurrentRequests 방지)
_MAX_CONCURRENT_REQUESTS = 2


def _create_llm() -> ChatOpenAI:
    """설정에 따라 LLM 인스턴스를 생성한다.

    Returns:
        ChatOpenAI 인스턴스.
    """
    settings = get_settings()

    kwargs: dict = {
        "model": settings.llm_model,
        "api_key": settings.llm_api_key,
        "temperature": 0.3,
        "timeout": 60,
        "max_retries": 5,  # 429 등 일시적 오류 시 자동 재시도
    }

    if settings.llm_provider == LLMProvider.GITHUB:
        kwargs["base_url"] = settings.llm_base_url

    return ChatOpenAI(**kwargs)


# --- 출력 파서 ---
_output_parser = PydanticOutputParser(pydantic_object=SummaryResult)


# --- 상세도별 프롬프트 규칙 ---
_DETAIL_RULES: dict[DetailLevel, str] = {
    DetailLevel.BRIEF: (
        "## 요약 규칙\n"
        "1. one_line: 영상의 핵심 내용을 1문장으로 간결하게 요약\n"
        "2. key_points: 가장 중요한 핵심 포인트만 {max_key_points}개 이내로 짧게 정리\n"
        "3. keywords: 핵심 키워드 {max_keywords}개\n"
        "4. 모든 결과는 한국어로 작성\n"
        "5. 간결함을 최우선으로 하고, 불필요한 설명은 생략"
    ),
    DetailLevel.NORMAL: (
        "## 요약 규칙\n"
        "1. one_line: 영상의 핵심 내용을 1~2문장으로 요약\n"
        "2. key_points: 주요 포인트를 {max_key_points}개 이내의 bullet point로 정리. "
        "각 포인트는 구체적인 내용을 포함\n"
        "3. keywords: 핵심 키워드 {max_keywords}개\n"
        "4. 모든 결과는 한국어로 작성"
    ),
    DetailLevel.DETAILED: (
        "## 요약 규칙\n"
        "1. one_line: 영상의 핵심 내용과 핵심 맥락을 2~3문장으로 상세 요약\n"
        "2. key_points: 영상의 내용을 {max_key_points}개 이내의 bullet point로 상세하게 정리. "
        "각 포인트는 구체적인 사실, 수치, 예시를 포함하여 충분히 설명. "
        "단순 나열이 아니라 맥락과 배경까지 서술\n"
        "3. keywords: 핵심 키워드 {max_keywords}개\n"
        "4. 모든 결과는 한국어로 작성\n"
        "5. 가능한 한 원본의 풍부한 디테일을 살려서 요약"
    ),
}


def _build_summary_prompt(options: SummarizeOptions) -> ChatPromptTemplate:
    """옵션에 따라 요약 프롬프트를 동적으로 생성한다.

    Args:
        options: 요약 옵션 설정.

    Returns:
        ChatPromptTemplate 인스턴스.
    """
    rules = _DETAIL_RULES[options.detail_level].format(
        max_key_points=options.max_key_points,
        max_keywords=options.max_keywords,
    )

    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 YouTube 영상 요약 전문가입니다. "
                "주어진 자막 텍스트를 분석하여 핵심 내용을 구조화된 형식으로 요약해주세요.\n\n"
                "{format_instructions}",
            ),
            (
                "human",
                "다음 YouTube 영상의 자막 텍스트를 요약해주세요.\n\n"
                f"{rules}\n\n"
                "## 자막 텍스트\n"
                "{transcript}",
            ),
        ]
    )


# --- Map 단계 프롬프트 (긴 텍스트 분할 시) ---
_MAP_PROMPT_BRIEF = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 텍스트 요약 전문가입니다. "
            "주어진 텍스트 조각의 핵심 내용을 간결하게 요약해주세요.",
        ),
        (
            "human",
            "다음 텍스트 조각을 2~3문장으로 핵심만 요약해주세요. 한국어로 작성하세요.\n\n"
            "{text}",
        ),
    ]
)

_MAP_PROMPT_NORMAL = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 텍스트 요약 전문가입니다. "
            "주어진 텍스트 조각의 핵심 내용을 간결하게 요약해주세요.",
        ),
        (
            "human",
            "다음 텍스트 조각을 3~5문장으로 요약해주세요. 한국어로 작성하세요.\n\n"
            "{text}",
        ),
    ]
)

_MAP_PROMPT_DETAILED = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "당신은 텍스트 요약 전문가입니다. "
            "주어진 텍스트 조각의 내용을 구체적인 디테일을 살려 요약해주세요.",
        ),
        (
            "human",
            "다음 텍스트 조각을 5~8문장으로 상세하게 요약해주세요. "
            "구체적인 사실, 수치, 예시를 반드시 포함하세요. 한국어로 작성하세요.\n\n"
            "{text}",
        ),
    ]
)

_MAP_PROMPTS: dict[DetailLevel, ChatPromptTemplate] = {
    DetailLevel.BRIEF: _MAP_PROMPT_BRIEF,
    DetailLevel.NORMAL: _MAP_PROMPT_NORMAL,
    DetailLevel.DETAILED: _MAP_PROMPT_DETAILED,
}


# --- 토큰 기준 분할 임계값 ---
_TOKEN_THRESHOLD = 4000
_CHARS_PER_TOKEN = 4  # 대략적인 한국어/영어 혼합 기준

_POLICY_SENSITIVE_PATTERNS = [
    r"자해",
    r"자살",
    r"죽고\s*싶",
    r"극단적\s*선택",
    r"self\s*-?\s*harm",
    r"suicid(?:e|al)",
    r"kill\s+myself",
]


def _is_content_filter_error(error: Exception) -> bool:
    """예외 메시지에 콘텐츠 필터 차단 신호가 있는지 확인한다."""
    message = str(error).lower()
    return "content_filter" in message or "responsibleaipolicyviolation" in message


def _sanitize_transcript_for_policy(transcript: str) -> str:
    """정책 필터 민감 표현을 최소 마스킹해 재요약 성공률을 높인다."""
    sanitized = transcript
    for pattern in _POLICY_SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[민감 내용]", sanitized, flags=re.IGNORECASE)
    return sanitized


async def summarize_transcript(
    transcript: str,
    options: SummarizeOptions | None = None,
) -> SummaryResult:
    """자막 텍스트를 AI로 요약한다.

    Args:
        transcript: YouTube 영상 자막 텍스트.
        options: 요약 옵션 설정. None이면 기본값 사용.

    Returns:
        구조화된 요약 결과.

    Raises:
        SummarizationError: 요약 처리 중 오류 발생 시.
    """
    if options is None:
        options = SummarizeOptions()

    try:
        llm = _create_llm()

        async def _summarize_by_length(input_text: str) -> SummaryResult:
            estimated_tokens = len(input_text) // _CHARS_PER_TOKEN
            if estimated_tokens <= _TOKEN_THRESHOLD:
                return await _summarize_short(llm, input_text, options)
            return await _summarize_long(llm, input_text, options)

        try:
            return await _summarize_by_length(transcript)
        except Exception as e:
            if not _is_content_filter_error(e):
                raise

            sanitized = _sanitize_transcript_for_policy(transcript)
            if sanitized == transcript:
                raise SummarizationError(
                    "콘텐츠 정책 필터에 의해 요약이 차단되었습니다. "
                    "다른 영상으로 시도해 주세요."
                ) from e

            logger.warning("콘텐츠 정책 필터 감지: 민감 표현 마스킹 후 1회 재시도")
            try:
                return await _summarize_by_length(sanitized)
            except Exception as retry_error:
                if _is_content_filter_error(retry_error):
                    raise SummarizationError(
                        "콘텐츠 정책 필터에 의해 요약이 차단되었습니다. "
                        "다른 영상으로 시도해 주세요."
                    ) from retry_error
                raise

    except SummarizationError:
        raise
    except Exception as e:
        raise SummarizationError(f"요약 처리 중 오류가 발생했습니다: {e}")


async def _summarize_short(
    llm: ChatOpenAI,
    transcript: str,
    options: SummarizeOptions,
) -> SummaryResult:
    """짧은 텍스트를 단일 요약(Stuff)한다.

    Args:
        llm: ChatOpenAI 인스턴스.
        transcript: 자막 텍스트.
        options: 요약 옵션.

    Returns:
        SummaryResult 객체.
    """
    prompt = _build_summary_prompt(options)
    chain = prompt | llm | _output_parser

    result = await chain.ainvoke(
        {
            "transcript": transcript,
            "format_instructions": _output_parser.get_format_instructions(),
        }
    )
    return result


async def _summarize_long(
    llm: ChatOpenAI,
    transcript: str,
    options: SummarizeOptions,
) -> SummaryResult:
    """긴 텍스트를 Map-Reduce 방식으로 요약한다.

    Args:
        llm: ChatOpenAI 인스턴스.
        transcript: 자막 텍스트.
        options: 요약 옵션.

    Returns:
        SummaryResult 객체.
    """
    # 1. 텍스트 분할
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(transcript)

    # 2. Map 단계 — 각 조각을 요약 (동시 요청 수 제한)
    map_prompt = _MAP_PROMPTS[options.detail_level]
    map_chain = map_prompt | llm
    semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)

    async def _map_with_limit(chunk: str, idx: int):
        async with semaphore:
            logger.info("Map 단계 %d/%d 처리 중...", idx + 1, len(chunks))
            return await map_chain.ainvoke({"text": chunk})

    map_tasks = [_map_with_limit(chunk, i) for i, chunk in enumerate(chunks)]
    map_results = await asyncio.gather(*map_tasks)
    combined_summary = "\n\n".join(r.content for r in map_results)

    # 3. Reduce 단계 — 합쳐진 요약을 최종 구조화
    reduce_prompt = _build_summary_prompt(options)
    reduce_chain = reduce_prompt | llm | _output_parser
    result = await reduce_chain.ainvoke(
        {
            "transcript": combined_summary,
            "format_instructions": _output_parser.get_format_instructions(),
        }
    )
    return result


# ──────────────────────────────────────────────
# 독서 전용 요약 (본깨적 3섹션 구조)
# ──────────────────────────────────────────────


_reading_output_parser = PydanticOutputParser(pydantic_object=ReadingBonkkaejeokSummary)


_READING_SYSTEM_PROMPT = (
    "당신은 독서 메모 정리를 돕는 큐레이터입니다. "
    "사용자가 책을 읽으며 직접 정리한 '본깨적(본 것 / 깨달은 것 / 적용할 것)' 노트를 토대로, "
    "나중에 사용자가 책 내용을 빠르게 환기할 수 있도록 구조화된 요약을 작성합니다.\n\n"
    "{format_instructions}"
)


_READING_HUMAN_PROMPT = (
    "다음은 사용자의 독서 노트입니다. 본깨적 섹션이 비어 있다면 본문을 활용해 추정하되, "
    "사용자가 직접 작성한 본깨적 섹션이 있다면 **반드시 그 내용을 우선시**해 요약하세요.\n\n"
    "## 작성 규칙\n"
    "1. one_line: 책 전체를 관통하는 한 문장 (2~3 문장 이내, 한국어)\n"
    "2. seen: 책에서 본 사실·핵심 인용·핵심 표현을 {max_items}개 이내. "
    "구체적인 표현/예문/수치 위주로 정리\n"
    "3. realized: 책을 통해 깨달은 통찰·생각의 전환을 {max_items}개 이내. "
    "단순 사실 나열이 아닌 '왜 중요한가'를 드러내는 형태로 작성\n"
    "4. applied: 일상/업무/행동에 적용할 구체적 실천 항목을 {max_items}개 이내. "
    "동사로 시작하고 즉시 실행 가능한 형태로 작성 (예: '~하기', '~을 시작하기')\n"
    "5. keywords: 나중에 책을 떠올릴 키워드 {max_keywords}개 (해시태그 형태가 아닌 단어/짧은 구)\n"
    "6. 모든 결과는 한국어로 작성\n"
    "7. 각 항목은 한 줄로 간결하게, 단 의미가 명확하도록 충분히 구체적으로\n\n"
    "## 독서 노트\n"
    "{notes}"
)


_reading_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _READING_SYSTEM_PROMPT),
        ("human", _READING_HUMAN_PROMPT),
    ]
)


async def summarize_reading(
    notes: str,
    *,
    max_items: int = 5,
    max_keywords: int = 5,
) -> ReadingBonkkaejeokSummary:
    """독서 노트(본깨적 + 메타)를 본깨적 3섹션 구조로 요약한다.

    Args:
        notes: `notion.build_summary_input`로 만든 입력 텍스트.
        max_items: seen/realized/applied 각 섹션의 최대 항목 수.
        max_keywords: keywords 최대 항목 수.

    Returns:
        ReadingBonkkaejeokSummary.

    Raises:
        SummarizationError
    """
    try:
        llm = _create_llm()
        chain = _reading_prompt | llm | _reading_output_parser
        result = await chain.ainvoke(
            {
                "notes": notes,
                "max_items": max_items,
                "max_keywords": max_keywords,
                "format_instructions": _reading_output_parser.get_format_instructions(),
            }
        )
        return result
    except SummarizationError:
        raise
    except Exception as e:
        raise SummarizationError(f"독서 요약 처리 중 오류가 발생했습니다: {e}")
