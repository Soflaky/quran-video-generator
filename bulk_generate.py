#!/usr/bin/env python3
"""
Bulk Quran Video Generator

Generates 100 videos from surahs 2-60, ayahs 20-30, 2 ayahs per video.
Randomizes reciters and backgrounds for variety.

Usage:
    python bulk_generate.py
    python bulk_generate.py --count 50
    python bulk_generate.py --reciter alafasy
"""

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

from config import RECITERS, CACHE_DIR, OUTPUT_DIR, NATURE_QUERIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bulk_generate.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# Ayah counts per surah (surahs 2-60)
SURAH_AYAH_COUNTS = {
    2: 286, 3: 200, 4: 176, 5: 120, 6: 165, 7: 206, 8: 75, 9: 129, 10: 109,
    11: 123, 12: 111, 13: 43, 14: 52, 15: 99, 16: 128, 17: 111, 18: 110,
    19: 98, 20: 135, 21: 112, 22: 78, 23: 118, 24: 64, 25: 77, 26: 227,
    27: 93, 28: 88, 29: 69, 30: 60, 31: 34, 32: 30, 33: 73, 34: 54, 35: 45,
    36: 83, 37: 182, 38: 88, 39: 75, 40: 85, 41: 54, 42: 53, 43: 89, 44: 59,
    45: 37, 46: 35, 47: 38, 48: 29, 49: 18, 50: 45, 51: 60, 52: 49, 53: 62,
    54: 55, 55: 78, 56: 96, 57: 29, 58: 22, 59: 24, 60: 13,
}

SURAH_NAMES = {
    2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة", 6: "الأنعام",
    7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس", 11: "هود",
    12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر", 16: "النحل",
    17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه", 21: "الأنبياء",
    22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان", 26: "الشعراء",
    27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم", 31: "لقمان",
    32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر", 36: "يس",
    37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر", 41: "فصلت",
    42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية", 46: "الأحقاف",
    47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق", 51: "الذاريات",
    52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن", 56: "الواقعة",
    57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
}

RECITER_NAMES_AR = {
    "alafasy": "مشاري العفاسي",
    "abdulbasit": "عبدالباسط عبدالصمد",
    "abdulbasit_mujawwad": "عبدالباسط عبدالصمد (مجود)",
    "sudais": "عبدالرحمن السديس",
    "shatri": "أبو بكر الشاطري",
    "rifai": "هاني الرفاعي",
    "husary": "محمود خليل الحصري",
    "husary_muallim": "محمود خليل الحصري (معلم)",
    "minshawi": "محمد صديق المنشاوي",
    "minshawi_mujawwad": "محمد صديق المنشاوي (مجود)",
    "shuraym": "سعود الشريم",
    "tablawi": "محمد الطبلاوي",
}

# Track progress
PROGRESS_FILE = Path(__file__).parent / "bulk_progress.json"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    return {"completed": [], "failed": []}


def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def build_playlist(count: int, reciter: str | None = None) -> list[dict]:
    """Build a playlist of random surah/ayah combinations."""
    # Build all valid combinations: surah 2-60, start ayah 20-30, need start+1 to exist
    valid = []
    for surah in range(2, 61):
        total = SURAH_AYAH_COUNTS[surah]
        for start in range(20, 31):
            end = start + 1  # 2 ayahs per video
            if end <= total:
                valid.append({"surah": surah, "start": start, "end": end})

    random.shuffle(valid)

    # Pick the requested count
    if count > len(valid):
        logger.warning(f"Only {len(valid)} valid combinations available, using all of them")
        count = len(valid)

    playlist = valid[:count]

    # Assign reciters and backgrounds
    reciter_keys = list(RECITERS.keys())
    for item in playlist:
        item["reciter"] = reciter or random.choice(reciter_keys)
        item["background"] = random.choice(NATURE_QUERIES)

    return playlist


