"""render for a single recording (OBS: game + facecam in one video): cover + video per platform, and SRT files."""
import json
import sys

from gdvideo.config import (COVER_INTRO, FFMPEG, LOUDNESS, SINGLE_BITRATES, SINGLE_BURN_HEIGHT, SINGLE_SUB_BOTTOM,
                            SINGLE_SUB_BOTTOM_EN, SINGLE_SUB_EN_SIZE, SINGLE_SUB_ZH_SIZE, TRUE_PEAK)
from gdvideo.media import encode_args, probe, recording, run, stream_info
from gdvideo.render import loudness
from gdvideo.subtitles import is_cleaned, write_ass, write_srt

ASS_HEIGHT = 1080  # subtitle sizes and positions are given on a frame this high; libass scales them to the video

# Per platform: burned-in subtitle languages (None: captions are uploaded as files), their distance from the bottom
# edge, and whether the video is scaled down to SINGLE_BURN_HEIGHT.
TARGETS = {
    "youtube": {"subs": None, "bottom": None, "scale": False},
    "tiktok": {"subs": ["en"], "bottom": SINGLE_SUB_BOTTOM_EN, "scale": True},
    "douyin": {"subs": ["zh", "en"], "bottom": SINGLE_SUB_BOTTOM, "scale": True},
}


def output_size(width, height, scale):
    """Output frame size: the source size, or scaled down to SINGLE_BURN_HEIGHT (even width)."""
    if scale and SINGLE_BURN_HEIGHT and height > SINGLE_BURN_HEIGHT:
        return round(width * SINGLE_BURN_HEIGHT / height / 2) * 2, SINGLE_BURN_HEIGHT
    return width, height


def bitrate(height):
    return next(rate for min_height, rate in SINGLE_BITRATES if height >= min_height)


def render_single(folder, only=None, test=None):
    """export/<platform>.mp4 for each platform: the cover for COVER_INTRO seconds, then the recording, with that
    platform's subtitles burned in. The SRT files are shifted by COVER_INTRO so they match these videos."""
    work, out = folder / "work", folder / "export"
    work.mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)
    subs_path = folder / "subs.json"
    if not subs_path.exists():
        sys.exit(f"{subs_path} not found. Run prep and clean first (or use: gdvideo all <folder>).")
    data = json.loads(subs_path.read_text())
    cues = data["cues"]
    if not is_cleaned(data):
        sys.exit(f"{subs_path} has no en/zh text. Run: gdvideo clean <folder> --force")
    cover = out / "cover.jpg"
    if not cover.exists():
        sys.exit(f"{cover} not found. Make it first: gdvideo cover <folder>")

    write_srt(cues, out / "en.srt", ["en"], COVER_INTRO)
    write_srt(cues, out / "zh.srt", ["zh"], COVER_INTRO)
    write_srt(cues, out / "bilingual.srt", ["zh", "en"], COVER_INTRO)

    video = recording(folder, "video")
    width, height, dur = probe(video)
    fps = stream_info(video, "v:0", "r_frame_rate")
    rate = stream_info(video, "a:0", "sample_rate") or "48000"
    source = ["-i", str(video)]
    suffix = ""
    if test:
        dur = min(dur, test)
        source = ["-t", str(dur), *source]
        suffix = "-test"  # never overwrite the full videos with a test clip

    # One gain for the whole video, then a peak limiter (see render.py for why not loudnorm)
    gain = LOUDNESS - loudness(source, "[0:a:0]anull", dur)
    audio = (f"anullsrc=r={rate}:cl=stereo,atrim=duration={COVER_INTRO}[ca];"
             f"[1:a:0]aresample={rate},aformat=channel_layouts=stereo,volume={gain:.2f}dB,"
             f"alimiter=limit={10 ** (TRUE_PEAK / 20):.3f}:level=0[a]")

    for name, target in TARGETS.items():
        if only not in (None, name):
            continue
        w, h = output_size(width, height, target["scale"])
        burn = ""
        if target["subs"]:
            ass_size = (round(ASS_HEIGHT * width / height), ASS_HEIGHT)
            write_ass(cues, work / f"{name}.ass", target["subs"], bottom=target["bottom"], size=ass_size,
                      zh_size=SINGLE_SUB_ZH_SIZE, en_size=SINGLE_SUB_EN_SIZE)
            burn = f",subtitles={name}.ass"
        # Subtitles are burned before the cover is put in front, so cue times stay on the recording's timeline
        vf = (f"[0:v]scale={w}:{h}:out_range=tv:out_color_matrix=bt709,setsar=1,fps={fps},format=yuv420p,"
              f"trim=duration={COVER_INTRO}[cv];"
              f"[1:v]scale={w}:{h},setsar=1,fps={fps}{burn},format=yuv420p[v];"
              f"{audio};[cv][ca][v][a]concat=n=2:v=1:a=1[ov][oa]")
        run([FFMPEG, "-v", "warning", "-stats", "-y", "-loop", "1", "-i", str(cover), *source,
             "-filter_complex", vf, "-map", "[ov]", "-map", "[oa]", *encode_args(bitrate(h)),
             str(out / f"{name}{suffix}.mp4")], cwd=work)

    print(f"Done: {out}", file=sys.stderr)
