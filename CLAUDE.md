# gd-video

Pipeline that turns a Geometry Dash recording session (iPad gameplay + MacBook facecam) into a horizontal YouTube video and a vertical 9:16 video with bilingual subtitles. Setup and usage are in `README.md`.

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

- Python package in `src/gdvideo/` (module map in `README.md`) with the `gdvideo` command and subcommands `prep` (start times + Whisper → `work/subs.raw.json`), `clean` (Claude API → `<folder>/subs.json` + `work/review.txt`), `post` (Claude API → `<folder>/post.md`), `render` (`subs.json` → `export/`), `cover` (logo + title on a frame → `export/cover-horizontal.jpg` from `horizontal.mp4`, `cover-vertical.jpg` built from the recordings without subtitles), `pack` (hard links of `export/` files + `post.txt` from the text blocks parsed from `post.md` → `export/pack/<platform>/`, rebuilt every run; 抖音/TikTok videos get the cover as a `COVER_INTRO` first frame, cached as `export/vertical-*-cover.mp4`) and `all` (prep, clean, post, render horizontal + `vertical-zh-en` + `vertical-en`, cover, pack; skips prep/clean/post/cover whose output exists). `work/` and `export/` are disposable; the cleaned `subs.json` sits next to the recordings so deleting them never loses subtitle work
- The pipeline must run from the terminal without Claude Code. `clean` and `post` call the Anthropic API directly through `claude.ask_json` (`CLAUDE_MODEL`, structured output; rules in `CLEAN_PROMPT` / `POST_PROMPT`); it needs `ANTHROPIC_API_KEY`. The cleanup rules live in `CLEAN_PROMPT` and `glossary.md`, not in the skill
- Installed editable in the venv: `.venv/bin/pip install -e '.[dev]'`, run as `.venv/bin/gdvideo ...`. Dependencies are pinned in `pyproject.toml`
- FFmpeg is `ffmpeg-full` (keg-only, has libass) at `/opt/homebrew/opt/ffmpeg-full/bin/`. The regular brew `ffmpeg` has no `subtitles` filter
- Tunable layout, audio and subtitle constants are at the top of the file. Keep new settings there

## Facts that shaped the design

- 剪映 (8.3) encrypts its draft files, so the pipeline can't generate 剪映 projects. Everything renders with FFmpeg; `--subs none` + `bilingual.srt` is the hand-off to 剪映
- `ipad.mov` has game audio only and `face.mov` has voice only (lav mic). By default both recordings are assumed to start together; `--ipad-start` / `--face-start` set where each begins. `--auto-sync` works because the lav picks up faint game sound from the iPad speaker: `find_offset` matches 30 s windows with GCC-PHAT and takes the majority value
- `subs.json` has `ipad_start` and `face_start` (seconds into each recording at video t=0; `face_start` < 0 only from auto-sync, then the facecam's first frame is held). Cue times are on the video timeline; render, cover and post read both through `subtitles.starts()`, which also reads older files with `offset` / `start`
- iPad recordings are stored rotated (display matrix 90°) and have black side bars; `probe` handles rotation and `detect_side_bars` crops the bars
- The facecam is variable frame rate (~27 fps); both inputs are converted to 60 fps

## Testing

There are no unit tests. To check a change, render a short clip of a real session and look at frames:

```sh
.venv/bin/gdvideo render <folder> --test 20
ffmpeg -ss 10 -i <folder>/export/vertical-zh-en-test.mp4 -frames:v 1 /tmp/check.jpg
```

Sample session: `~/Downloads/GD/2026-11-03`.
