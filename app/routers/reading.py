"""오늘의 독서 내용 (Notion 독서 DB) 라우터."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.exceptions import NoCompletedPagesError, NotionError
from app.models.schemas import (
    DetailLevel,
    ReadingPageMeta,
    ReadingSummaryData,
    ReadingSummaryResponse,
    SummarizeOptions,
    SummaryResult,
)
from app.services import notion as notion_service
from app.services.summarizer import summarize_transcript

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


# ──────────────────────────────────────────────
# 페이지(팝업) 라우트
# ──────────────────────────────────────────────


@router.get("/reading/today", response_class=HTMLResponse)
async def reading_today_page(request: Request) -> HTMLResponse:
    """팝업 초기 페이지를 렌더링한다.

    실제 데이터는 페이지 로드 후 HTMX/`fetch`로 `/api/reading/today-summary`를 호출해 채운다.
    """
    return templates.TemplateResponse(
        name="reading_popup.html",
        request=request,
    )


# ──────────────────────────────────────────────
# 데이터 API
# ──────────────────────────────────────────────


def _error_response(code: str, message: str, status: int = 500) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "success": False,
            "error": {"code": code, "message": message},
        },
    )


@router.get("/api/reading/today-summary")
async def api_today_reading_summary() -> JSONResponse:
    """읽기 완료 페이지 중 1건을 랜덤 선택하여 요약 결과를 반환한다."""
    started = time.monotonic()
    try:
        pages = await notion_service.fetch_completed_pages()
        page = notion_service.pick_random_completed(pages)
        page_id: str = page.get("id", "")

        body_text = await notion_service.fetch_page_block_text(page_id)
        input_text, used_fallback = notion_service.build_summary_input(page, body_text)

        options = SummarizeOptions(
            detail_level=DetailLevel.NORMAL,
            include_transcript=False,
        )
        summary: SummaryResult = await summarize_transcript(input_text, options)

        title = notion_service.extract_title(page)
        meta: ReadingPageMeta = notion_service.extract_meta(page)
        notion_url = page.get("url", "")

        elapsed = time.monotonic() - started
        logger.info(
            "[Reading] page_id=%s | fallback=%s | elapsed=%.2fs",
            page_id,
            used_fallback,
            elapsed,
        )

        data = ReadingSummaryData(
            page_id=page_id,
            title=title or "(제목 없음)",
            notion_url=notion_url,
            meta=meta,
            summary=summary,
            used_fallback=used_fallback,
        )
        return JSONResponse(
            content=ReadingSummaryResponse(success=True, data=data).model_dump()
        )

    except NoCompletedPagesError as exc:
        logger.info("[Reading] %s", exc.message)
        return _error_response(exc.code, exc.message, status=404)
    except NotionError as exc:
        logger.warning("[Reading] %s | %s", exc.code, exc.message)
        return _error_response(exc.code, exc.message, status=502)
    except Exception as exc:  # pragma: no cover - 방어적 처리
        logger.exception("[Reading] 예상치 못한 오류")
        return _error_response(
            "UNEXPECTED_ERROR",
            f"예상치 못한 오류가 발생했습니다: {exc}",
            status=500,
        )
