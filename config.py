import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = BASE_DIR / "output"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# API Keys
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")

# Video dimensions (TikTok 9:16)
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
FPS = 30

# Font
FONT_PATH = FONTS_DIR / "Amiri-Regular.ttf"
FONT_BOLD_PATH = FONTS_DIR / "Amiri-Bold.ttf"
FONT_SIZE = 64
LINE_SPACING = 40

# Text colors (RGB)
HIGHLIGHT_COLOR = (255, 215, 0)      # Gold for active word
NORMAL_COLOR = (255, 255, 255)       # White for inactive words
SHADOW_COLOR = (0, 0, 0)            # Black shadow
BG_OVERLAY_OPACITY = 0.45           # Dark overlay on background

# Text area
TEXT_PADDING = 60                    # Horizontal padding from edges
TEXT_Y_CENTER = TARGET_HEIGHT // 2   # Vertical center for text block
MAX_WORDS_ON_SCREEN = 5             # Maximum words displayed at once

# Audio
SILENCE_BETWEEN_AYAHS_MS = 150       # short breath-length pause between ayahs

# Quran.com API
QURAN_API_BASE = "https://api.quran.com/api/v4"
QURAN_AUDIO_CDN = "https://audio.qurancdn.com"

# EveryAyah fallback
EVERYAYAH_BASE = "https://everyayah.com/data"

# Reciter map: key -> {quran.com reciter_id, everyayah folder name, display name}
RECITERS = {
    "alafasy": {
        "id": 7,
        "name": "Mishari Rashid al-Afasy",
        "everyayah": "Alafasy_128kbps",
    },
    "abdulbasit": {
        "id": 2,
        "name": "AbdulBaset AbdulSamad (Murattal)",
        "everyayah": "Abdul_Basit_Murattal_192kbps",
    },
    "abdulbasit_mujawwad": {
        "id": 1,
        "name": "AbdulBaset AbdulSamad (Mujawwad)",
        "everyayah": "Abdul_Basit_Mujawwad_128kbps",
    },
    "sudais": {
        "id": 3,
        "name": "Abdur-Rahman as-Sudais",
        "everyayah": "Sudais_128kbps",
    },
    "shatri": {
        "id": 4,
        "name": "Abu Bakr al-Shatri",
        "everyayah": "Abu_Bakr_Ash-Shaatree_128kbps",
    },
    "rifai": {
        "id": 5,
        "name": "Hani ar-Rifai",
        "everyayah": "Hani_Rifai_192kbps",
    },
    "husary": {
        "id": 6,
        "name": "Mahmoud Khalil Al-Husary",
        "everyayah": "Husary_128kbps",
    },
    "husary_muallim": {
        "id": 12,
        "name": "Mahmoud Khalil Al-Husary (Muallim)",
        "everyayah": "Husary_Muallim_128kbps",
    },
    "minshawi": {
        "id": 9,
        "name": "Mohamed Siddiq al-Minshawi (Murattal)",
        "everyayah": "Minshawi_Murattal_128kbps",
    },
    "minshawi_mujawwad": {
        "id": 8,
        "name": "Mohamed Siddiq al-Minshawi (Mujawwad)",
        "everyayah": "Minshawi_Mujawwad_192kbps",
    },
    "shuraym": {
        "id": 10,
        "name": "Sa'ud ash-Shuraym",
        "everyayah": "Shuraym_128kbps",
    },
    "tablawi": {
        "id": 11,
        "name": "Mohamed al-Tablawi",
        "everyayah": "Tablawi_128kbps",
    },
}

# Pexels search queries for backgrounds
NATURE_QUERIES = [
    "nature landscape",
    "ocean waves",
    "mountains clouds",
    "night sky stars",
    "forest green",
    "waterfall",
    "clouds sky timelapse",
    "rain window",
    "sunset",
    "aurora borealis",
]
