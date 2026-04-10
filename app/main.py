"""FastAPI 앱 진입점."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.models.exceptions import InvalidURLError, TranscriptNotFoundError, SummarizationError
from app.routers import summarize, history
from app.services.history import init_db

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """DB 초기화 등 앱 시작/종료 시 실행할 작업."""
    await init_db()
    yield


# --- 앱 인스턴스 ---
app = FastAPI(
    title="InSighTube",
    description="YouTube 영상 핵심 내용 AI 요약 서비스",
    version="0.1.0",
    lifespan=lifespan,
)

# --- 정적 파일 & 템플릿 ---
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# --- 라우터 등록 ---
app.include_router(summarize.router)
app.include_router(history.router)


# --- 페이지 라우트 ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """메인 페이지를 렌더링한다."""
    return templates.TemplateResponse(name="index.html", request=request)


# --- 커스텀 예외 핸들러 ---
@app.exception_handler(InvalidURLError)
async def invalid_url_handler(request: Request, exc: InvalidURLError) -> JSONResponse:
    """유효하지 않은 URL 에러 핸들러."""
    logger.warning("INVALID_URL | path=%s | %s", request.url.path, exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        return HTMLResponse(
            content=f'<div class="text-red-500 font-medium p-4">{exc.message}</div>',
            status_code=400,
        )
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {"code": "INVALID_URL", "message": exc.message},
        },
    )


@app.exception_handler(TranscriptNotFoundError)
async def transcript_not_found_handler(
    request: Request, exc: TranscriptNotFoundError
) -> JSONResponse:
    """자막 없음 에러 핸들러."""
    logger.warning("TRANSCRIPT_NOT_FOUND | path=%s | %s", request.url.path, exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        return HTMLResponse(
            content=f'<div class="text-red-500 font-medium p-4">{exc.message}</div>',
            status_code=404,
        )
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": {"code": "TRANSCRIPT_NOT_FOUND", "message": exc.message},
        },
    )


@app.exception_handler(SummarizationError)
async def summarization_error_handler(
    request: Request, exc: SummarizationError
) -> JSONResponse:
    """요약 오류 핸들러."""
    logger.error("SUMMARIZATION_ERROR | path=%s | %s", request.url.path, exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        return HTMLResponse(
            content=f'<div class="text-red-500 font-medium p-4">{exc.message}</div>',
            status_code=500,
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "SUMMARIZATION_ERROR", "message": exc.message},
        },
    )