def generate_single(item: dict) -> dict:
    """Generate a single video. Returns result dict with status."""
    surah = item["surah"]
    start = item["start"]
    end = item["end"]
    reciter = item["reciter"]
    background = item["background"]
    surah_name = SURAH_NAMES.get(surah, str(surah))

    video_id = f"surah{surah}_{start}-{end}_{reciter}"
    output_filename = f"{video_id}.mp4"
    output_path = OUTPUT_DIR / output_filename

    # Skip if already generated
    if output_path.exists():
        logger.info(f"SKIP (exists): {output_filename}")
        return {"id": video_id, "status": "skipped", "path": str(output_path)}

    try:
        from modules.quran_data import fetch_multiple_ayahs
        from modules.word_timing import build_timed_words
        from modules.video_composer import concatenate_audio, compose_video
        from modules.background_video import download_background

        # Fetch data
        ayahs = fetch_multiple_ayahs(surah, start, end, reciter)

        # Build timing
        timed_words, total_duration_ms = build_timed_words(ayahs)

        # Concatenate audio
        audio_paths = [a.audio_path for a in ayahs]
        combined_audio_path = CACHE_DIR / f"combined_{surah}_{start}_{end}_{reciter}.mp3"
        concatenate_audio(audio_paths, combined_audio_path)

        # Download background
        background_path = download_background(background)

        # Surah info header
        surah_info = f"سورة {surah_name} — آيات {start}-{end}"

        # Compose video
        compose_video(
            background_path=background_path,
            combined_audio_path=combined_audio_path,
            timed_words=timed_words,
            ayahs=ayahs,
            total_duration_ms=total_duration_ms,
            surah_info=surah_info,
            output_filename=output_filename,
        )

        # Generate caption
        reciter_ar = RECITER_NAMES_AR.get(reciter, reciter)
        surah_hashtag = surah_name.replace(" ", "_")
        reciter_hashtag = reciter_ar.replace(" ", "_")
        caption = (
            f"سورة {surah_name} - اية {start} الى {end}\n"
            f"{reciter_ar}\n"
            f"#قران #قران_كريم #سورة_{surah_hashtag} #{reciter_hashtag} "
            f"#تلاوة #اسلام #quran #recitation #islam #tiktok"
        )
        caption_path = output_path.with_suffix(".txt")
        caption_path.write_text(caption, encoding="utf-8")

        return {"id": video_id, "status": "success", "path": str(output_path)}

    except Exception as e:
        logger.error(f"FAILED: {video_id} — {e}")
        return {"id": video_id, "status": "failed", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Bulk Quran Video Generator")
    parser.add_argument("--count", type=int, default=100, help="Number of videos to generate (default: 100)")
    parser.add_argument("--reciter", type=str, default=None, choices=list(RECITERS.keys()),
                        help="Force a specific reciter (default: random)")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("BULK QURAN VIDEO GENERATOR")
    logger.info(f"Target: {args.count} videos")
    logger.info(f"Surahs: 2-60 | Ayahs: 20-30 | 2 ayahs per video")
    logger.info(f"Reciter: {args.reciter or 'random'}")
    logger.info("=" * 60)

    # Build playlist
    playlist = build_playlist(args.count, args.reciter)
    logger.info(f"Playlist: {len(playlist)} videos to generate\n")

    # Load progress (for resuming)
    progress = load_progress()
    completed_ids = set(progress["completed"])

    success = 0
    failed = 0
    skipped = 0
    start_time = time.time()

    for i, item in enumerate(playlist):
        video_id = f"surah{item['surah']}_{item['start']}-{item['end']}_{item['reciter']}"

        # Skip already completed in previous runs
        if video_id in completed_ids:
            skipped += 1
            continue

        logger.info(f"\n[{i+1}/{len(playlist)}] Generating: Surah {item['surah']} "
                     f"Ayahs {item['start']}-{item['end']} ({item['reciter']})")

        result = generate_single(item)

        if result["status"] == "success":
            success += 1
            progress["completed"].append(video_id)
        elif result["status"] == "skipped":
            skipped += 1
            progress["completed"].append(video_id)
        else:
            failed += 1
            progress["failed"].append({"id": video_id, "error": result.get("error", "")})

        # Save progress after each video
        save_progress(progress)

        elapsed = time.time() - start_time
        done = success + failed + skipped
        if done > 0 and success > 0:
            avg_time = elapsed / (success + failed)
            remaining = avg_time * (len(playlist) - done)
            logger.info(f"  Progress: {done}/{len(playlist)} | "
                         f"Success: {success} | Failed: {failed} | Skipped: {skipped} | "
                         f"ETA: {remaining/60:.0f}min")

    elapsed_total = time.time() - start_time
    logger.info(f"\n{'=' * 60}")
    logger.info(f"BULK GENERATION COMPLETE")
    logger.info(f"Success: {success} | Failed: {failed} | Skipped: {skipped}")
    logger.info(f"Total time: {elapsed_total/60:.1f} minutes")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    main()
