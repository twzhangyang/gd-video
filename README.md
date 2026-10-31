# gd-video

Turns one Geometry Dash recording session into two videos:

- `horizontal.mp4`: the game at its native ratio with the facecam in a small top-right window, for YouTube
- `vertical.mp4`: 1080×1920, facecam on top, game in the middle, burned-in Chinese/English subtitles, for TikTok, Douyin, Instagram Reels and YouTube Shorts

It syncs the two recordings automatically, transcribes the voice locally with Whisper, and renders with FFmpeg.

## Requirements

- macOS on Apple Silicon (Whisper runs on MLX; encoding uses VideoToolbox)
- [Homebrew](https://brew.sh)
- Python 3.13 (`brew install python@3.13`)

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
.venv/bin/pip install -r requirements.txt
```

### 3. Download the Whisper model (first run only)

The first `prep` downloads `mlx-community/whisper-large-v3-turbo` (~1.6 GB) into `~/.cache/huggingface`. To do it ahead of time:

```sh
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/whisper-large-v3-turbo')"
```

## Subtitle glossary

`glossary.md` holds game terms, known Whisper mishearings (`wrong → right`), zh translations and the cleanup rules. Bullets under **Levels** and **Game terms** are passed to Whisper as a hint; the rest is used by the cleanup step. Add a line whenever a subtitle comes out wrong, and commit it.

## Usage

Put the two recordings in a dated folder with these names:

```
~/Downloads/GD/2026-11-03/
  ipad.mov   iPad screen recording (game audio only)
  face.mov   MacBook facecam (voice only)
```

### Step 1: sync and transcribe

```sh
.venv/bin/python gdvideo.py prep ~/Downloads/GD/2026-11-03
```

Writes `work/subs.json` with the sync offset and raw subtitle cues (`src` text). If sync fails, pass the offset by hand: `--offset 1.09` (seconds into `face.mov` that match `ipad.mov` t=0). Use `--lang zh` to force the speech language.

### Step 2: clean and translate the subtitles

Fill in `en` and `zh` for each cue in `work/subs.json`: remove filler, fix terms, translate. In practice Claude Code does this with the `gd-video` skill (see below).

### Step 3: render

```sh
.venv/bin/python gdvideo.py render ~/Downloads/GD/2026-11-03
```

| Option | Effect |
|---|---|
| `--subs zh,en` (default) / `en` / `zh` / `none` | Languages burned into the vertical video. `none` gives a clean video for editing in 剪映 |
| `--only horizontal` / `--only vertical` | Render one format |
| `--burn-horizontal` | Also burn subtitles into the horizontal video |
| `--test 20` | Render only the first 20 s for a quick check |

Outputs go to `export/`: `horizontal.mp4`, `vertical.mp4`, `en.srt`, `zh.srt`, `bilingual.srt`. Rendering both takes about 2 minutes for a 3-minute video on an M4 Pro.

## With Claude Code

The whole flow (prep → clean subtitles → review → render) is the `gd-video` skill in this repo (`.claude/skills/gd-video/SKILL.md`). It works when Claude Code runs in this repo. To use it from any folder (e.g. the Obsidian vault), link it at user level once:

```sh
ln -s ~/Documents/gd-video/.claude/skills/gd-video ~/.claude/skills/gd-video
```

Then run:

```
/gd-video ~/Downloads/GD/2026-11-03
```

## Tuning

Layout, audio mix and subtitle style are constants at the top of `gdvideo.py`: `PIP_WIDTH`, `PIP_TOP`, `GAME_VOLUME`, `VOICE_VOLUME`, `LOUDNESS`, `SUB_GAP`, plus the ASS style in `write_ass`.
