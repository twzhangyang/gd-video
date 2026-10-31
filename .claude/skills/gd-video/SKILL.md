---
name: gd-video
description: Turn a Geometry Dash recording session (iPad gameplay ipad.mov + MacBook facecam face.mov) into a horizontal YouTube video and a vertical 9:16 video with cleaned bilingual (zh/en) subtitles. Use when the user gives a GD video folder or asks to make/render/subtitle a Geometry Dash video.
---

# gd-video

Pipeline: the `gdvideo` command from the repo `~/Documents/gd-video` (Python package in `src/gdvideo/`; venv at `~/Documents/gd-video/.venv`, setup in its `README.md`).
If `.venv` or `ffmpeg-full` is missing, follow the README setup first.
Workflow notes (product context): `~/Documents/obsidian/geometry-dash/`, starting at `Video Workflow.md`.
This skill lives in the repo at `.claude/skills/gd-video/` and is linked from `~/.claude/skills/gd-video`, so it works from any folder.

Input: a folder (e.g. `~/Downloads/GD/2026-11-03`) with the two recordings.

## Steps

1. **Check the inputs.** The folder must contain `ipad.mov` (game audio only) and `face.mov` (voice only).
   If the files have other names, identify them: the iPad file has the tag `com.apple.quicktime.author=ReplayKitRecording`
   (`ffprobe -v error -show_entries format_tags -of compact <file>`). Ask before renaming.

2. **Prep (sync + transcribe):**
   ```
   ~/Documents/gd-video/.venv/bin/gdvideo prep <folder>
   ```
   It prints the sync offset and how many 30 s windows agree. If it exits with "Sync is unreliable",
   tell the user and ask for the offset (seconds into face.mov matching ipad.mov t=0), then rerun with `--offset`.

3. **Clean and translate:**
   ```
   ~/Documents/gd-video/.venv/bin/gdvideo clean <folder>
   ```
   The script calls Claude through the Anthropic API (needs `ANTHROPIC_API_KEY`; see the README) and writes
   `<folder>/subs.json`. Don't clean the subtitles yourself: the rules live in the script and `glossary.md`.
   If `subs.json` already exists it stops; only pass `--force` if the user wants a fresh cleanup.

4. **Show the user the review list** from `<folder>/work/review.txt` (lines Claude was unsure about) before
   rendering, and ask whether to fix anything. Apply fixes by editing `en`/`zh` in `<folder>/subs.json`.
   If a correction will recur, add it to `~/Documents/gd-video/glossary.md`
   (new terms under **Levels** or **Game terms**, which are the sections Whisper reads).

5. **Render:**
   ```
   ~/Documents/gd-video/.venv/bin/gdvideo render <folder> [--subs zh,en|en|zh|none]
   ```
   Default burns bilingual subtitles into the vertical video. `--subs none` gives clean videos for editing in 剪映
   (then import the SRT there). `--test 20` renders 20 s for a quick check. Takes about 2 minutes.
   Changing layout or audio constants only needs `render` again, not `prep`.

6. **Report** the outputs in `<folder>/export/`:
   - `horizontal.mp4` → YouTube, upload `en.srt` and `zh.srt` as captions
   - `vertical.mp4` → TikTok, Douyin, Instagram Reels, YouTube Shorts
   - `bilingual.srt` → for 剪映 if they want to edit further

## Tuning

Layout, volumes and models are constants in `src/gdvideo/config.py`
(`PIP_WIDTH`, `PIP_TOP`, `GAME_VOLUME`, `VOICE_VOLUME`, `SUB_GAP`, `CLAUDE_MODEL`); the subtitle style is `write_ass` in `src/gdvideo/subtitles.py`.
