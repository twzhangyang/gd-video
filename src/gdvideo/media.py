"""ffmpeg / ffprobe helpers."""
import json
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

from gdvideo.config import FFMPEG, FFPROBE, SR

VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v"}


def recordings(folder):
    """(horizontal, vertical): the two OBS recordings in the folder. The vertical one has "vertical" in its name
    (Aitum Vertical saves "<date>-vertical.mov"; vertical.mp4 works too), the horizontal one is the other video."""
    videos = sorted(p for p in folder.iterdir()
                    if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS and not p.name.startswith("."))
    vertical = [p for p in videos if "vertical" in p.stem.lower()]
    horizontal = [p for p in videos if p not in vertical]
    if len(horizontal) != 1 or len(vertical) != 1:
        found = ", ".join(p.name for p in videos) or "none"
        sys.exit(f"{folder} should have two videos: the horizontal recording and the vertical one (with \"vertical\" "
                 f"in its name). Found: {found}")
    return horizontal[0], vertical[0]


def audio_tracks(path):
    return len(stream_info(path, "a", "index").split())


def stream_info(path, stream, entry):
    """One ffprobe value of a stream, e.g. stream_info(p, 'v:0', 'r_frame_rate'). '' if there is no such stream."""
    return subprocess.run([FFPROBE, "-v", "error", "-select_streams", stream, "-show_entries", f"stream={entry}",
                           "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip()


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd[:6]), "...", file=sys.stderr)
    subprocess.run(cmd, check=True, **kw)


def probe(path):
    """Display width, height (rotation applied) and duration of a video."""
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    w, h = s["width"], s["height"]
    rot = next((abs(int(d.get("rotation", 0))) for d in s.get("side_data_list", [])), 0)
    if rot in (90, 270):
        w, h = h, w
    return w, h, float(j["format"]["duration"])


def extract_wav(src, dst, track=0):
    run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-vn", "-map", f"0:a:{track}", "-ac", "1", "-ar", str(SR),
         str(dst)])
    return wavfile.read(dst)[1].astype(np.float64)


def encode_args(bitrate):
    return ["-c:v", "h264_videotoolbox", "-b:v", bitrate, "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
