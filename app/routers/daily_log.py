"""Daily Log 조회 라우터."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services import daily_log as daily_log_service

logger = logging.getLogger(__name__)

router = APIRouter()

KST = timezone(timedelta(hours=9))


@router.get("/api/daily-log")
async def api_get_daily_log(date: str | None = None) -> JSONResponse:
    """특정 날짜의 Daily Log를 JSON으로 반환한다. 미지정 시 오늘."""
    if date is None:
        date = datetime.now(KST).strftime("%Y-%m-%d")
    items = await daily_log_service.get_by_date(date)
    return JSONResponse(content={"success": True, "data": items})


@router.get("/api/daily-log/recent")
async def api_get_recent_daily_log(days: int = 7) -> JSONResponse:
    """최근 N일간 날짜별 Daily Log를 JSON으로 반환한다."""
    days = max(1, min(days, 90))
    summaries = await daily_log_service.get_recent_days(days)
    return JSONResponse(content={"success": True, "data": summaries})
