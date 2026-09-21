"""Fetch a YouTube video's transcript as a single block of text."""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


class TranscriptUnavailable(Exception):
    pass


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Server-side fallback fetch. Note: cloud hosts (Render, Fly.io, AWS,
    etc.) are frequently IP-blocked by YouTube's transcript endpoint --
    this is a known limitation of fetching transcripts from a datacenter.
    The extension fetches the transcript in the browser instead (see
    extension/content.js) and sends it to /ingest directly, which sidesteps
    this entirely; this function only runs if no transcript was supplied.
    """
    languages = languages or ["en"]
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=languages)
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as e:
        raise TranscriptUnavailable(str(e)) from e
    except Exception as e:
        # Catches RequestBlocked / IpBlocked and anything else the library
        # raises that isn't one of the specific cases above.
        raise TranscriptUnavailable(
            f"Server-side transcript fetch failed ({e}). This usually means "
            "the host's IP is blocked by YouTube -- pass the transcript "
            "from the client instead."
        ) from e

    return " ".join(snippet.text.strip() for snippet in fetched if snippet.text.strip())
