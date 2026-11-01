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

# Posting text (gdvideo post); channel.md sits at the repo root next to glossary.md
CHANNEL = Path(os.environ.get("GDVIDEO_CHANNEL", Path(__file__).resolve().parents[2] / "channel.md"))
YT_MAX_TITLE = 100        # YouTube title limit (characters)
YT_MAX_TAG_CHARS = 500    # YouTube limit for all tags together
IG_MAX_HASHTAGS = 30      # Instagram limit per post

# Cover (gdvideo cover)
ASSETS = Path(__file__).resolve().parents[2] / "assets"
COVER_LOGO = ASSETS / "logo.png"                         # "GEOMETRY DASH" logo from Canva, transparent PNG
COVER_FONT = ASSETS / "fonts" / "PermanentMarker-Regular.ttf"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
COVER_EMOJI = "🔥"
COVER_AT = 0.3            # take the frame at this fraction of the video (override with --at)
COVER_MAX_WIDTH = 1920    # output width; YouTube thumbnails must be under 2 MB
# Positions and sizes as fractions of the cover width (x, widths) or height (y, title size).
# title_bottom keeps the title above the platform UI / the 3:4 crop 抖音 and TikTok use in profile grids.
COVER_LAYOUT = {
    "horizontal": {"logo_x": 0.03, "logo_y": 0.22, "logo_w": 0.62,
                   "title_x": 0.06, "title_y": 0.68, "title_w": 0.8, "title_size": 0.09, "title_bottom": 0.96},
    "vertical": {"logo_x": 0.05, "logo_y": 0.40, "logo_w": 0.85,
                 "title_x": 0.05, "title_y": 0.72, "title_w": 0.85, "title_size": 0.06, "title_bottom": 0.87},
}
COVER_TILT = 4            # degrees the logo and title are tilted (counter-clockwise)
COVER_INTRO = 0.1         # seconds the cover shows at the start of the 抖音/TikTok videos, so it can be picked as cover

# Layout
PIP_WIDTH = 0.22          # horizontal: facecam width as a fraction of the canvas width
PIP_MARGIN = 32           # px from the right edge
PIP_TOP = 110             # px from the top, below the progress bar
PIP_BORDER = 6            # white border around the facecam
V_W, V_H = 1080, 1920     # vertical canvas
V_BG = "black"
SUB_GAP = -50              # px between the game and the first subtitle line
SUB_END_STRIP = "。.，,、；;：:"  # removed from the end of each subtitle line; ？！?! and … stay
SUB_FONT = "Hiragino Sans GB"  # macOS system font with a real bold; PingFang loads only as Medium in libass

# Audio
GAME_VOLUME = 0.1
VOICE_VOLUME = 1.0
LOUDNESS = -14            # LUFS, the target for YouTube/TikTok

# Subtitle cue splitting
MAX_CHARS = 42
MAX_DURATION = 4.0
PAUSE_SPLIT = 0.5

SR = 16000                # sample rate for sync and transcription audio
