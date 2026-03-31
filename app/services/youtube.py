"""YouTube 자막/메타데이터 추출 서비스."""

from __future__ import annotations

import asyncio
import re
from functools import partial

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from app.models.exceptions import InvalidURLError, TranscriptNotFoundError
from app.models.schemas import VideoMetadata

# YouTube URL 패턴
_YOUTUBE_URL_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})"),
    re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})"),
]


def extract_video_id(url: str) -> str:
    """YouTube URL에서 영상 ID를 추출한다.

    Args:
        url: YouTube 영상 URL.

    Returns:
        11자리 YouTube 영상 ID.

    Raises:
        InvalidURLError: 유효하지 않은 YouTube URL인 경우.
    """
    if not url or not url.strip():
        raise InvalidURLError()

    url = url.strip()

    for pattern in _YOUTUBE_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return match.group(1)

    raise InvalidURLError()


async def get_transcript(
    video_id: str, languages: list[str] | None = None
) -> str:
    """YouTube 영상의 자막 텍스트를 추출한다.

    Args:
        video_id: YouTube 영상 ID.
        languages: 선호 자막 언어 코드 목록. 기본값은 ["ko", "en"].

    Returns:
        결합된 자막 텍스트.

    Raises:
        TranscriptNotFoundError: 사용 가능한 자막이 없는 경우.
    """
    if languages is None:
        languages = ["ko", "en"]

    loop = asyncio.get_event_loop()

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = await loop.run_in_executor(
            None,
            partial(ytt_api.fetch, video_id, languages=languages),
        )
        text = " ".join(snippet.text for snippet in transcript)
        return text

    except (NoTranscriptFound, TranscriptsDisabled):
        # 지정 언어로 찾지 못하면 자동 생성 자막 시도
        try:
            transcript_list = await loop.run_in_executor(
                None,
                partial(ytt_api.list, video_id),
            )
            # 자동 생성 자막 중 첫 번째 사용
            generated = [t for t in transcript_list if t.is_generated]
            if generated:
                transcript = await loop.run_in_executor(
                    None,
                    partial(ytt_api.fetch, video_id, languages=[generated[0].language_code]),
                )
                text = " ".join(snippet.text for snippet in transcript)
                return text

            raise TranscriptNotFoundError()

        except Exception:
            raise TranscriptNotFoundError()

    except VideoUnavailable:
        raise TranscriptNotFoundError("영상을 찾을 수 없습니다.")

    except Exception as e:
        raise TranscriptNotFoundError(f"자막 추출 중 오류가 발생했습니다: {e}")


async def get_video_metadata(video_id: str) -> VideoMetadata | None:
    """YouTube 영상의 메타데이터를 추출한다.

    Args:
        video_id: YouTube 영상 ID.

    Returns:
        VideoMetadata 객체. 실패 시 None.
    """
    loop = asyncio.get_event_loop()

    try:
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }

        def _extract() -> dict:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(
                    f"https://www.youtube.com/watch?v={video_id}",
                    download=False,
                )

        info = await loop.run_in_executor(None, _extract)

        # duration 포맷팅 (초 → MM:SS 또는 HH:MM:SS)
        duration_sec = info.get("duration", 0) or 0
        if duration_sec >= 3600:
            hours = duration_sec // 3600
            minutes = (duration_sec % 3600) // 60
            seconds = duration_sec % 60
            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            minutes = duration_sec // 60
            seconds = duration_sec % 60
            duration_str = f"{minutes}:{seconds:02d}"

        return VideoMetadata(
            title=info.get("title", ""),
            channel=info.get("channel", "") or info.get("uploader", ""),
            duration=duration_str,
            thumbnail_url=info.get("thumbnail", "")
            or f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        )

    except Exception:
        # 메타데이터 추출 실패 시 None 반환 — 요약 기능에 영향 없음
        return None
