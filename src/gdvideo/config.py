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

# Cover (gdvideo cover)
ASSETS = Path(__file__).resolve().parents[2] / "assets"
COVER_LOGO = ASSETS / "logo.png"                         # "GEOMETRY DASH" logo from Canva, transparent PNG
COVER_FONT = ASSETS / "fonts" / "PermanentMarker-Regular.ttf"
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
COVER_EMOJI = "🔥"
COVER_AT = 0.3            # take the frame at this fraction of the video (override with --at)
COVER_MAX_WIDTH = 1920    # output width; YouTube thumbnails must be under 2 MB
# Positions and sizes as fractions of the cover width (x, widths) or height (y, title size).
# title_y is where the title starts (smaller = higher). title_bottom only pushes it up when it would end below that
# line, keeping it above the platform UI / the 3:4 crop 抖音 and TikTok use in profile grids.
COVER_LAYOUT = {
    # horizontal recording: the facecam is in the frame, top right
    "horizontal": {"logo_x": 0.09, "logo_y": 0.16, "logo_w": 0.5,
                   "title_x": 0.1, "title_y": 0.62, "title_w": 0.8, "title_size": 0.13, "title_bottom": 0.95},
    # vertical recording (Aitum layout: facecam y 0-810, game 810-1506, black below): logo and title over the game,
    # inside the 3:4 crop of profile grids (y 240-1680)
    "vertical": {"logo_x": 0.06, "logo_y": 0.44, "logo_w": 0.7,
                 "title_x": 0.05, "title_y": 0.6, "title_w": 0.7, "title_size": 0.06, "title_bottom": 0.78},
}
COVER_TITLE_COLOR = "#FFE14D"     # title fill (GD yellow); any PIL color name or hex
COVER_TITLE_STROKE = "#173A5E"    # title outline, the dark blue of the logo outline
COVER_TITLE_STROKE_W = 0.10       # outline width as a fraction of the font size
COVER_TITLE_SHADOW = (0.06, 0.08)  # drop shadow offset (x, y) as a fraction of the font size; None for no shadow
COVER_TILT = 4            # degrees the logo and title are tilted (counter-clockwise)
COVER_INTRO = 0.1         # seconds the cover shows at the start of the 抖音/TikTok videos, so it can be picked as cover

# Vertical videos (tiktok.mp4, douyin.mp4) are rendered from the vertical recording at this size
V_W, V_H = 1080, 1920
VERTICAL_BITRATE = "12M"
# Burned-in subtitles, px on the 1080x1920 frame. The apps cover roughly the bottom 300 px with their caption and
# buttons; the recording's black band below the game (y 1506-1920) is free, so subtitles sit at its top.
VERTICAL_SUB_BOTTOM = 360     # 抖音 (zh + en): px from the bottom edge to the bottom of the subtitles
VERTICAL_SUB_BOTTOM_EN = 320  # TikTok (en only): same
SUB_ZH_SIZE = 45              # Chinese line font size
SUB_EN_SIZE = 38              # English line font size
SUB_END_STRIP = "。.，,、；;：:"  # removed from the end of each subtitle line; ？！?! and … stay
SUB_FONT = "Hiragino Sans GB"  # macOS system font with a real bold; PingFang loads only as Medium in libass

# Audio of the vertical videos: one fixed gain for the whole video to reach the loudness target
LOUDNESS = -14            # LUFS, the target for TikTok/抖音
TRUE_PEAK = -1.5          # dBFS, peak limiter ceiling after that gain

# Sync: the vertical recording is lined up with the horizontal one by matching their audio in windows of this length
SYNC_WINDOW = 30          # seconds; shorter for short recordings so there are at least 3 windows

# Subtitle cue splitting
MAX_CHARS = 50
MAX_DURATION = 4.0
PAUSE_SPLIT = 0.5

SR = 16000                # sample rate for sync and transcription audio
