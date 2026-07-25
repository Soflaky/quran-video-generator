"""
Fetch Quran text, audio, and word-level timing data from Quran.com API.
Fallback to EveryAyah.com for audio downloads.
"""

import json
import logging
import requests
from dataclasses import dataclass, field
from pathlib import Path

from config import (
    QURAN_API_BASE, QURAN_AUDIO_CDN, EVERYAYAH_BASE,
    RECITERS, CACHE_DIR, SILENCE_BETWEEN_AYAHS_MS,
)

logger = logging.getLogger(__name__)


@dataclass
class WordSegment:
    word_index: int
    text: str
    start_ms: int
    end_ms: int


@dataclass
class AyahData:
    surah: int
    ayah: int
    text_uthmani: str
    words: list[str]
    audio_path: Path
    segments: list[WordSegment] = field(default_factory=list)


def _cache_path(name: str) -> Path:
    return CACHE_DIR / name


def _get_json(url: str, cache_name: str | None = None) -> dict:
    """GET JSON with optional disk cache."""
    if cache_name:
        cp = _cache_path(cache_name)
        if cp.exists():
            return json.loads(cp.read_text(encoding="utf-8"))

    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if cache_name:
        cp = _cache_path(cache_name)
        cp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    return data


def _download_file(url: str, dest: Path) -> Path:
    """Download a file if not already cached."""
    if dest.exists():
        logger.info(f"Using cached: {dest.name}")
        return dest
    logger.info(f"Downloading: {url}")
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return dest


def fetch_words(surah: int, ayah: int) -> tuple[str, list[str]]:
    """Fetch the Uthmani text and word list for an ayah."""
    cache_name = f"words_{surah}_{ayah}.json"
    url = f"{QURAN_API_BASE}/verses/by_key/{surah}:{ayah}?words=true&word_fields=text_uthmani&language=ar"
    data = _get_json(url, cache_name)

    verse = data["verse"]
    # Filter out "end" type words (ayah number markers)
    words = []
    for w in verse["words"]:
        if w.get("char_type_name") == "end":
            continue
        words.append(w["text_uthmani"])

    text_uthmani = verse.get("text_uthmani", " ".join(words))
    return text_uthmani, words


def fetch_audio_and_segments(surah: int, ayah: int, reciter_key: str) -> tuple[Path, list[list]]:
    """
    Fetch audio URL and word-level timing segments from Quran.com.
    Returns (audio_path, raw_segments) where raw_segments is list of [pos, next_pos, start_ms, end_ms].
    """
    reciter = RECITERS[reciter_key]
    reciter_id = reciter["id"]

    # Fetch recitation with segments — ?fields=segments is required to get timing data
    cache_name = f"recitation_{surah}_{ayah}_{reciter_key}_segments.json"
    url = f"{QURAN_API_BASE}/recitations/{reciter_id}/by_ayah/{surah}:{ayah}?fields=segments"
    data = _get_json(url, cache_name)

    # Response format: {"audio_files": [{"verse_key", "url", "segments"}], ...}
    audio_files = data.get("audio_files", [])
    if not audio_files:
        raise ValueError(f"No audio found for {surah}:{ayah} with reciter {reciter_key}")

    audio_info = audio_files[0]
    audio_url = audio_info.get("url", "")

    # Build full audio URL
    if audio_url.startswith("http"):
        full_url = audio_url
    else:
        full_url = f"{QURAN_AUDIO_CDN}/{audio_url}"

    # Download audio
    audio_dest = CACHE_DIR / "audio" / f"{reciter_key}_{surah:03d}{ayah:03d}.mp3"
    audio_path = _download_file(full_url, audio_dest)

    # Extract segments
    raw_segments = audio_info.get("segments", [])

    return audio_path, raw_segments


def fetch_audio_everyayah(surah: int, ayah: int, reciter_key: str) -> Path:
    """Fallback: download audio from EveryAyah.com."""
    reciter = RECITERS[reciter_key]
    folder = reciter["everyayah"]
    filename = f"{surah:03d}{ayah:03d}.mp3"
    url = f"{EVERYAYAH_BASE}/{folder}/{filename}"
    dest = CACHE_DIR / "audio" / f"{reciter_key}_{filename}"
    return _download_file(url, dest)


def fetch_ayah_data(surah: int, ayah: int, reciter_key: str) -> AyahData:
    """Fetch all data for a single ayah: text, words, audio, and timing."""
    logger.info(f"Fetching data for {surah}:{ayah} (reciter: {reciter_key})")

    # Get text and words
    text_uthmani, words = fetch_words(surah, ayah)

    # Get audio and segments
    try:
        audio_path, raw_segments = fetch_audio_and_segments(surah, ayah, reciter_key)
    except Exception as e:
        logger.warning(f"Quran.com audio failed: {e}. Falling back to EveryAyah.")
        audio_path = fetch_audio_everyayah(surah, ayah, reciter_key)
        raw_segments = []

    # Parse segments into WordSegment objects
    segments = []
    for seg in raw_segments:
        if len(seg) >= 4:
            pos, _next_pos, start_ms, end_ms = seg[0], seg[1], seg[2], seg[3]
            if pos < len(words):
                segments.append(WordSegment(
                    word_index=pos,
                    text=words[pos],
                    start_ms=start_ms,
                    end_ms=end_ms,
                ))

    return AyahData(
        surah=surah,
        ayah=ayah,
        text_uthmani=text_uthmani,
        words=words,
        audio_path=audio_path,
        segments=segments,
    )


def fetch_multiple_ayahs(surah: int, start: int, end: int, reciter_key: str) -> list[AyahData]:
    """Fetch data for a range of ayahs."""
    ayahs = []
    for ayah_num in range(start, end + 1):
        ayah_data = fetch_ayah_data(surah, ayah_num, reciter_key)
        ayahs.append(ayah_data)
    return ayahs
