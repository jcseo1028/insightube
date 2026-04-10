"""히스토리 DB 서비스 — SQLite + aiosqlite 기반."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "history.db"

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id       TEXT    NOT NULL,
    url            TEXT    NOT NULL,
    title          TEXT    NOT NULL DEFAULT '',
    channel        TEXT    NOT NULL DEFAULT '',
    duration       TEXT    NOT NULL DEFAULT '',
    thumbnail_url  TEXT    NOT NULL DEFAULT '',
    one_line       TEXT    NOT NULL,
    key_points     TEXT    NOT NULL,
    keywords       TEXT    NOT NULL,
    transcript     TEXT    NOT NULL DEFAULT '',
    detail_level   TEXT    NOT NULL DEFAULT 'detailed',
    created_at     TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(id DESC);
"""


async def init_db() -> None:
    """DB 파일과 테이블을 초기화한다."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(_CREATE_TABLE_SQL)
        await db.execute(_CREATE_INDEX_SQL)
        await db.commit()
    logger.info("History DB initialized: %s", DB_PATH)


async def save(
    *,
    video_id: str,
    url: str,
    title: str,
    channel: str,
    duration: str,
    thumbnail_url: str,
    one_line: str,
    key_points: list[str],
    keywords: list[str],
    transcript: str,
    detail_level: str,
) -> int:
    """요약 결과를 DB에 저장하고 생성된 id를 반환한다."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO history
                (video_id, url, title, channel, duration, thumbnail_url,
                 one_line, key_points, keywords, transcript, detail_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video_id,
                url,
                title,
                channel,
                duration,
                thumbnail_url,
                one_line,
                json.dumps(key_points, ensure_ascii=False),
                json.dumps(keywords, ensure_ascii=False),
                transcript,
                detail_level,
            ),
        )
        await db.commit()
        row_id = cursor.lastrowid
    logger.info("History saved: id=%s, video_id=%s", row_id, video_id)
    return row_id  # type: ignore[return-value]


async def list_recent(limit: int = 20) -> list[dict[str, Any]]:
    """최근 히스토리 목록을 반환한다 (사이드 패널용, transcript 제외)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, video_id, url, title, channel, duration,
                   thumbnail_url, one_line, detail_level, created_at
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_by_id(history_id: int) -> dict[str, Any] | None:
    """히스토리 단건을 조회한다."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM history WHERE id = ?",
            (history_id,),
        )
        row = await cursor.fetchone()
    if row is None:
        return None
    item = dict(row)
    item["key_points"] = json.loads(item["key_points"])
    item["keywords"] = json.loads(item["keywords"])
    return item


async def delete_by_id(history_id: int) -> bool:
    """히스토리 단건을 삭제한다. 삭제 성공 시 True."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM history WHERE id = ?",
            (history_id,),
        )
        await db.commit()
        return cursor.rowcount > 0
