"""
Word-level timing engine.

Tier 1: Quran.com segments (pre-computed, professional accuracy)
Tier 2: Even distribution fallback (audio_duration / word_count)
"""

import logging
from dataclasses import dataclass
from pydub import AudioSegment

from modules.quran_data import AyahData, WordSegment
from config import SILENCE_BETWEEN_AYAHS_MS

logger = logging.getLogger(__name__)


@dataclass
class TimedWord:
    """A word with absolute timing in the combined audio."""
    word_index: int       # Index within the full word list (across all ayahs)
    ayah_index: int       # Which ayah this word belongs to
    text: str
    start_ms: int         # Absolute start time in combined audio
    end_ms: int           # Absolute end time in combined audio


def get_audio_duration_ms(audio_path) -> int:
    """Get duration of an audio file in milliseconds."""
    audio = AudioSegment.from_file(str(audio_path))
    return len(audio)


def build_timed_words(ayahs: list[AyahData]) -> tuple[list[TimedWord], int]:
    """
    Build a flat list of TimedWords with absolute timestamps across all ayahs.
    Returns (timed_words, total_duration_ms).
    """
    timed_words = []
    cumulative_offset_ms = 0
    global_word_index = 0

    for ayah_idx, ayah in enumerate(ayahs):
        ayah_duration_ms = get_audio_duration_ms(ayah.audio_path)

        if ayah.segments:
            # Tier 1: Use Quran.com segments
            logger.info(f"Using Quran.com segments for {ayah.surah}:{ayah.ayah} ({len(ayah.segments)} segments)")
            for seg in ayah.segments:
                timed_words.append(TimedWord(
                    word_index=global_word_index,
                    ayah_index=ayah_idx,
                    text=seg.text,
                    start_ms=cumulative_offset_ms + seg.start_ms,
                    end_ms=cumulative_offset_ms + seg.end_ms,
                ))
                global_word_index += 1
        else:
            # Tier 2: Even distribution
            logger.info(f"Using even distribution for {ayah.surah}:{ayah.ayah} ({len(ayah.words)} words)")
            word_count = len(ayah.words)
            if word_count > 0:
                duration_per_word = ayah_duration_ms / word_count
                for i, word in enumerate(ayah.words):
                    timed_words.append(TimedWord(
                        word_index=global_word_index,
                        ayah_index=ayah_idx,
                        text=word,
                        start_ms=cumulative_offset_ms + int(i * duration_per_word),
                        end_ms=cumulative_offset_ms + int((i + 1) * duration_per_word),
                    ))
                    global_word_index += 1

        cumulative_offset_ms += ayah_duration_ms + SILENCE_BETWEEN_AYAHS_MS

    # Total duration = cumulative minus the trailing silence
    total_duration_ms = cumulative_offset_ms - SILENCE_BETWEEN_AYAHS_MS
    if not ayahs:
        total_duration_ms = 0

    return timed_words, total_duration_ms


def find_active_word(timed_words: list[TimedWord], current_ms: int) -> int | None:
    """Find the index (in timed_words list) of the currently spoken word."""
    for i, tw in enumerate(timed_words):
        if tw.start_ms <= current_ms <= tw.end_ms:
            return i
    return None
