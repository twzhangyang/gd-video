# gd-video

Pipeline that turns a Geometry Dash recording session into uploads with bilingual subtitles. OBS records each session twice at the same time, both with game + facecam: the horizontal recording goes to YouTube untouched (with `en.srt` / `zh.srt` captions), the vertical 1080×1920 one (Aitum Vertical) becomes TikTok (English burned in) and 抖音 (Chinese + English burned in). Setup and usage are in `README.md`.

## Product context lives in Obsidian

This repo holds the code and the subtitle glossary. The goals, decisions and workflow live in the Obsidian vault at `~/Documents/obsidian/geometry-dash/`. Read the relevant note before changing behaviour, and update it when a decision changes:

| Note | What it holds |
|---|---|
| `Video Workflow.md` | Hub: goals, both output formats, per-video steps, topic list |
| `Recording Setup.md` | Gear, recording routine, sync and audio decisions |

`channel.md` (channel profile for `gdvideo post`) also lives in this repo. The subtitle glossary is the other exception: it lives in this repo as `glossary.md` (game terms, mishearings, zh translations, cleanup rules). `gdvideo` reads the **Levels** and **Game terms** sections at runtime as the Whisper hint; the skill uses the whole file for cleanup. When a correction will recur, add it there.

The end-to-end workflow, including the subtitle cleanup rules, is the skill at `.claude/skills/gd-video/SKILL.md` in this repo (linked from `~/.claude/skills/gd-video` so it works from any folder). Keep it in sync when commands, options or outputs change.

Follow the vault's own `CLAUDE.md` when editing notes there (wikilinks, edit in place, never touch `.obsidian/`).

## Code

- Python package in `src/gdvideo/` (module map in `README.md`) with the `gdvideo` command and subcommands `prep` (vertical offset + Whisper on the horizontal recording → `work/subs.raw.json`), `clean` (Claude API → `<folder>/subs.json` + `work/review.txt`), `post` (Claude API → `<folder>/post.md`), `cover` (logo + title on the same moment of each recording → `export/cover-horizontal.jpg`, `cover-vertical.jpg`), `render` (vertical recording → `export/tiktok.mp4`, `douyin.mp4`, each starting with the vertical cover for `COVER_INTRO`; plus `en/zh/bilingual.srt`), `pack` (hard links + `post.txt` from the text blocks parsed from `post.md` → `export/pack/<platform>/`, rebuilt every run; YouTube gets the horizontal recording itself) and `all` (prep, clean, post, cover, render, pack; skips prep/clean/post/cover whose output exists). `work/` and `export/` are disposable; `subs.json` and `post.md` sit next to the recordings so deleting them never loses work
- `media.recordings(folder)` finds the two videos: the one with "vertical" in its name (Aitum saves `<date>-vertical.mov`) and the other one. No renaming needed
- Cue times in `subs.json` are on the horizontal recording's timeline. `vertical_start` (seconds into the vertical recording at horizontal t=0, negative if it started later) shifts them for the burned-in ASS (`write_ass(shift=...)`) and picks the vertical cover frame
- The pipeline must run from the terminal without Claude Code. `clean` and `post` call the Anthropic API directly through `claude.ask_json` (`CLAUDE_MODEL`, structured output; rules in `CLEAN_PROMPT` / `POST_PROMPT`); it needs `ANTHROPIC_API_KEY`. The cleanup rules live in `CLEAN_PROMPT` and `glossary.md`, not in the skill
- Installed editable in the venv: `.venv/bin/pip install -e '.[dev]'`, run as `.venv/bin/gdvideo ...`. Dependencies are pinned in `pyproject.toml`
- FFmpeg is `ffmpeg-full` (keg-only, has libass) at `/opt/homebrew/opt/ffmpeg-full/bin/`. The regular brew `ffmpeg` has no `subtitles` filter
- Tunable layout, audio and subtitle constants are at the top of the file. Keep new settings there

## Facts that shaped the design

- 剪映 (8.3) encrypts its draft files, so the pipeline can't generate 剪映 projects. Everything renders with FFmpeg; `bilingual.srt` is the hand-off to 剪映
- The two OBS recordings don't start at the same instant (2026-11-17: the vertical one started 1.6 s later). Both carry the same audio mix, so `find_offset` (GCC-PHAT over windows, majority value) measures it reliably; `sync_window` shortens the window for short recordings
- YouTube gets the horizontal recording without re-encoding: the thumbnail and captions are uploaded separately and YouTube normalizes loudness itself. Only TikTok and 抖音 need the cover as the first frame
- The Aitum layout (2026-11-17) is facecam y 0–810, game 810–1506, black below. Subtitles sit in that black band (`VERTICAL_SUB_BOTTOM*`) and the vertical cover's logo and title over the game (`COVER_LAYOUT["vertical"]`); retune both if the OBS layout changes
- The horizontal recording may have several audio tracks; `prep` transcribes the last one (record the mic alone there)

## Testing

`.venv/bin/pytest` covers the pure functions (no ffmpeg or API key needed). To check a layout change, render a short clip of a real session and look at frames:

```sh
.venv/bin/gdvideo render <folder> --test 20
ffmpeg -ss 4 -i <folder>/export/douyin-test.mp4 -frames:v 1 /tmp/check.jpg
```

Sample session: `~/Downloads/GD/2026-11-17` (horizontal 2992×1934 + vertical 1080×1920, 60 fps, 4 min; a subtitle shows at 4 s). Older folders (`2026-11-10` iPad + facecam, `2026-11-15` single recording) are from removed modes and no longer run.
