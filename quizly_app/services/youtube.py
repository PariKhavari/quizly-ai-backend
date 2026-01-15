from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from typing import Tuple
from yt_dlp import YoutubeDL
from .utils import (
    QuizlyValidationError,
    build_yt_dlp_options,
    canonical_youtube_url,
    extract_youtube_video_id,
)


@dataclass(frozen=True)
class DownloadResult:
    """Result container for a YouTube audio download."""

    video_id: str
    video_url: str
    audio_path: str


def download_youtube_audio(url: str) -> DownloadResult:
    """
    Download the best available audio for a YouTube URL using yt-dlp.
    Returns:
        DownloadResult: includes canonical video_url and the downloaded audio file path.

        Use a stable template. yt-dlp will choose the correct extension.
        yt-dlp may return different keys depending on extraction result    
        Persist the audio file to a non-temp location by copying it out.
        The TemporaryDirectory will be deleted after this function returns,
        so we must move the file to a new temp file that survives.
    """
    video_id = extract_youtube_video_id(url)
    video_url = canonical_youtube_url(video_id)

    with tempfile.TemporaryDirectory() as tmp_dir:
        
        tmp_filename = os.path.join(tmp_dir, f"{video_id}.%(ext)s")
        ydl_opts = build_yt_dlp_options(tmp_filename)

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)

        downloaded_path = _resolve_downloaded_filepath(info, video_id, tmp_dir)
        if not downloaded_path or not os.path.exists(downloaded_path):
            raise QuizlyValidationError("Audio download failed: output file not found.")

        final_path = _persist_file(downloaded_path)

    return DownloadResult(video_id=video_id, video_url=video_url, audio_path=final_path)

def _resolve_downloaded_filepath(info: dict, video_id: str, tmp_dir: str) -> str:
    """Resolve the final audio filepath created by yt-dlp."""
    
    filename = info.get("_filename") or info.get("requested_downloads", [{}])[0].get("filepath")
    if filename:
        return filename

    for name in os.listdir(tmp_dir):
        if name.startswith(video_id + "."):
            return os.path.join(tmp_dir, name)

    return ""

def _persist_file(src_path: str) -> str:
    """Move the downloaded file to a persistent temp file and return its path."""
    suffix = os.path.splitext(src_path)[1] or ".audio"
    fd, dst_path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)

    os.replace(src_path, dst_path)
    return dst_path