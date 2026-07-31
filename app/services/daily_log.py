"""Daily Log 서비스 — DB 저장 + 날짜별 파일 로깅."""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "history.db"
LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs" / "daily"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS daily_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT    NOT NULL,
    video_id     TEXT    NOT NULL,
    title        TEXT    NOT NULL DEFAULT '',
    channel      TEXT    NOT NULL DEFAULT '',
    one_line     TEXT    NOT NULL DEFAULT '',
    detail_level TEXT    NOT NULL DEFAULT 'normal',
    created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_daily_log_date ON daily_log(date);
"""


# ──────────────────────────────────────────────
# DB 초기화 / CRUD
# ──────────────────────────────────────────────

async def init_db() -> None:
    """daily_log 테이블과 인덱스를 생성한다."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE_SQL)
        await db.execute(_CREATE_INDEX_SQL)
        await db.commit()
    logger.info("Daily-log DB initialized: %s", DB_PATH)


async def save(
    *,
    video_id: str,
    title: str,
    channel: str,
    one_line: str,
    detail_level: str,
) -> int:
    """요약 성공 로그를 DB에 저장하고 생성된 id를 반환한다."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO daily_log (date, video_id, title, channel, one_line, detail_level)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (today, video_id, title, channel, one_line, detail_level),
        )
        await db.commit()
        row_id = cursor.lastrowid
    logger.info("Daily-log saved: id=%s, video_id=%s", row_id, video_id)
    return row_id  # type: ignore[return-value]


async def get_by_date(date: str | None = None) -> list[dict[str, Any]]:
    """특정 날짜의 로그 목록을 반환한다. 미지정 시 오늘."""
    if date is None:
        date = datetime.now(KST).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, video_id, title, channel, one_line,
                   detail_level, created_at
            FROM daily_log
            WHERE date = ?
            ORDER BY id DESC
            """,
            (date,),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_recent_days(days: int = 7) -> list[dict[str, Any]]:
    """최근 N일간 날짜별 요약 건수와 목록을 반환한다."""
    since = (datetime.now(KST) - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, date, video_id, title, channel, one_line,
                   detail_level, created_at
            FROM daily_log
            WHERE date >= ?
            ORDER BY date DESC, id DESC
            """,
            (since,),
        )
        rows = await cursor.fetchall()

    # 날짜별 그룹핑
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        d = dict(row)
        dt = d.pop("date")
        grouped.setdefault(dt, []).append(d)

    return [
        {"date": dt, "count": len(items), "items": items}
        for dt, items in grouped.items()
    ]


# ──────────────────────────────────────────────
# 파일 로깅 (logs/daily/YYYY-MM-DD.log)
# ──────────────────────────────────────────────

_file_logger: logging.Logger | None = None
_current_log_date: str | None = None


def _get_file_logger() -> logging.Logger:
    """오늘(KST) 날짜 파일(`YYYY-MM-DD.log`)에 쓰는 로거를 반환한다. 날짜 변경 시 자동 전환."""
    global _file_logger, _current_log_date

    today = datetime.now(KST).strftime("%Y-%m-%d")

    if _file_logger is not None and _current_log_date == today:
        return _file_logger

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 구버전 `daily.log` 잔존 이월: 오늘 파일이 없을 때만 rename.
    legacy = LOG_DIR / "daily.log"
    today_file = LOG_DIR / f"{today}.log"
    if legacy.exists() and not today_file.exists():
        try:
            legacy.rename(today_file)
        except OSError:
            pass

    fl = logging.getLogger("daily_log_file")
    fl.setLevel(logging.INFO)
    fl.propagate = False

    for h in list(fl.handlers):
        h.close()
        fl.removeHandler(h)

    handler = logging.FileHandler(
        filename=today_file,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    fl.addHandler(handler)

    _file_logger = fl
    _current_log_date = today
    return fl


def _now_str() -> str:
    return datetime.now(KST).strftime("%H:%M:%S")


def log_request(url: str, video_id: str | None = None) -> None:
    """REQUEST 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    if video_id:
        fl.info("[%s] REQUEST  | video_id=%s 추출 완료", _now_str(), video_id)
    else:
        fl.info("[%s] REQUEST  | url=%s", _now_str(), url)


def log_success(
    *,
    video_id: str,
    title: str,
    channel: str,
    detail_level: str,
    elapsed: float,
) -> None:
    """SUCCESS 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    fl.info(
        "[%s] SUCCESS  | video_id=%s | title=%s | channel=%s | detail=%s | elapsed=%.2fs",
        _now_str(), video_id, title, channel, detail_level, elapsed,
    )


def log_failure(
    status: str,
    *,
    video_id: str | None = None,
    url: str | None = None,
    error_msg: str = "",
    elapsed: float | None = None,
) -> None:
    """FAIL_* 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    parts = [f"[{_now_str()}] {status:<16}"]
    if video_id:
        parts.append(f"video_id={video_id}")
    if url:
        parts.append(f"url={url}")
    if elapsed is not None:
        parts.append(f"elapsed={elapsed:.2f}s")
    if error_msg:
        parts.append(error_msg)
    fl.info(" | ".join(parts))


# ──────────────────────────────────────────────
# Reading (오늘의 독서 내용) 파일 로깅
# ──────────────────────────────────────────────


def log_reading_request() -> None:
    """오늘의 독서 요청 시작 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    fl.info("[%s] READING_REQ      | 오늘의 독서 요청", _now_str())


def log_reading_success(
    *,
    page_id: str,
    title: str,
    used_fallback: bool,
    elapsed: float,
) -> None:
    """오늘의 독서 요약 성공 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    fl.info(
        "[%s] READING_OK       | page_id=%s | title=%s | fallback=%s | elapsed=%.2fs",
        _now_str(), page_id, title, used_fallback, elapsed,
    )


def log_reading_failure(
    status: str,
    *,
    page_id: str | None = None,
    error_msg: str = "",
    elapsed: float | None = None,
) -> None:
    """오늘의 독서 요약 실패 이벤트를 파일에 기록한다."""
    fl = _get_file_logger()
    parts = [f"[{_now_str()}] {status:<16}"]
    if page_id:
        parts.append(f"page_id={page_id}")
    if elapsed is not None:
        parts.append(f"elapsed={elapsed:.2f}s")
    if error_msg:
        parts.append(error_msg)
    fl.info(" | ".join(parts))
