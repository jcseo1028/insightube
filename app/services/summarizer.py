"""LangChain 기반 AI 요약 서비스."""

from __future__ import annotations

import asyncio
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings, LLMProvider
from app.models.schemas import DetailLevel, SummarizeOptions, SummaryResult
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
        estimated_tokens = len(transcript) // _CHARS_PER_TOKEN

        if estimated_tokens <= _TOKEN_THRESHOLD:
            return await _summarize_short(llm, transcript, options)
        else:
            return await _summarize_long(llm, transcript, options)

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
