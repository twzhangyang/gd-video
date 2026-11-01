# gd-video

Turns one Geometry Dash recording session into two videos:

- `horizontal.mp4`: the game at its native ratio with the facecam in a small top-right window, for YouTube
- `vertical-<langs>.mp4`: 1080×1920, facecam on top, game in the middle, burned-in subtitles, for 抖音, TikTok, Instagram Reels and YouTube Shorts. `<langs>` is the burned-in languages, e.g. `vertical-zh-en.mp4` (Chinese + English) or `vertical-en.mp4` (English only)

It lines up the two recordings (both start together by default, or by start times you give), transcribes the voice locally with Whisper, has Claude clean and translate the subtitles, and renders with FFmpeg.

## Requirements

- macOS on Apple Silicon (Whisper runs on MLX; encoding uses VideoToolbox)
- [Homebrew](https://brew.sh)
- Python 3.13 (`brew install python@3.13`)
- An Anthropic API key, for the subtitle cleanup step

## Setup

### 1. Install FFmpeg

```sh
brew install ffmpeg-full
```

`ffmpeg-full` includes libass, which is needed to burn in subtitles; the regular `ffmpeg` formula doesn't have it. It's keg-only, so it doesn't replace a regular `ffmpeg`. The script calls it at `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`.

### 2. Create the Python environment

```sh
cd ~/Documents/gd-video
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
```

### 3. Download the Whisper model (first run only)

The first `prep` downloads `mlx-community/whisper-large-v3-turbo` (~1.6 GB) into `~/.cache/huggingface`. To do it ahead of time:

```sh
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/whisper-large-v3-turbo')"
```

### 4. Add an Anthropic API key

The `clean` step calls Claude through the Anthropic API. Create a key at [platform.claude.com](https://platform.claude.com) (Settings → API keys), then add it to your shell profile:

```sh
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

## Cover assets

`gdvideo cover` uses files in `assets/`:

- `assets/logo.png`: the "GEOMETRY DASH" logo, made in Canva and downloaded as a PNG with a transparent background. Without it the cover is made without a logo
- `assets/fonts/PermanentMarker-Regular.ttf`: the brush font for the title (Google Fonts, Apache License 2.0)

The 🔥 comes from macOS's Apple Color Emoji. Positions and sizes per format are in `COVER_LAYOUT` in `config.py`; the emoji and tilt are `COVER_EMOJI` and `COVER_TILT`.

## Channel profile

`channel.md` holds the channel's name, voice, hashtags to always include and a YouTube description footer. `gdvideo post` follows it, so fill it in once.

## Subtitle glossary

`glossary.md` holds game terms, known Whisper mishearings (`wrong → right`), zh translations and the cleanup rules. Bullets under **Levels** and **Game terms** are passed to Whisper as a hint; the rest is used by the cleanup step. Add a line whenever a subtitle comes out wrong, and commit it.

## Common usage

Each week: put `ipad.mov` and `face.mov` in a new dated folder, then run these from the repo root. Set the folder once:

```sh
F=~/Downloads/GD/2026-11-03
```

**1. Prep:** transcribe the voice (about 30 s); add start times if the recordings didn't start together (see Step 1 below)

```sh
.venv/bin/gdvideo prep $F
```

**2. Clean:** Claude removes filler, fixes mishearings and adds Chinese (about 1 min). Check the lines it prints as unsure, and fix them in `$F/subs.json` if needed.

```sh
.venv/bin/gdvideo clean $F
```

**3. YouTube:** horizontal video without burned-in subtitles. Upload `export/en.srt` and `export/zh.srt` as captions on YouTube instead.

```sh
.venv/bin/gdvideo render $F --only horizontal
```

→ `export/horizontal.mp4`

**4. 抖音:** vertical video with Chinese and English burned in

```sh
.venv/bin/gdvideo render $F --only vertical --subs zh,en
```

→ `export/vertical-zh-en.mp4`

**5. TikTok and Instagram:** vertical video with English only burned in

```sh
.venv/bin/gdvideo render $F --only vertical --subs en
```

→ `export/vertical-en.mp4`

Each render takes about 1 minute. Steps 3–5 write separate files, so they can run in any order and never overwrite each other. After editing `subs.json`, rerun only the render steps.

**6. Posting text:** titles, descriptions, tags and hashtags for every platform (about 30 s)

```sh
.venv/bin/gdvideo post $F
```

→ `$F/post.md`, with a copy-paste block per platform: YouTube (title, description with chapter timestamps, tags), 抖音 (Chinese title and caption with hashtags), TikTok and Instagram (caption with hashtags). Add `--level "Name"` if the level isn't named in the commentary, or `--notes "first try at all 3 coins"` to steer it. `--force` writes a new one.

**7. Covers:** a cover for each format, with the logo, 🔥 and the title (a few seconds)

```sh
.venv/bin/gdvideo cover $F
```

→ `export/cover-horizontal.jpg` for YouTube (a frame of `horizontal.mp4`, so render it first) and `export/cover-vertical.jpg` for 抖音, TikTok and Instagram (the vertical layout without subtitles; logo and title stay inside the 3:4 area those apps show in profile grids). `--only horizontal` or `--only vertical` makes just one. The title defaults to the level name from step 6; use `--text "Electroman Adventures"` to set it yourself, and `--at 1:05` to pick the frame (default: 30% into the video). Rerun with a different `--at` until you like the frame.

**8. Pack for upload:** one folder per platform with everything that platform needs

```sh
.venv/bin/gdvideo pack $F --open
```

→ `export/pack/youtube/`, `douyin/`, `tiktok/`, `instagram/`, each with `video.mp4`, `cover.jpg` and `post.txt` (that platform's text from `post.md`: title, description and tags for YouTube, title and caption for 抖音, caption for TikTok and Instagram). YouTube also gets `captions-en.srt` and `captions-zh.srt`. Drag the files into each upload page or your scheduler. The 抖音 and TikTok videos start with the cover for 0.1 s (`COVER_INTRO`), since those apps pick the cover from a video frame: it's the default cover on 抖音, and on TikTok pick the first frame. That re-encodes those two videos once (about 45 s each, cached as `export/vertical-*-cover.mp4` and remade when the video or cover changes); the other videos are hard links, so they take no extra disk space. It reads `post.md`, so edit that file (not `post.txt`) and run `pack` again; the pack folder is rebuilt every time. Missing files are listed with the command that makes them. `--open` opens the folder in Finder.

## Usage

Put the two recordings in a dated folder with these names:

```
~/Downloads/GD/2026-11-03/
  ipad.mov   iPad screen recording (game audio only)
  face.mov   MacBook facecam (voice only)
```

The extension can be `.mov`, `.mp4` or `.m4v` in any letter case (`ipad.MP4` works too); keep only one file per name.

Then run everything with one command:

```sh
.venv/bin/gdvideo all ~/Downloads/GD/2026-11-03
```

It runs prep, clean and post (each skipped if its output already exists), renders `horizontal.mp4`, `vertical-zh-en.mp4` and `vertical-en.mp4`, makes the covers (skipped if they exist, so a frame you picked with `cover --at` is kept) and builds `export/pack/`. Running it again after changing a setting only re-renders and re-packs. `--force` redoes prep, clean, post and covers from scratch; `--subs en` (repeatable) renders only the vertical variants you name; `--test 20` renders clips and skips cover and pack. About 3 minutes. At the end of the clean step it prints the subtitle lines Claude was unsure about; fix them in `subs.json` and run `render` again.

The folder then looks like this. `work/` and `export/` can be deleted at any time; `subs.json` holds the cleaned subtitles, so keep it unless you want a fresh cleanup.

```
2026-11-03/
  ipad.mov, face.mov
  subs.json        cleaned zh/en subtitles (edit by hand if needed)
  post.md          titles, descriptions and hashtags for each platform
  work/            audio, raw transcript (subs.raw.json), review.txt
  export/          horizontal.mp4, vertical-zh-en.mp4, cover-horizontal.jpg, cover-vertical.jpg, *.srt
    pack/          one upload folder per platform (gdvideo pack)
```

### Step 1: `prep` (line up and transcribe)

```sh
.venv/bin/gdvideo prep ~/Downloads/GD/2026-11-03
```

Transcribes the voice with Whisper into `work/subs.raw.json`. Use `--lang zh` to force the speech language.

By default both recordings are taken to start at 0 s together. If they didn't, say where the video should begin in each one:

| Option | Meaning | Example |
|---|---|---|
| `--ipad-start S` | seconds into `ipad.mov` where the video begins | `--ipad-start 11`: cut 11 s of static iPad screen |
| `--face-start S` | seconds into `face.mov` that match that moment | `--face-start 1.09`: the facecam started 1.09 s earlier |
| `--auto-sync` | measure `--face-start` from the audio (the facecam mic hears the iPad speaker) | |

So "ipad 11 s = face 0 s" is `--ipad-start 11` (face start defaults to 0). `all` takes the same options. The values are saved in `subs.json` (`ipad_start`, `face_start`) and subtitle times count from the video start, so changing them means running prep and clean again: `gdvideo all <folder> --force --ipad-start 11`.

### Step 2: `clean` (clean and translate subtitles)

```sh
.venv/bin/gdvideo clean ~/Downloads/GD/2026-11-03
```

Sends the raw cues and `glossary.md` to Claude (`claude-opus-5-5` through the Anthropic API) and writes `subs.json` with cleaned English and Chinese text. It won't overwrite an existing `subs.json` unless you pass `--force`. Unsure lines are printed and saved to `work/review.txt`. A 3-minute video costs a few cents.

### Step 3: `render`

```sh
.venv/bin/gdvideo render ~/Downloads/GD/2026-11-03
```

| Option | Effect |
|---|---|
| `--subs zh,en` (default) / `en` / `zh` / `none` | Languages burned into the vertical video, which is saved as `vertical-<langs>.mp4` (e.g. `vertical-en.mp4`), so each version gets its own file. `none` gives a clean video for editing in 剪映 |
| `--only horizontal` / `--only vertical` | Render one format |
| `--burn-horizontal` | Also burn subtitles into the horizontal video |
| `--test 20` | Render only the first 20 s to `horizontal-test.mp4` / `vertical-<langs>-test.mp4` for a quick check; the full videos are left alone |

These options also work with `all`. Rendering both formats takes about 2 minutes for a 3-minute video on an M4 Pro.

## With Claude Code

Optional: the same flow is also the `gd-video` skill in this repo (`.claude/skills/gd-video/SKILL.md`). It works when Claude Code runs in this repo. To use it from any folder (e.g. the Obsidian vault), link it at user level once:

```sh
ln -s ~/Documents/gd-video/.claude/skills/gd-video ~/.claude/skills/gd-video
```

Then run:

```
/gd-video ~/Downloads/GD/2026-11-03
```

## Tuning

Layout, audio mix, models and subtitle splitting are constants in `src/gdvideo/config.py`: `PIP_WIDTH`, `PIP_TOP`, `GAME_VOLUME`, `VOICE_VOLUME`, `LOUDNESS`, `SUB_GAP`, `CLAUDE_MODEL` and more. The subtitle style is in `write_ass` in `src/gdvideo/subtitles.py`.

## Development

The code is a standard Python package in `src/gdvideo/`, installed in editable mode, so code changes take effect immediately:

| Module | What it does |
|---|---|
| `cli.py` | Command line (`gdvideo all/prep/clean/post/render/cover/pack`) |
| `config.py` | All tunable settings and paths |
| `transcribe.py` | `prep`: start times + Whisper → raw cues |
| `sync.py` | `--auto-sync`: audio offset between the two recordings |
| `clean.py` | `clean`: Claude API → `subs.json` |
| `post.py` | `post`: Claude API → `post.md` (titles, descriptions, hashtags) |
| `claude.py` | Shared Claude API call with structured output and error handling |
| `cover.py` | `cover`: horizontal and vertical covers with logo, emoji and title (Pillow) |
| `pack.py` | `pack`: per-platform upload folders from `export/` and `post.md`; cover intro for 抖音/TikTok |
| `subtitles.py` | SRT and ASS writers |
| `render.py` | `render`: both video layouts |
| `media.py` | ffmpeg / ffprobe helpers |

Run the tests with `.venv/bin/pytest`. They cover the pure functions (subtitle files, cue splitting, glossary parsing, sync, cue tidying, posting text, covers, packing) and need neither ffmpeg nor an API key.
