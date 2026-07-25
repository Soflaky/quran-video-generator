#!/usr/bin/env python3
"""
Quran TikTok Video Generator

Generates vertical (9:16) videos with:
- Nature background (from Pexels API)
- Quran recitation audio (from Quran.com / EveryAyah.com)
- Word-by-word highlighted Arabic text overlay

Usage:
    python main.py --surah 2 --start 255 --end 257 --reciter alafasy
    python main.py --surah 1 --start 1 --end 7 --reciter sudais --background "ocean waves"
"""

import argparse
import logging
import sys

from config import RECITERS, CACHE_DIR, OUTPUT_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("quran_video.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Quran TikTok Video Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --surah 2 --start 255 --end 257 --reciter alafasy
  python main.py --surah 1 --start 1 --end 7 --reciter sudais --background "ocean waves"
  python main.py --surah 36 --start 1 --end 3 --reciter abdulbasit
        """,
    )
    parser.add_argument("--surah", type=int, required=True, help="Surah number (1-114)")
    parser.add_argument("--start", type=int, required=True, help="Starting ayah number")
    parser.add_argument("--end", type=int, required=True, help="Ending ayah number")
    parser.add_argument(
        "--reciter", type=str, default="alafasy",
        choices=list(RECITERS.keys()),
        help=f"Reciter key (default: alafasy). Options: {', '.join(RECITERS.keys())}",
    )
    parser.add_argument(
        "--background", type=str, default=None,
        help="Pexels search query for background (default: random nature)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output filename (default: auto-generated)",
    )
    args = parser.parse_args()

    # Validate
    if args.surah < 1 or args.surah > 114:
        parser.error("Surah must be between 1 and 114")
    if args.start < 1:
        parser.error("Start ayah must be >= 1")
    if args.end < args.start:
        parser.error("End ayah must be >= start ayah")

    reciter_name = RECITERS[args.reciter]["name"]
    logger.info(f"=== Quran Video Generator ===")
    logger.info(f"Surah {args.surah}, Ayahs {args.start}-{args.end}")
    logger.info(f"Reciter: {reciter_name}")

    # Step 1: Fetch Quran data
    logger.info("Step 1/5: Fetching Quran data...")
    from modules.quran_data import fetch_multiple_ayahs
    ayahs = fetch_multiple_ayahs(args.surah, args.start, args.end, args.reciter)

    for a in ayahs:
        logger.info(f"  {a.surah}:{a.ayah} — {len(a.words)} words, {len(a.segments)} segments")

    # Step 2: Build word timing
    logger.info("Step 2/5: Building word timing...")
    from modules.word_timing import build_timed_words
    timed_words, total_duration_ms = build_timed_words(ayahs)
    logger.info(f"  Total: {len(timed_words)} words, {total_duration_ms / 1000:.1f}s duration")

    # Step 3: Concatenate audio
    logger.info("Step 3/5: Concatenating audio...")
    from modules.video_composer import concatenate_audio
    audio_paths = [a.audio_path for a in ayahs]
    combined_audio_path = CACHE_DIR / f"combined_{args.surah}_{args.start}_{args.end}_{args.reciter}.mp3"
    concatenate_audio(audio_paths, combined_audio_path)

    # Step 4: Download background video
    logger.info("Step 4/5: Fetching background video...")
    from modules.background_video import download_background
    background_path = download_background(args.background)
    logger.info(f"  Background: {background_path.name}")

    # Step 5: Compose video
    logger.info("Step 5/5: Composing final video...")

    # Build surah info header
    surah_names = {
        1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
        6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
        11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
        16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
        21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
        26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
        31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
        36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
        41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
        46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
        51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
        56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
        61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
        66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
        71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
        76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
        81: "التكوير", 82: "الانفطار", 83: "المطففين", 84: "الانشقاق", 85: "البروج",
        86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
        91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
        96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
        101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
        106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
        111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس",
    }
    surah_name = surah_names.get(args.surah, f"سورة {args.surah}")
    if args.start == args.end:
        surah_info = f"سورة {surah_name} — آية {args.start}"
    else:
        surah_info = f"سورة {surah_name} — آيات {args.start}-{args.end}"

    output_filename = args.output or f"surah{args.surah}_{args.start}-{args.end}_{args.reciter}.mp4"

    from modules.video_composer import compose_video
    output_path = compose_video(
        background_path=background_path,
        combined_audio_path=combined_audio_path,
        timed_words=timed_words,
        ayahs=ayahs,
        total_duration_ms=total_duration_ms,
        surah_info=surah_info,
        output_filename=output_filename,
    )

    # Generate TikTok caption
    reciter_names_ar = {
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
    reciter_ar = reciter_names_ar.get(args.reciter, reciter_name)

    # Surah name for hashtag (remove ال prefix for cleaner tag)
    surah_hashtag = surah_name.replace(" ", "_")
    reciter_hashtag = reciter_ar.replace(" ", "_")

    if args.start == args.end:
        ayah_line = f"سورة {surah_name} - اية {args.start}"
    else:
        ayah_line = f"سورة {surah_name} - اية {args.start} الى {args.end}"

    caption = (
        f"{ayah_line}\n"
        f"{reciter_ar}\n"
        f"#قران #قران_كريم #سورة_{surah_hashtag} #{reciter_hashtag} "
        f"#تلاوة #اسلام #quran #recitation #islam #tiktok"
    )

    # Save caption to file next to the video
    caption_path = output_path.with_suffix(".txt")
    caption_path.write_text(caption, encoding="utf-8")

    logger.info(f"\n{'='*50}")
    logger.info(f"Video generated successfully!")
    logger.info(f"Output: {output_path}")
    logger.info(f"{'='*50}")
    print(f"\n📋 TikTok Caption:\n")
    print(caption)
    print(f"\n(Also saved to: {caption_path})")


if __name__ == "__main__":
    main()
