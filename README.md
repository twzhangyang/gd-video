# gd-video

Turns one Geometry Dash recording session into two videos:

- `horizontal.mp4`: the game at its native ratio with the facecam in a small top-right window, for YouTube
- `vertical-<langs>.mp4`: 1080×1920, facecam on top, game in the middle, burned-in subtitles, for 抖音, TikTok, Instagram Reels and YouTube Shorts. `<langs>` is the burned-in languages, e.g. `vertical-zh-en.mp4` (Chinese + English) or `vertical-en.mp4` (English only)

It syncs the two recordings automatically, transcribes the voice locally with Whisper, has Claude clean and translate the subtitles, and renders with FFmpeg.

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

## Channel profile

`channel.md` holds the channel's name, voice, hashtags to always include and a YouTube description footer. `gdvideo post` follows it, so fill it in once.

## Subtitle glossary

`glossary.md` holds game terms, known Whisper mishearings (`wrong → right`), zh translations and the cleanup rules. Bullets under **Levels** and **Game terms** are passed to Whisper as a hint; the rest is used by the cleanup step. Add a line whenever a subtitle comes out wrong, and commit it.

## Common usage

Each week: put `ipad.mov` and `face.mov` in a new dated folder, then run these from the repo root. Set the folder once:

```sh
F=~/Downloads/GD/2026-11-03
```

**1. Prep:** sync the recordings and transcribe the voice (about 30 s)

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

## Usage

Put the two recordings in a dated folder with these names:

```
~/Downloads/GD/2026-11-03/
  ipad.mov   iPad screen recording (game audio only)
  face.mov   MacBook facecam (voice only)
```

Then run everything with one command:

```sh
.venv/bin/gdvideo all ~/Downloads/GD/2026-11-03
```

It runs the three steps below, skipping any step whose output already exists, so running it again after changing a setting only re-renders. `--force` redoes prep and clean from scratch. At the end of the clean step it prints the subtitle lines Claude was unsure about; fix them in `subs.json` and run `render` again.

The folder then looks like this. `work/` and `export/` can be deleted at any time; `subs.json` holds the cleaned subtitles, so keep it unless you want a fresh cleanup.

```
2026-11-03/
  ipad.mov, face.mov
  subs.json        cleaned zh/en subtitles (edit by hand if needed)
  post.md          titles, descriptions and hashtags for each platform
  work/            audio, raw transcript (subs.raw.json), review.txt
  export/          horizontal.mp4, vertical-zh-en.mp4, en.srt, zh.srt, bilingual.srt
```

### Step 1: `prep` (sync and transcribe)

```sh
.venv/bin/gdvideo prep ~/Downloads/GD/2026-11-03
```

Finds the sync offset and transcribes the voice with Whisper into `work/subs.raw.json`. If sync fails, pass the offset by hand: `--offset 1.09` (seconds into `face.mov` that match `ipad.mov` t=0). Use `--lang zh` to force the speech language.

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
| `cli.py` | Command line (`gdvideo all/prep/clean/render`) |
| `config.py` | All tunable settings and paths |
| `transcribe.py` | `prep`: sync + Whisper → raw cues |
| `sync.py` | Audio offset between the two recordings |
| `clean.py` | `clean`: Claude API → `subs.json` |
| `post.py` | `post`: Claude API → `post.md` (titles, descriptions, hashtags) |
| `claude.py` | Shared Claude API call with structured output and error handling |
| `subtitles.py` | SRT and ASS writers |
| `render.py` | `render`: both video layouts |
| `media.py` | ffmpeg / ffprobe helpers |

Run the tests with `.venv/bin/pytest`. They cover the pure functions (subtitle files, cue splitting, glossary parsing, sync, cue tidying) and need neither ffmpeg nor an API key.
