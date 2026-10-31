---
name: gd-video
description: Turn a Geometry Dash recording session (iPad gameplay ipad.mov + MacBook facecam face.mov) into a horizontal YouTube video and a vertical 9:16 video with cleaned bilingual (zh/en) subtitles. Use when the user gives a GD video folder or asks to make/render/subtitle a Geometry Dash video.
---

# gd-video

Pipeline code: `~/Documents/gd-video/gdvideo.py` (git repo; venv at `~/Documents/gd-video/.venv`, setup in its `README.md`).
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
   ~/Documents/gd-video/.venv/bin/python ~/Documents/gd-video/gdvideo.py prep <folder>
   ```
   It prints the sync offset and how many 30 s windows agree. If it exits with "Sync is unreliable",
   tell the user and ask for the offset (seconds into face.mov matching ipad.mov t=0), then rerun with `--offset`.

3. **Clean and translate `<folder>/work/subs.json`.** First copy it to `subs.raw.json`.
   Read `~/Documents/gd-video/glossary.md` and apply it. Replace `cues` with cleaned cues
   `{"start", "end", "en", "zh"}`:
   - Fix mishearings with the glossary (`wrong → right`), use its zh translations for game terms
   - Drop filler-only cues ("okay okay okay", "whatever", "um") and filler inside lines
   - Rejoin sentences Whisper split badly, then re-split into one idea per cue, `en` ≤ 45 chars
   - Keep timings inside the original cue boundaries (you may merge or split them; don't shift speech)
   - Keep the speaker's voice and reactions; don't make it formal
   - `zh`: natural, casual simplified Chinese; level names stay in English
   - If the speech is Chinese, `zh` is the cleaned source and `en` the translation

4. **Show the user a short review list** before rendering: only the lines you were unsure about
   (guessed words, possible mishearings), with timestamps. Ask whether to fix anything.
   If they add a correction that will recur, add it to `~/Documents/gd-video/glossary.md`
   (new terms under **Levels** or **Game terms**, which are the sections Whisper reads).

5. **Render:**
   ```
   ~/Documents/gd-video/.venv/bin/python ~/Documents/gd-video/gdvideo.py render <folder> [--subs zh,en|en|zh|none]
   ```
   Default burns bilingual subtitles into the vertical video. `--subs none` gives clean videos for editing in 剪映
   (then import the SRT there). `--test 20` renders 20 s for a quick check. Takes about 2 minutes.

6. **Report** the outputs in `<folder>/export/`:
   - `horizontal.mp4` → YouTube, upload `en.srt` and `zh.srt` as captions
   - `vertical.mp4` → TikTok, Douyin, Instagram Reels, YouTube Shorts
   - `bilingual.srt` → for 剪映 if they want to edit further

## Tuning

Layout, volumes and subtitle styles are constants at the top of `gdvideo.py`
(`PIP_WIDTH`, `PIP_TOP`, `GAME_VOLUME`, `VOICE_VOLUME`, `SUB_GAP`, the ASS style in `write_ass`).
