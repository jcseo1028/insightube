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
from app.routers import summarize, history, daily_log, reading
from app.services.history import init_db
from app.services import daily_log as daily_log_service

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """DB 초기화 등 앱 시작/종료 시 실행할 작업."""
    await init_db()
    await daily_log_service.init_db()
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
app.include_router(daily_log.router)
app.include_router(reading.router)


def _build_htmx_error_html(*, title: str, message: str, tone: str = "error") -> str:
    """HTMX 결과 영역에 바로 렌더링할 에러 블록 HTML을 생성한다."""
    if tone == "warning":
        container = "border-amber-200 bg-amber-50 text-amber-800"
        title_color = "text-amber-900"
    else:
        container = "border-red-200 bg-red-50 text-red-700"
        title_color = "text-red-800"

    return (
        "<section class='rounded-2xl border p-4 md:p-5 "
        f"{container}'>"
        f"<h3 class='font-semibold {title_color}'>{title}</h3>"
        f"<p class='mt-2 text-sm leading-relaxed'>{message}</p>"
        "</section>"
    )


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
    daily_log_service.log_failure("FAIL_URL", url=str(request.url), error_msg=exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        return HTMLResponse(
            content=_build_htmx_error_html(
                title="URL 형식을 확인해 주세요",
                message=exc.message,
            ),
            status_code=200,
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
    daily_log_service.log_failure("FAIL_TRANSCRIPT", url=str(request.url), error_msg=exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        return HTMLResponse(
            content=_build_htmx_error_html(
                title="자막을 찾을 수 없습니다",
                message=exc.message,
            ),
            status_code=200,
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
    daily_log_service.log_failure("FAIL_SUMMARY", url=str(request.url), error_msg=exc.message)
    is_htmx = request.headers.get("HX-Request")
    if is_htmx:
        is_policy_blocked = "콘텐츠 정책 필터" in exc.message
        title = "콘텐츠 정책으로 요약이 제한되었습니다" if is_policy_blocked else "요약 중 오류가 발생했습니다"
        message = (
            exc.message + " 필요하면 요약 상세도를 '간단'으로 바꿔 다시 시도해 주세요."
            if is_policy_blocked
            else exc.message
        )
        return HTMLResponse(
            content=_build_htmx_error_html(
                title=title,
                message=message,
                tone="warning" if is_policy_blocked else "error",
            ),
            status_code=200,
        )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {"code": "SUMMARIZATION_ERROR", "message": exc.message},
        },
    )
