"""Fetch a YouTube video's transcript as a single block of text."""

from xml.etree.ElementTree import ParseError

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


class TranscriptUnavailable(Exception):
    pass


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str:
    """Return the full transcript text for a video, or raise TranscriptUnavailable."""
    languages = languages or ["en"]
    api = YouTubeTranscriptApi()
    try:
        fetched = api.fetch(video_id, languages=languages)
    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable, ParseError) as e:
        raise TranscriptUnavailable(str(e)) from e

    # Each snippet has .text, .start, .duration
    return " ".join(snippet.text.strip() for snippet in fetched if snippet.text.strip())
