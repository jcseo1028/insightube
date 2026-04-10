"""히스토리 조회 라우터."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.schemas import DetailLevel, SummarizeOptions, SummaryResult
from app.services import history as history_service

logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


# --- JSON API ---


@router.get("/api/history")
async def api_list_history(limit: int = 20) -> JSONResponse:
    """최근 히스토리 목록을 JSON으로 반환한다."""
    items = await history_service.list_recent(limit=min(limit, 100))
    return JSONResponse(content={"success": True, "data": items})


@router.get("/api/history/{history_id}")
async def api_get_history(history_id: int) -> JSONResponse:
    """히스토리 단건을 JSON으로 반환한다."""
    item = await history_service.get_by_id(history_id)
    if item is None:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": {"code": "NOT_FOUND", "message": "히스토리를 찾을 수 없습니다."}},
        )
    return JSONResponse(content={"success": True, "data": item})


@router.delete("/api/history/{history_id}")
async def api_delete_history(history_id: int) -> JSONResponse:
    """히스토리 단건을 삭제한다."""
    deleted = await history_service.delete_by_id(history_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": {"code": "NOT_FOUND", "message": "히스토리를 찾을 수 없습니다."}},
        )
    return JSONResponse(content={"success": True})


# --- HTMX partials ---


@router.get("/history/panel", response_class=HTMLResponse)
async def htmx_history_panel(request: Request) -> HTMLResponse:
    """사이드 패널용 히스토리 목록 HTML 파셜을 반환한다."""
    items = await history_service.list_recent(limit=30)
    return templates.TemplateResponse(
        name="partials/history_panel.html",
        request=request,
        context={"items": items},
    )


@router.get("/history/{history_id}", response_class=HTMLResponse)
async def htmx_history_detail(request: Request, history_id: int) -> HTMLResponse:
    """히스토리 단건의 요약 결과 HTML 파셜을 반환한다.

    기존 summary_result.html 파셜을 재사용한다.
    """
    item = await history_service.get_by_id(history_id)
    if item is None:
        return HTMLResponse(
            content='<div class="text-red-500 font-medium p-4">히스토리를 찾을 수 없습니다.</div>',
            status_code=404,
        )

    summary = SummaryResult(
        one_line=item["one_line"],
        key_points=item["key_points"],
        keywords=item["keywords"],
    )

    try:
        detail_level = DetailLevel(item["detail_level"])
    except ValueError:
        detail_level = DetailLevel.DETAILED

    options = SummarizeOptions(detail_level=detail_level)

    return templates.TemplateResponse(
        name="partials/summary_result.html",
        request=request,
        context={
            "video_id": item["video_id"],
            "title": item["title"],
            "channel": item["channel"],
            "duration": item["duration"],
            "thumbnail_url": item["thumbnail_url"],
            "summary": summary,
            "transcript": item["transcript"],
            "options": options,
        },
    )
