# Quran Video Generator

A small Python tool that generates vertical Quran recitation videos for TikTok/Reels/Shorts. Give it a surah and a range of ayahs, and it pulls the audio, syncs the Arabic text word by word, drops it over a nature background, and spits out a ready to post video with a caption.

## What it does

1. Fetches the ayah text and word timing data from the Quran.com API (falls back to EveryAyah.com if needed)
2. Downloads and stitches together the recitation audio for the range you picked
3. Grabs a background video from Pexels (nature, ocean, sky, whatever you search for)
4. Renders the Arabic text on screen, highlighting each word as it's recited
5. Generates a caption with hashtags so you can just copy and post

## Setup

```bash
pip install -r requirements.txt
```

You'll need a free Pexels API key for the background videos. Get one at https://www.pexels.com/api/ and put it in a `.env` file:

```
PEXELS_API_KEY=your_key_here
```

## Usage

```bash
python main.py --surah 2 --start 255 --end 257 --reciter alafasy
```

Other examples:

```bash
python main.py --surah 1 --start 1 --end 7 --reciter sudais --background "ocean waves"
python main.py --surah 36 --start 1 --end 3 --reciter abdulbasit
```

Arguments:

- `--surah` surah number, 1 to 114
- `--start` / `--end` ayah range
- `--reciter` which reciter to use (alafasy, sudais, husary, minshawi, and a few others, see `config.py` for the full list)
- `--background` search term for the background video, leave it out for a random nature clip
- `--output` custom filename, otherwise one is generated for you

The finished video and caption text file land in `output/`.

## Bulk generating

If you want a batch of videos instead of one at a time, use `bulk_generate.py`. It picks random surah and ayah combinations (surahs 2-60, two ayahs per video) and randomizes the reciter and background for each one.

```bash
python bulk_generate.py --count 50
python bulk_generate.py --count 20 --reciter alafasy
```

Leave out `--reciter` and it picks a random one for each video. It keeps track of what's already been generated in `bulk_progress.json`, so if you stop it or it crashes partway through, running it again picks up where it left off instead of starting over.

Every video gets its own caption file too, so you end up with a folder of videos ready to upload with captions already written for each one.

## Notes

- Audio and background clips get cached locally so you're not re-downloading the same files every run
- Recitation audio comes from public reciters via Quran.com and EveryAyah, and background footage comes from Pexels, so check their usage terms if you're planning to distribute videos at scale
