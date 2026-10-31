"""ffmpeg / ffprobe helpers."""
import json
import re
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

from gdvideo.config import FFMPEG, FFPROBE, SR


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


def detect_side_bars(path, duration):
    """Width and x of the game area inside the iPad recording (it has black bars left and right)."""
    found = []
    for t in (duration * 0.25, duration * 0.5, duration * 0.75):
        out = subprocess.run(
            [FFMPEG, "-v", "info", "-ss", str(t), "-i", str(path), "-t", "5",
             "-vf", "cropdetect=limit=24:round=2", "-f", "null", "-"],
            capture_output=True, text=True).stderr
        found += re.findall(r"crop=(\d+):\d+:(\d+):\d+", out)
    w, x = max(set(found), key=found.count)
    return int(w), int(x)


def extract_wav(src, dst):
    run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", str(SR), str(dst)])
    return wavfile.read(dst)[1].astype(np.float64)


def encode_args(bitrate):
    return ["-c:v", "h264_videotoolbox", "-b:v", bitrate, "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
