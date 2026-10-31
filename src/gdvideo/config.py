"""Tunable settings and paths. Keep new settings here."""
import os
from pathlib import Path

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"

# glossary.md sits at the repo root (src/gdvideo/config.py -> parents[2]); override with GDVIDEO_GLOSSARY
GLOSSARY = Path(os.environ.get("GDVIDEO_GLOSSARY", Path(__file__).resolve().parents[2] / "glossary.md"))
GLOSSARY_TERM_SECTIONS = {"Levels", "Game terms"}

CLAUDE_MODEL = "claude-opus-5-5"
CLAUDE_EFFORT = "medium"

# Layout
PIP_WIDTH = 0.22          # horizontal: facecam width as a fraction of the canvas width
PIP_MARGIN = 32           # px from the right edge
PIP_TOP = 110             # px from the top, below the progress bar
PIP_BORDER = 6            # white border around the facecam
V_W, V_H = 1080, 1920     # vertical canvas
V_BG = "black"
SUB_GAP = 40              # px between the game and the first subtitle line

# Audio
GAME_VOLUME = 0.3
VOICE_VOLUME = 1.0
LOUDNESS = -14            # LUFS, the target for YouTube/TikTok

# Subtitle cue splitting
MAX_CHARS = 42
MAX_DURATION = 4.0
PAUSE_SPLIT = 0.5

SR = 16000                # sample rate for sync and transcription audio
