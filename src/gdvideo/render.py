"""render: the vertical recording -> export/tiktok.mp4 (en) and douyin.mp4 (zh + en), each starting with the cover,
plus en/zh/bilingual SRT files on the horizontal recording's timeline (YouTube gets the horizontal recording as is)."""
import json
import re
import subprocess
import sys

from gdvideo.config import (COVER_INTRO, FFMPEG, LOUDNESS, TRUE_PEAK, V_H, V_W, VERTICAL_BITRATE, VERTICAL_SUB_BOTTOM,
                            VERTICAL_SUB_BOTTOM_EN)
from gdvideo.media import encode_args, probe, recordings, run, stream_info
from gdvideo.subtitles import is_cleaned, write_ass, write_srt

# Per platform: burned-in subtitle languages and their distance from the bottom edge
TARGETS = {
    "tiktok": {"subs": ["en"], "bottom": VERTICAL_SUB_BOTTOM_EN},
    "douyin": {"subs": ["zh", "en"], "bottom": VERTICAL_SUB_BOTTOM},
}


def load_subs(folder):
    """subs.json, checked to be cleaned."""
    path = folder / "subs.json"
    if not path.exists():
        sys.exit(f"{path} not found. Run prep and clean first (or use: gdvideo all <folder>).")
    data = json.loads(path.read_text())
    if not is_cleaned(data):
        sys.exit(f"{path} has no en/zh text. Run: gdvideo clean <folder> --force")
    return data


def loudness(inputs, audio, dur):
    """Integrated loudness (LUFS) of the audio, measured before rendering so one fixed gain can be applied."""
    err = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-vn", *inputs, "-filter_complex", f"{audio},ebur128",
                          "-t", str(dur), "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def render(folder, only=None, test=None):
    """export/<platform>.mp4 for TikTok and 抖音: the cover for COVER_INTRO seconds, then the vertical recording with
    that platform's subtitles burned in."""
    work, out = folder / "work", folder / "export"
    work.mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)
    data = load_subs(folder)
    cues = data["cues"]
    shift = data.get("vertical_start", 0)

    # Captions for YouTube (uploaded next to the untouched horizontal recording) and the 剪映 hand-off
    write_srt(cues, out / "en.srt", ["en"])
    write_srt(cues, out / "zh.srt", ["zh"])
    write_srt(cues, out / "bilingual.srt", ["zh", "en"])

    cover = out / "cover-vertical.jpg"
    if not cover.exists():
        sys.exit(f"{cover} not found. Make it first: gdvideo cover <folder>")
    _, video = recordings(folder)
    width, height, dur = probe(video)
    if abs(width / height - V_W / V_H) > 0.01:
        print(f"Warning: {video.name} is {width}x{height}, not 9:16; it is fitted into {V_W}x{V_H} with bars",
              file=sys.stderr)
    fps = stream_info(video, "v:0", "r_frame_rate")
    rate = stream_info(video, "a:0", "sample_rate") or "48000"
    source = ["-i", str(video)]
    suffix = ""
    if test:
        dur = min(dur, test)
        source = ["-t", str(dur), *source]
        suffix = "-test"  # never overwrite the full videos with a test clip

    # One gain for the whole video, then a peak limiter. A single-pass loudnorm would act as an automatic gain
    # control and turn up the pauses between words.
    gain = LOUDNESS - loudness(source, "[0:a:0]anull", dur)
    audio = (f"anullsrc=r={rate}:cl=stereo,atrim=duration={COVER_INTRO}[ca];"
             f"[1:a:0]aresample={rate},aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
             f"alimiter=limit={10 ** (TRUE_PEAK / 20):.3f}:level=0[a]")
    fit = f"scale={V_W}:{V_H}:force_original_aspect_ratio=decrease,pad={V_W}:{V_H}:-1:-1,setsar=1,fps={fps}"
    cover_v = (f"[0:v]scale={V_W}:{V_H}:out_range=tv:out_color_matrix=bt709,setsar=1,fps={fps},format=yuv420p,"
               f"trim=duration={COVER_INTRO}[cv]")

    for name, target in TARGETS.items():
        if only not in (None, name):
            continue
        write_ass(cues, work / f"{name}.ass", target["subs"], bottom=target["bottom"], shift=shift)
        # Subtitles are burned before the cover is put in front, so cue times stay on the recording's timeline
        vf = (f"{cover_v};[1:v]{fit},subtitles={name}.ass,format=yuv420p[v];"
              f"{audio};[cv][ca][v][a]concat=n=2:v=1:a=1[ov][oa]")
        run([FFMPEG, "-v", "warning", "-stats", "-y", "-loop", "1", "-i", str(cover), *source,
             "-filter_complex", vf, "-map", "[ov]", "-map", "[oa]", *encode_args(VERTICAL_BITRATE),
             str(out / f"{name}{suffix}.mp4")], cwd=work)

    print(f"Done: {out}", file=sys.stderr)
