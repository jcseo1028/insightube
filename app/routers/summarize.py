"""요약 관련 API 라우터."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.models.schemas import (
    DetailLevel,
    SummarizeData,
    SummarizeOptions,
    SummarizeRequest,
    SummarizeResponse,
    SummaryResult,
)
from app.services.youtube import extract_video_id, get_transcript, get_video_metadata
from app.services.summarizer import summarize_transcript
from app.services import history as history_service
from app.services import daily_log as daily_log_service
from app.config import get_settings

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


@router.post("/api/summarize", response_model=SummarizeResponse)
async def api_summarize(body: SummarizeRequest) -> SummarizeResponse:
    """JSON API로 YouTube 영상을 요약한다.

    Args:
        body: YouTube URL과 옵션이 포함된 요청 데이터.

    Returns:
        구조화된 요약 응답.
    """
    start = time.monotonic()
    logger.info("[API] POST /api/summarize 요청 수신 | url=%s", body.url)
    daily_log_service.log_request(url=body.url)

    # 1. URL에서 video_id 추출 (API 키 불필요 단계 — 먼저 검증)
    video_id = extract_video_id(body.url)
    logger.info("[API] video_id=%s 추출 완료", video_id)
    daily_log_service.log_request(url=body.url, video_id=video_id)

    settings = get_settings()

    # 2. 자막 추출 + 메타데이터 추출 (병렬)
    transcript_task = get_transcript(video_id)
    metadata_task = get_video_metadata(video_id)
    transcript, metadata = await asyncio.gather(transcript_task, metadata_task)

    # 3. 자막 길이 제한
    max_len = settings.max_transcript_length
    if len(transcript) > max_len:
        transcript = transcript[:max_len]

    # 4. AI 요약 (옵션 전달)
    summary: SummaryResult = await summarize_transcript(transcript, body.options)

    # 5. 응답 구성
    data = SummarizeData(
        video_id=video_id,
        title=metadata.title if metadata else "",
        channel=metadata.channel if metadata else "",
        duration=metadata.duration if metadata else "",
        thumbnail_url=metadata.thumbnail_url
        if metadata
        else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        summary=summary,
        transcript=transcript if body.options.include_transcript else "",
    )

    elapsed = time.monotonic() - start
    logger.info("[API] video_id=%s 요약 완료 | %.2fs", video_id, elapsed)

    # 6. 히스토리 저장 (실패해도 응답에 영향 없음)
    try:
        await history_service.save(
            video_id=video_id,
            url=str(body.url),
            title=data.title,
            channel=data.channel,
            duration=data.duration,
            thumbnail_url=data.thumbnail_url,
            one_line=summary.one_line,
            key_points=summary.key_points,
            keywords=summary.keywords,
            transcript=data.transcript,
            detail_level=body.options.detail_level.value,
        )
    except Exception:
        logger.warning("[API] 히스토리 저장 실패", exc_info=True)

    # 7. Daily Log 저장 + 파일 로깅
    try:
        await daily_log_service.save(
            video_id=video_id,
            title=data.title,
            channel=data.channel,
            one_line=summary.one_line,
            detail_level=body.options.detail_level.value,
        )
    except Exception:
        logger.warning("[API] Daily-log DB 저장 실패", exc_info=True)
    daily_log_service.log_success(
        video_id=video_id,
        title=data.title,
        channel=data.channel,
        detail_level=body.options.detail_level.value,
        elapsed=elapsed,
    )

    return SummarizeResponse(success=True, data=data)


def _parse_options_from_form(form_data: dict) -> SummarizeOptions:
    """폼 데이터에서 SummarizeOptions를 파싱한다.

    Args:
        form_data: 폼으로부터 전달된 데이터 딕셔너리.

    Returns:
        SummarizeOptions 인스턴스.
    """
    detail_level_str = form_data.get("detail_level", "detailed")
    try:
        detail_level = DetailLevel(detail_level_str)
    except ValueError:
        detail_level = DetailLevel.DETAILED

    try:
        max_key_points = int(form_data.get("max_key_points", "7"))
        max_key_points = max(3, min(15, max_key_points))
    except (ValueError, TypeError):
        max_key_points = 7

    try:
        max_keywords = int(form_data.get("max_keywords", "5"))
        max_keywords = max(3, min(10, max_keywords))
    except (ValueError, TypeError):
        max_keywords = 5

    include_transcript = form_data.get("include_transcript", "off") == "on"

    return SummarizeOptions(
        detail_level=detail_level,
        max_key_points=max_key_points,
        max_keywords=max_keywords,
        include_transcript=include_transcript,
    )


@router.post("/summarize", response_class=HTMLResponse)
async def htmx_summarize(request: Request) -> HTMLResponse:
    """HTMX 요청으로 YouTube 영상을 요약하고 HTML 파셜을 반환한다.

    Args:
        request: FastAPI Request 객체.

    Returns:
        요약 결과 HTML 파셜.
    """
    start = time.monotonic()
    logger.info("[HTMX] POST /summarize 요청 수신")

    # 폼 데이터 파싱
    form = await request.form()
    url = form.get("url", "")
    options = _parse_options_from_form(dict(form))
    daily_log_service.log_request(url=str(url))

    # 1. URL에서 video_id 추출 (API 키 불필요 단계 — 먼저 검증)
    video_id = extract_video_id(str(url))
    logger.info("[HTMX] video_id=%s 추출 완료 | detail_level=%s", video_id, options.detail_level.value)
    daily_log_service.log_request(url=str(url), video_id=video_id)

    settings = get_settings()

    # 2. 자막 추출 + 메타데이터 추출 (병렬)
    transcript_task = get_transcript(video_id)
    metadata_task = get_video_metadata(video_id)
    transcript, metadata = await asyncio.gather(transcript_task, metadata_task)

    # 3. 자막 길이 제한
    max_len = settings.max_transcript_length
    if len(transcript) > max_len:
        transcript = transcript[:max_len]

    # 4. AI 요약 (옵션 전달)
    summary: SummaryResult = await summarize_transcript(transcript, options)

    elapsed = time.monotonic() - start
    logger.info("[HTMX] video_id=%s 요약 완료 | %.2fs", video_id, elapsed)

    # 6. 히스토리 저장 (실패해도 응답에 영향 없음)
    try:
        await history_service.save(
            video_id=video_id,
            url=str(url),
            title=metadata.title if metadata else "",
            channel=metadata.channel if metadata else "",
            duration=metadata.duration if metadata else "",
            thumbnail_url=metadata.thumbnail_url
            if metadata
            else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            one_line=summary.one_line,
            key_points=summary.key_points,
            keywords=summary.keywords,
            transcript=transcript if options.include_transcript else "",
            detail_level=options.detail_level.value,
        )
    except Exception:
        logger.warning("[HTMX] 히스토리 저장 실패", exc_info=True)

    # Daily Log 저장 + 파일 로깅
    try:
        await daily_log_service.save(
            video_id=video_id,
            title=metadata.title if metadata else "",
            channel=metadata.channel if metadata else "",
            one_line=summary.one_line,
            detail_level=options.detail_level.value,
        )
    except Exception:
        logger.warning("[HTMX] Daily-log DB 저장 실패", exc_info=True)
    daily_log_service.log_success(
        video_id=video_id,
        title=metadata.title if metadata else "",
        channel=metadata.channel if metadata else "",
        detail_level=options.detail_level.value,
        elapsed=elapsed,
    )

    # 7. HTML 파셜 렌더링
    response = templates.TemplateResponse(
        name="partials/summary_result.html",
        request=request,
        context={
            "video_id": video_id,
            "title": metadata.title if metadata else "",
            "channel": metadata.channel if metadata else "",
            "duration": metadata.duration if metadata else "",
            "thumbnail_url": metadata.thumbnail_url
            if metadata
            else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "summary": summary,
            "transcript": transcript if options.include_transcript else "",
            "options": options,
        },
    )
    response.headers["HX-Trigger"] = "historyUpdated"
    return response
