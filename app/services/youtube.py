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

# 자막 문단 구분 간격 (초) — 이 간격마다 줄바꿈 삽입
_PARAGRAPH_GAP_SECONDS = 30.0


def _format_timestamp(seconds: float) -> str:
    """초를 [MM:SS] 형식의 타임스탬프로 변환한다.

    Args:
        seconds: 초 단위 시간.

    Returns:
        "[MM:SS]" 또는 "[H:MM:SS]" 형식 문자열.
    """
    total = int(seconds)
    if total >= 3600:
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"[{h}:{m:02d}:{s:02d}]"
    m = total // 60
    s = total % 60
    return f"[{m:02d}:{s:02d}]"


def _format_transcript(transcript) -> str:
    """자막 snippet 목록을 타임스탬프 기반으로 문단 구분된 텍스트로 변환한다.

    일정 시간 간격(_PARAGRAPH_GAP_SECONDS)마다 줄바꿈과 타임스탬프를 삽입하여
    가독성을 높인다.

    Args:
        transcript: youtube-transcript-api에서 반환된 snippet 리스트.

    Returns:
        포맷팅된 자막 텍스트.
    """
    if not transcript:
        return ""

    snippets = list(transcript)
    paragraphs: list[str] = []
    current_texts: list[str] = []
    paragraph_start: float = snippets[0].start if snippets else 0.0

    for snippet in snippets:
        # 이전 문단 시작으로부터 _PARAGRAPH_GAP_SECONDS 이상 지나면 문단 구분
        if snippet.start - paragraph_start >= _PARAGRAPH_GAP_SECONDS and current_texts:
            timestamp = _format_timestamp(paragraph_start)
            paragraphs.append(f"{timestamp} {' '.join(current_texts)}")
            current_texts = []
            paragraph_start = snippet.start

        current_texts.append(snippet.text.strip())

    # 마지막 문단
    if current_texts:
        timestamp = _format_timestamp(paragraph_start)
        paragraphs.append(f"{timestamp} {' '.join(current_texts)}")

    return "\n\n".join(paragraphs)


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
        text = _format_transcript(transcript)
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
                text = _format_transcript(transcript)
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
