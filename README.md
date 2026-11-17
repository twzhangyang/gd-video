# gd-video

Turns one Geometry Dash recording session into uploads for YouTube, TikTok and 抖音. OBS records the session twice at the same time, both with the game and the facecam:

- the **horizontal** recording (main OBS canvas) → **YouTube** as it is, with English and Chinese caption files
- the **vertical** recording (1080×1920, [Aitum Vertical](https://aitum.tv) canvas) → **TikTok** with English subtitles burned in, and **抖音** with Chinese + English burned in

It transcribes the voice locally with Whisper, has Claude clean and translate the subtitles and write the titles, descriptions and tags, makes a cover for each format, and renders with FFmpeg.

## Requirements

- macOS on Apple Silicon (Whisper runs on MLX; encoding uses VideoToolbox)
- [Homebrew](https://brew.sh)
- Python 3.13 (`brew install python@3.13`)
- An Anthropic API key, for the subtitle cleanup and posting text steps

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

The `clean` and `post` steps call Claude through the Anthropic API. Create a key at [platform.claude.com](https://platform.claude.com) (Settings → API keys), then add it to your shell profile:

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

## Usage

Put the two recordings in a dated folder, straight from OBS:

```
~/Downloads/GD/2026-11-17/
  2026-11-17 21-07-00.mov            horizontal recording
  2026-11-17 21-07-02-vertical.mov   vertical recording (Aitum Vertical adds "-vertical")
```

The vertical one is the video with "vertical" in its name; the horizontal one is the other video (`horizontal.mp4` + `vertical.mp4` works too). `.mov`, `.mp4` or `.m4v`, any letter case. Then run everything with one command from the repo root:

```sh
.venv/bin/gdvideo all ~/Downloads/GD/2026-11-17
.venv/bin/gdvideo all ~/Downloads/GD/2026-11-17 --test 20    # 20 s test clips, no pack
```

It runs prep, clean, post and cover (each skipped if its output already exists, so hand edits and a cover frame you picked are kept), renders the TikTok and 抖音 videos and builds `export/pack/`. Running it again after changing a setting only re-renders and re-packs. `--force` redoes prep, clean, post and the covers. At the end of the clean step it prints the subtitle lines Claude was unsure about; fix them in `subs.json` and run `render` and `pack` again. A 4-minute session takes about 3 minutes.

What you get:

| | YouTube | TikTok | 抖音 |
|---|---|---|---|
| Video | the horizontal recording, untouched | `export/tiktok.mp4` | `export/douyin.mp4` |
| Subtitles | upload `en.srt` and `zh.srt` as captions | English burned in at the bottom | Chinese + English burned in at the bottom |
| Cover | `cover-horizontal.jpg`, uploaded as the thumbnail | `cover-vertical.jpg`, also the first 0.1 s of the video | same as TikTok |
| Text (`post.md`) | title, description with chapters, tags | caption with hashtags | title, caption with hashtags |

The folder then looks like this. `work/` and `export/` can be deleted at any time; `subs.json` and `post.md` hold the cleaned subtitles and the posting text, so keep them unless you want fresh ones.

```
2026-11-17/
  <the two recordings>
  subs.json        cleaned zh/en subtitles and the vertical offset (edit by hand if needed)
  post.md          titles, descriptions and hashtags for each platform (edit by hand if needed)
  work/            audio, raw transcript (subs.raw.json), review.txt, cover frames
  export/          tiktok.mp4, douyin.mp4, cover-horizontal.jpg, cover-vertical.jpg, en/zh/bilingual.srt
    pack/          one upload folder per platform
```

### The steps one by one

`all` runs these in order; each can also be run on its own. Set the folder once: `F=~/Downloads/GD/2026-11-17`.

**1. `prep`: line up and transcribe** (about 30 s)

```sh
.venv/bin/gdvideo prep $F
```

Transcribes the horizontal recording with Whisper into `work/subs.raw.json`. If it has several audio tracks, the last one is used (record the mic alone on the last track for cleaner subtitles). Use `--lang zh` to force the speech language.

The two recordings rarely start at exactly the same moment, so `prep` also measures how far apart they are: both carry the same audio, so it matches them in 30 s windows and takes the value the windows agree on (`vertical_start` in `subs.json`: seconds into the vertical recording when the horizontal one starts; negative when the vertical one started later). Subtitle times are on the horizontal recording's timeline and are shifted by that much for the vertical videos. If it reports "unreliable", set it by hand: `--vertical-start -1.6` (`all` takes it too).

**2. `clean`: clean and translate the subtitles** (about 1 min)

```sh
.venv/bin/gdvideo clean $F
```

Sends the raw cues and `glossary.md` to Claude (`claude-opus-5-5` through the Anthropic API) and writes `subs.json` with cleaned English and Chinese text. It won't overwrite an existing `subs.json` unless you pass `--force`. Unsure lines are printed and saved to `work/review.txt`. A few cents per video.

**3. `post`: posting text** (about 30 s)

```sh
.venv/bin/gdvideo post $F
```

→ `$F/post.md`, with a copy-paste block per platform: YouTube (title, description with chapter timestamps, tags), 抖音 (Chinese title, caption with hashtags) and TikTok (caption with hashtags). Add `--level "Name"` if the level isn't named in the commentary, or `--notes "first try at all 3 coins"` to steer it. `--force` writes a new one.

**4. `cover`: covers** (a few seconds)

```sh
.venv/bin/gdvideo cover $F
```

→ `export/cover-horizontal.jpg` (a frame of the horizontal recording) and `export/cover-vertical.jpg` (the same moment in the vertical recording), each with the logo, 🔥 and the title. On the vertical cover the logo and title sit over the game and inside the 3:4 area the apps show in profile grids. The title defaults to the level name from `post`; `--text "Clubstep Monster"` sets it, `--at 1:05` picks the moment (default: 30% into the video), `--only horizontal|vertical` makes one. The TikTok and 抖音 videos start with the vertical cover, so after a new cover run `render` and `pack` again.

**5. `render`: the TikTok and 抖音 videos** (about 1 min each for 4 minutes)

```sh
.venv/bin/gdvideo render $F
```

→ `export/tiktok.mp4` and `export/douyin.mp4`: the vertical cover for 0.1 s (`COVER_INTRO`, so it can be picked as the cover in the app), then the vertical recording with the subtitles burned in and its loudness set to −14 LUFS. Also writes `en.srt`, `zh.srt` and `bilingual.srt` on the horizontal recording's timeline (for YouTube; `bilingual.srt` is for 剪映). `--only tiktok|douyin` renders one; `--test 20` renders the first 20 s to `<platform>-test.mp4` and leaves the full videos alone.

**6. `pack`: upload folders**

```sh
.venv/bin/gdvideo pack $F --open
```

→ `export/pack/youtube/` (the horizontal recording as `video.mov`, `cover.jpg`, `captions-en.srt`, `captions-zh.srt`), `douyin/` and `tiktok/` (`video.mp4`, `cover.jpg`), each with `post.txt` (that platform's text from `post.md`). Files are hard links, so they take no extra disk space. It reads `post.md`, so edit that file (not `post.txt`) and run `pack` again; the pack folder is rebuilt every time. Missing files are listed with the command that makes them. `--open` opens the folder in Finder.

## With Claude Code

Optional: the same flow is also the `gd-video` skill in this repo (`.claude/skills/gd-video/SKILL.md`). It works when Claude Code runs in this repo. To use it from any folder (e.g. the Obsidian vault), link it at user level once:

```sh
ln -s ~/Documents/gd-video/.claude/skills/gd-video ~/.claude/skills/gd-video
```

Then run:

```
/gd-video ~/Downloads/GD/2026-11-17
```

## Tuning

Constants in `src/gdvideo/config.py`:

- Subtitles: `VERTICAL_SUB_BOTTOM` (抖音) and `VERTICAL_SUB_BOTTOM_EN` (TikTok) are the px from the bottom edge of the 1080×1920 frame to the bottom of the subtitles; `SUB_ZH_SIZE` and `SUB_EN_SIZE` are the font sizes. They are set for the current Aitum layout (facecam y 0–810, game 810–1506, black below), so the subtitles sit in the black band under the game, above the apps' own caption and buttons. Change them if the OBS layout changes
- Covers: `COVER_LAYOUT` (positions per format), `COVER_EMOJI`, `COVER_TILT`, `COVER_AT`
- Audio: `LOUDNESS`, `TRUE_PEAK`; video: `VERTICAL_BITRATE`
- `CLAUDE_MODEL`, `WHISPER_MODEL` and the cue splitting (`MAX_CHARS`, `MAX_DURATION`, `PAUSE_SPLIT`)

The subtitle style is in `write_ass` in `src/gdvideo/subtitles.py`.

## Development

The code is a standard Python package in `src/gdvideo/`, installed in editable mode, so code changes take effect immediately:

| Module | What it does |
|---|---|
| `cli.py` | Command line (`gdvideo all/prep/clean/post/cover/render/pack`) |
| `config.py` | All tunable settings and paths |
| `transcribe.py` | `prep`: vertical offset + Whisper → raw cues |
| `sync.py` | Audio offset between the two recordings |
| `clean.py` | `clean`: Claude API → `subs.json` |
| `post.py` | `post`: Claude API → `post.md` (titles, descriptions, hashtags) |
| `claude.py` | Shared Claude API call with structured output and error handling |
| `cover.py` | `cover`: horizontal and vertical covers with logo, emoji and title (Pillow) |
| `render.py` | `render`: TikTok and 抖音 videos (cover intro + burned subtitles) and the SRT files |
| `pack.py` | `pack`: per-platform upload folders from the recordings, `export/` and `post.md` |
| `subtitles.py` | SRT and ASS writers |
| `media.py` | Finding the recordings, ffmpeg / ffprobe helpers |

Run the tests with `.venv/bin/pytest`. They cover the pure functions (finding the recordings, subtitle files, cue splitting, glossary parsing, sync, cue tidying, posting text, covers, packing) and need neither ffmpeg nor an API key.
