"""
Download and process nature background videos from Pexels API.
"""

import logging
import random
import requests
from pathlib import Path

from config import (
    PEXELS_API_KEY, CACHE_DIR, TARGET_WIDTH, TARGET_HEIGHT, NATURE_QUERIES,
)

logger = logging.getLogger(__name__)

BACKGROUNDS_DIR = CACHE_DIR / "backgrounds"
BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)


def search_pexels_videos(query: str, per_page: int = 10) -> list[dict]:
    """Search Pexels for portrait/vertical videos."""
    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": per_page,
        "orientation": "portrait",
    }

    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("videos", [])


def _pick_best_video_file(video: dict) -> dict | None:
    """Pick the best quality video file closest to 1080x1920."""
    files = video.get("video_files", [])
    if not files:
        return None

    # Prefer HD files, sort by height descending
    hd_files = [f for f in files if f.get("height", 0) >= 720]
    candidates = hd_files if hd_files else files

    # Sort by proximity to target resolution
    def score(f):
        h = f.get("height", 0)
        w = f.get("width", 0)
        return abs(h - TARGET_HEIGHT) + abs(w - TARGET_WIDTH)

    candidates.sort(key=score)
    return candidates[0]


def download_background(query: str | None = None) -> Path:
    """
    Search Pexels and download a random nature background video.
    Returns path to the downloaded video.
    """
    if not PEXELS_API_KEY or PEXELS_API_KEY == "your_pexels_api_key_here":
        raise ValueError(
            "Pexels API key not set. Get one free at https://www.pexels.com/api/ "
            "and add it to .env as PEXELS_API_KEY=..."
        )

    if query is None:
        query = random.choice(NATURE_QUERIES)

    logger.info(f"Searching Pexels for: '{query}'")
    videos = search_pexels_videos(query)

    if not videos:
        raise ValueError(f"No videos found on Pexels for query: '{query}'")

    # Pick a random video from results
    video = random.choice(videos)
    video_file = _pick_best_video_file(video)
    if not video_file:
        raise ValueError("Could not find a suitable video file")

    video_url = video_file["link"]
    video_id = video["id"]
    ext = video_file.get("file_type", "video/mp4").split("/")[-1]
    dest = BACKGROUNDS_DIR / f"pexels_{video_id}.{ext}"

    if dest.exists():
        logger.info(f"Using cached background: {dest.name}")
        return dest

    logger.info(f"Downloading background video ({video_file.get('width')}x{video_file.get('height')})")
    resp = requests.get(video_url, timeout=120, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"Saved background: {dest.name}")
    return dest


def resize_clip_to_target(clip, method="crop"):
    """
    Resize a MoviePy clip to 1080x1920 without distortion.
    method: "crop" (fill and crop excess) or "fit" (add black bars).
    """
    from moviepy.editor import ColorClip, CompositeVideoClip

    clip_aspect = clip.w / clip.h
    target_aspect = TARGET_WIDTH / TARGET_HEIGHT

    if method == "crop":
        if clip_aspect > target_aspect:
            resized = clip.resize(height=TARGET_HEIGHT)
            x_center = resized.w // 2
            x1 = x_center - (TARGET_WIDTH // 2)
            return resized.crop(x1=x1, x2=x1 + TARGET_WIDTH)
        else:
            resized = clip.resize(width=TARGET_WIDTH)
            y_center = resized.h // 2
            y1 = y_center - (TARGET_HEIGHT // 2)
            return resized.crop(y1=y1, y2=y1 + TARGET_HEIGHT)
    else:
        if clip_aspect > target_aspect:
            resized = clip.resize(width=TARGET_WIDTH)
        else:
            resized = clip.resize(height=TARGET_HEIGHT)
        bg = ColorClip(size=(TARGET_WIDTH, TARGET_HEIGHT), color=(0, 0, 0))
        bg = bg.set_duration(resized.duration)
        return CompositeVideoClip(
            [bg, resized.set_position("center")],
            size=(TARGET_WIDTH, TARGET_HEIGHT),
        )
