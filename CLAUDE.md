# gd-video

Pipeline that turns a Geometry Dash recording session (iPad gameplay + MacBook facecam) into a horizontal YouTube video and a vertical 9:16 video with bilingual subtitles. Setup and usage are in `README.md`.

## Product context lives in Obsidian

This repo holds the code and the subtitle glossary. The goals, decisions and workflow live in the Obsidian vault at `~/Documents/obsidian/geometry-dash/`. Read the relevant note before changing behaviour, and update it when a decision changes:

| Note | What it holds |
|---|---|
| `Video Workflow.md` | Hub: goals, both output formats, per-video steps, topic list |
| `Recording Setup.md` | Gear, recording routine, sync and audio decisions |

The subtitle glossary is the exception: it lives in this repo as `glossary.md` (game terms, mishearings, zh translations, cleanup rules). `gdvideo.py` reads the **Levels** and **Game terms** sections at runtime as the Whisper hint; the skill uses the whole file for cleanup. When a correction will recur, add it there.

The end-to-end workflow, including the subtitle cleanup rules, is the skill at `.claude/skills/gd-video/SKILL.md` in this repo (linked from `~/.claude/skills/gd-video` so it works from any folder). Keep it in sync when commands, options or outputs change.

Follow the vault's own `CLAUDE.md` when editing notes there (wikilinks, edit in place, never touch `.obsidian/`).

## Code

- Single script: `gdvideo.py`, with subcommands `prep` (sync + Whisper → `work/subs.json`) and `render` (`subs.json` → `export/`)
- Run with the venv: `.venv/bin/python gdvideo.py ...`. Dependencies are pinned in `requirements.txt`
- FFmpeg is `ffmpeg-full` (keg-only, has libass) at `/opt/homebrew/opt/ffmpeg-full/bin/`. The regular brew `ffmpeg` has no `subtitles` filter
- Tunable layout, audio and subtitle constants are at the top of the file. Keep new settings there

## Facts that shaped the design

- 剪映 (8.3) encrypts its draft files, so the pipeline can't generate 剪映 projects. Everything renders with FFmpeg; `--subs none` + `bilingual.srt` is the hand-off to 剪映
- `ipad.mov` has game audio only and `face.mov` has voice only (lav mic). Sync works because the lav picks up faint game sound from the iPad speaker. `find_offset` matches 30 s windows with GCC-PHAT and takes the majority value
- iPad recordings are stored rotated (display matrix 90°) and have black side bars; `probe` handles rotation and `detect_side_bars` crops the bars
- The facecam is variable frame rate (~27 fps); both inputs are converted to 60 fps

## Testing

There are no unit tests. To check a change, render a short clip of a real session and look at frames:

```sh
.venv/bin/python gdvideo.py render <folder> --test 20
ffmpeg -ss 10 -i <folder>/export/vertical.mp4 -frames:v 1 /tmp/check.jpg
```

Sample session: `~/Downloads/GD/2026-11-03`.
