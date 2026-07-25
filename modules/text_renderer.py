"""
Arabic text rendering with word-by-word highlighting.

Uses Pillow + arabic-reshaper + python-bidi for proper Arabic glyph shaping.
Pre-renders all highlight states per ayah for performance.
"""

import logging
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

from config import (
    TARGET_WIDTH, TARGET_HEIGHT, FONT_PATH, FONT_BOLD_PATH, FONT_SIZE,
    HIGHLIGHT_COLOR, NORMAL_COLOR, SHADOW_COLOR, TEXT_PADDING, LINE_SPACING,
    MAX_WORDS_ON_SCREEN,
)

logger = logging.getLogger(__name__)


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD_PATH if bold and FONT_BOLD_PATH.exists() else FONT_PATH
    return ImageFont.truetype(str(path), size)


_reshaper = arabic_reshaper.ArabicReshaper(configuration={
    "delete_harakat": False,
    "delete_tatweel": False,
})


def prepare_arabic(text: str) -> str:
    """Reshape and apply BiDi algorithm to Arabic text."""
    reshaped = _reshaper.reshape(text)
    return get_display(reshaped)


def _measure_word(font: ImageFont.FreeTypeFont, word: str) -> int:
    """Get the pixel width of a rendered word."""
    bbox = font.getbbox(word)
    return bbox[2] - bbox[0]


def _build_lines(words: list[str], font: ImageFont.FreeTypeFont, max_width: int) -> list[list[int]]:
    """
    Break words into lines that fit within max_width.
    Returns list of lines, each line is a list of word indices.
    Words are stored in logical order (first word = rightmost visually in RTL).
    """
    lines = []
    current_line = []
    current_width = 0
    space_width = _measure_word(font, " ")

    for i, word in enumerate(words):
        display_word = prepare_arabic(word)
        w = _measure_word(font, display_word)

        needed = w + (space_width if current_line else 0)
        if current_width + needed > max_width and current_line:
            lines.append(current_line)
            current_line = [i]
            current_width = w
        else:
            current_line.append(i)
            current_width += needed

    if current_line:
        lines.append(current_line)

    return lines


def render_ayah_frame(
    words: list[str],
    highlighted_local_index: int | None,
    surah_info: str = "",
) -> np.ndarray:
    """
    Render a single ayah's text with one highlighted word.
    Words are drawn RIGHT-TO-LEFT (proper Arabic layout).

    Args:
        words: list of Arabic words for THIS ayah only
        highlighted_local_index: index within this ayah's words to highlight (None = no highlight)
        surah_info: optional header text

    Returns:
        numpy array (H, W, 4) RGBA image
    """
    img = Image.new("RGBA", (TARGET_WIDTH, TARGET_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(FONT_SIZE)
    header_font = _load_font(36)

    max_text_width = TARGET_WIDTH - 2 * TEXT_PADDING
    space_width = _measure_word(font, " ")

    # Build line layout
    lines = _build_lines(words, font, max_text_width)

    # Calculate total text block height
    line_height = FONT_SIZE + LINE_SPACING
    total_text_height = len(lines) * line_height - LINE_SPACING

    # Starting Y position (centered vertically)
    start_y = (TARGET_HEIGHT - total_text_height) // 2

    # Draw header if provided
    if surah_info:
        header_display = prepare_arabic(surah_info)
        header_w = _measure_word(header_font, header_display)
        header_x = (TARGET_WIDTH - header_w) // 2
        header_y = start_y - 80
        # Shadow
        draw.text((header_x + 2, header_y + 2), header_display, font=header_font, fill=SHADOW_COLOR + (180,))
        draw.text((header_x, header_y), header_display, font=header_font, fill=(200, 200, 200, 255))

    # Draw each line of words — RTL (right to left)
    for line_idx, word_indices in enumerate(lines):
        y = start_y + line_idx * line_height

        # Prepare display words and measure widths
        line_words_display = []
        line_widths = []
        for wi in word_indices:
            dw = prepare_arabic(words[wi])
            line_words_display.append(dw)
            line_widths.append(_measure_word(font, dw))

        total_line_width = sum(line_widths) + space_width * (len(word_indices) - 1)

        # RTL: start from the RIGHT edge of the centered text block
        x_right = (TARGET_WIDTH + total_line_width) // 2

        for j, wi in enumerate(word_indices):
            display_word = line_words_display[j]
            w = line_widths[j]

            # Move x left by word width to get the drawing position
            x = x_right - w

            is_highlighted = (highlighted_local_index is not None and wi == highlighted_local_index)
            color = HIGHLIGHT_COLOR + (255,) if is_highlighted else NORMAL_COLOR + (255,)

            # Draw shadow
            draw.text((x + 2, y + 2), display_word, font=font, fill=SHADOW_COLOR + (160,))
            # Draw word
            draw.text((x, y), display_word, font=font, fill=color)

            # Move x_right left past this word + space
            x_right -= w + space_width

    return np.array(img)


def prerender_ayah_states(
    words: list[str],
    surah_info: str = "",
) -> dict[int, list[np.ndarray]]:
    """
    Pre-render frames for a single ayah, chunked into groups of MAX_WORDS_ON_SCREEN.

    Returns dict: {chunk_idx: [no_highlight_frame, word0_frame, word1_frame, ...]}
    Each chunk contains at most MAX_WORDS_ON_SCREEN words.
    """
    # Split words into chunks
    chunks = []
    for i in range(0, len(words), MAX_WORDS_ON_SCREEN):
        chunks.append(words[i:i + MAX_WORDS_ON_SCREEN])

    result = {}
    for chunk_idx, chunk_words in enumerate(chunks):
        logger.info(f"  Chunk {chunk_idx}: {len(chunk_words)} words")
        frames = []
        # No highlight state
        frames.append(render_ayah_frame(chunk_words, None, surah_info))
        # Each word highlighted
        for i in range(len(chunk_words)):
            frames.append(render_ayah_frame(chunk_words, i, surah_info))
        result[chunk_idx] = frames

    return result


def get_chunk_and_local_index(word_local_index: int) -> tuple[int, int]:
    """Given a word's index within an ayah, return (chunk_idx, index_within_chunk)."""
    chunk_idx = word_local_index // MAX_WORDS_ON_SCREEN
    local_idx = word_local_index % MAX_WORDS_ON_SCREEN
    return chunk_idx, local_idx
