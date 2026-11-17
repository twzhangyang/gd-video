---
name: gd-video
description: Turn a Geometry Dash recording session (two OBS recordings made at the same time, a horizontal one and a vertical 9:16 one from Aitum Vertical, both with game + facecam) into uploads for YouTube (original video + en/zh captions), TikTok (English subtitles burned in) and 抖音 (Chinese + English burned in), with covers and posting text. Use when the user gives a GD video folder or asks to make/render/subtitle a Geometry Dash video.
---

# gd-video

Pipeline: the `gdvideo` command from the repo `~/Documents/gd-video` (Python package in `src/gdvideo/`; venv at `~/Documents/gd-video/.venv`, setup in its `README.md`).
If `.venv` or `ffmpeg-full` is missing, follow the README setup first.
Workflow notes (product context): `~/Documents/obsidian/geometry-dash/`, starting at `Video Workflow.md`.
This skill lives in the repo at `.claude/skills/gd-video/` and is linked from `~/.claude/skills/gd-video`, so it works from any folder.

Input: a folder (e.g. `~/Downloads/GD/2026-11-17`) with the two OBS recordings.

## Steps

1. **Check the inputs.** The folder must contain exactly two videos: the horizontal recording and the vertical one,
   which has "vertical" in its name (Aitum Vertical saves `<date>-vertical.mov`). If the vertical one has no
   "vertical" in its name, find it (1080×1920: `ffprobe -v error -show_entries stream=width,height <file>`) and ask
   before renaming it.

2. **Prep (line up + transcribe):**
   ```
   ~/Documents/gd-video/.venv/bin/gdvideo prep <folder>
   ```
   Measures how far apart the two recordings started from their audio (`vertical_start`) and transcribes the
   horizontal recording. If it exits with "unreliable", ask the user and pass `--vertical-start S` (seconds into the
   vertical recording when the horizontal one starts; negative if the vertical one started later).

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

5. **Posting text:** `~/Documents/gd-video/.venv/bin/gdvideo post <folder>` writes `<folder>/post.md`
   (YouTube title/description/tags, 抖音 title/caption, TikTok caption). Pass `--level` / `--notes` if the user gives them.

6. **Covers:** `~/Documents/gd-video/.venv/bin/gdvideo cover <folder>` writes `<folder>/export/cover-horizontal.jpg`
   (YouTube) and `cover-vertical.jpg` (TikTok/抖音) from the same moment of each recording. `--text` sets the title,
   `--at 1:05` picks the moment, `--only horizontal|vertical` makes one. Show them to the user. This comes before
   render, because the TikTok and 抖音 videos start with the vertical cover.

7. **Render:**
   ```
   ~/Documents/gd-video/.venv/bin/gdvideo render <folder>
   ```
   Writes `export/tiktok.mp4` (English at the bottom) and `export/douyin.mp4` (Chinese + English) from the vertical
   recording, each starting with the cover for 0.1 s, plus `en.srt`, `zh.srt`, `bilingual.srt`. `--only tiktok|douyin`
   renders one; `--test 20` renders 20 s clips (`*-test.mp4`) for a quick check. After editing `subs.json` or the
   cover, run render and pack again.

8. **Pack:** `~/Documents/gd-video/.venv/bin/gdvideo pack <folder>` builds `<folder>/export/pack/<platform>/` for
   youtube (the horizontal recording itself + cover + captions), douyin and tiktok (video + cover), each with
   `post.txt`. If it lists missing files, run the commands it prints, then pack again.

`gdvideo all <folder>` runs steps 2–8 in order, skipping prep/clean/post/cover whose output exists.

9. **Report** the outputs in `<folder>/export/pack/` and `<folder>/post.md`:
   - YouTube: the horizontal recording as is; upload `cover.jpg` as the thumbnail and the two SRTs as captions
   - TikTok: `tiktok.mp4` (pick the first frame as the cover); 抖音: `douyin.mp4`
   - `bilingual.srt` → for 剪映 if they want to edit further

## Tuning

Constants in `src/gdvideo/config.py`: `VERTICAL_SUB_BOTTOM` (抖音), `VERTICAL_SUB_BOTTOM_EN` (TikTok), `SUB_ZH_SIZE`,
`SUB_EN_SIZE` (px on the 1080×1920 frame, set for the current Aitum layout), `COVER_LAYOUT`, `LOUDNESS`,
`CLAUDE_MODEL`; the subtitle style is `write_ass` in `src/gdvideo/subtitles.py`.
