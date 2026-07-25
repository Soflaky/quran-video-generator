"""
Final video composition: background + dark overlay + text highlight clip + audio.
Renders one ayah at a time with word-by-word highlighting.
"""

import logging
import numpy as np
from pathlib import Path
from pydub import AudioSegment
from moviepy.editor import (
    VideoFileClip, AudioFileClip, CompositeVideoClip, ColorClip, VideoClip,
)

from config import (
    TARGET_WIDTH, TARGET_HEIGHT, FPS, BG_OVERLAY_OPACITY,
    OUTPUT_DIR, SILENCE_BETWEEN_AYAHS_MS,
)
from modules.background_video import resize_clip_to_target
from modules.text_renderer import prerender_ayah_states, get_chunk_and_local_index
from modules.word_timing import TimedWord, find_active_word
from modules.quran_data import AyahData

logger = logging.getLogger(__name__)


def concatenate_audio(ayah_audio_paths: list[Path], output_path: Path) -> Path:
    """
    Concatenate multiple ayah audio files with silence gaps between them.
    Returns path to the combined audio file.
    """
    combined = AudioSegment.empty()
    silence = AudioSegment.silent(duration=SILENCE_BETWEEN_AYAHS_MS)

    for i, audio_path in enumerate(ayah_audio_paths):
        segment = AudioSegment.from_file(str(audio_path))
        combined += segment
        if i < len(ayah_audio_paths) - 1:
            combined += silence

    combined.export(str(output_path), format="mp3", bitrate="320k")
    logger.info(f"Combined audio: {output_path.name} ({len(combined)}ms)")
    return output_path


def compose_video(
    background_path: Path,
    combined_audio_path: Path,
    timed_words: list[TimedWord],
    ayahs: list[AyahData],
    total_duration_ms: int,
    surah_info: str,
    output_filename: str,
) -> Path:
    """
    Compose the final TikTok video.
    Shows one ayah at a time with word-by-word RTL highlighting.
    """
    total_duration_s = total_duration_ms / 1000.0
    output_path = OUTPUT_DIR / output_filename

    # 1. Load background
    logger.info("Loading background video...")
    bg_clip = VideoFileClip(str(background_path))
    bg_clip = resize_clip_to_target(bg_clip, method="crop")

    # 2. Loop if needed
    if bg_clip.duration < total_duration_s:
        bg_clip = bg_clip.loop(duration=total_duration_s)
    else:
        bg_clip = bg_clip.subclip(0, total_duration_s)

    # 3. Dark overlay for text readability
    overlay = ColorClip(
        size=(TARGET_WIDTH, TARGET_HEIGHT),
        color=(0, 0, 0),
    ).set_opacity(BG_OVERLAY_OPACITY).set_duration(total_duration_s)

    # 4. Pre-render text frames PER AYAH (chunked into groups of max words)
    logger.info("Pre-rendering text frames per ayah (chunked)...")
    # ayah_chunks[ayah_idx] = {chunk_idx: [no_highlight, word0, word1, ...]}
    ayah_chunks_rgba = {}
    for ayah_idx, ayah in enumerate(ayahs):
        logger.info(f"  Pre-rendering ayah {ayah.surah}:{ayah.ayah} ({len(ayah.words)} words)...")
        ayah_chunks_rgba[ayah_idx] = prerender_ayah_states(ayah.words, surah_info)

    # Also create a blank frame for silence between ayahs
    blank_frame = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 4), dtype=np.uint8)

    # Split all frames into RGB + alpha
    ayah_chunks_rgb = {}
    ayah_chunks_alpha = {}
    for ayah_idx, chunks in ayah_chunks_rgba.items():
        ayah_chunks_rgb[ayah_idx] = {}
        ayah_chunks_alpha[ayah_idx] = {}
        for chunk_idx, frames in chunks.items():
            ayah_chunks_rgb[ayah_idx][chunk_idx] = [f[:, :, :3] for f in frames]
            ayah_chunks_alpha[ayah_idx][chunk_idx] = [f[:, :, 3].astype(np.float64) / 255.0 for f in frames]

    blank_rgb = blank_frame[:, :, :3]
    blank_alpha = blank_frame[:, :, 3].astype(np.float64) / 255.0

    # Build a mapping from each timed_word to its local index within its ayah
    word_local_indices = []
    ayah_word_counters = {}
    for tw in timed_words:
        if tw.ayah_index not in ayah_word_counters:
            ayah_word_counters[tw.ayah_index] = 0
        local_idx = ayah_word_counters[tw.ayah_index]
        word_local_indices.append(local_idx)
        ayah_word_counters[tw.ayah_index] = local_idx + 1

    def _select_frame(t):
        """Returns (ayah_idx, chunk_idx, frame_index_in_chunk) or None for blank."""
        current_ms = t * 1000
        active_idx = find_active_word(timed_words, current_ms)
        if active_idx is not None:
            tw = timed_words[active_idx]
            local_idx = word_local_indices[active_idx]
            chunk_idx, idx_in_chunk = get_chunk_and_local_index(local_idx)
            return (tw.ayah_index, chunk_idx, idx_in_chunk + 1)  # +1 because 0 = no highlight

        # Between ayahs or before/after — show nearest ayah's first chunk with no highlight
        for i, tw in enumerate(timed_words):
            if tw.start_ms > current_ms:
                local_idx = word_local_indices[i]
                chunk_idx, _ = get_chunk_and_local_index(local_idx)
                return (tw.ayah_index, chunk_idx, 0)
        if timed_words:
            local_idx = word_local_indices[-1]
            chunk_idx, _ = get_chunk_and_local_index(local_idx)
            return (timed_words[-1].ayah_index, chunk_idx, 0)
        return None

    def make_text_frame(t):
        result = _select_frame(t)
        if result is None:
            return blank_rgb
        ayah_idx, chunk_idx, frame_idx = result
        return ayah_chunks_rgb[ayah_idx][chunk_idx][frame_idx]

    def make_mask_frame(t):
        result = _select_frame(t)
        if result is None:
            return blank_alpha
        ayah_idx, chunk_idx, frame_idx = result
        return ayah_chunks_alpha[ayah_idx][chunk_idx][frame_idx]

    text_clip = VideoClip(make_text_frame, duration=total_duration_s)
    mask_clip = VideoClip(make_mask_frame, ismask=True, duration=total_duration_s)
    text_clip = text_clip.set_mask(mask_clip).set_position((0, 0))

    # 5. Composite everything
    logger.info("Compositing video layers...")
    final = CompositeVideoClip(
        [bg_clip, overlay, text_clip],
        size=(TARGET_WIDTH, TARGET_HEIGHT),
    )

    # 6. Add audio
    audio_clip = AudioFileClip(str(combined_audio_path))
    final = final.set_audio(audio_clip)
    final = final.set_duration(total_duration_s)

    # 7. Write output
    logger.info(f"Writing final video: {output_path}")
    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="320k",
        fps=FPS,
        threads=4,
        preset="fast",
        ffmpeg_params=[
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ],
    )

    # Cleanup
    bg_clip.close()
    audio_clip.close()
    final.close()

    logger.info(f"Video saved: {output_path}")
    return output_path
