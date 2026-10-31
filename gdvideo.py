#!/usr/bin/env python3
"""Geometry Dash video pipeline: sync iPad gameplay + facecam, transcribe, render two layouts.

Folder layout (one folder per video):
    <folder>/ipad.mov   gameplay (game audio only)
    <folder>/face.mov   facecam (voice only)

Commands:
    prep   <folder>   sync + transcribe -> <folder>/work/subs.json  (then clean/translate it)
    render <folder>   subs.json -> <folder>/export/{horizontal,vertical}.mp4 + .srt files
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.io import wavfile

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
GLOSSARY = Path(__file__).resolve().parent / "glossary.md"
GLOSSARY_TERM_SECTIONS = {"Levels", "Game terms"}

# Layout
PIP_WIDTH = 0.22          # horizontal: facecam width as a fraction of the canvas width
PIP_MARGIN = 32           # px from the right edge
PIP_TOP = 110             # px from the top, below the progress bar
PIP_BORDER = 6            # white border around the facecam
V_W, V_H = 1080, 1920     # vertical canvas
V_BG = "black"
SUB_GAP = 40              # px between the game and the first subtitle line

# Audio
GAME_VOLUME = 0.6
VOICE_VOLUME = 1.0
LOUDNESS = -14            # LUFS, the target for YouTube/TikTok

# Subtitle cue splitting
MAX_CHARS = 42
MAX_DURATION = 4.0
PAUSE_SPLIT = 0.5

SR = 16000


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd[:6]), "...", file=sys.stderr)
    subprocess.run(cmd, check=True, **kw)


def probe(path):
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


def gcc_phat(a, b):
    """Lag (s) of b inside a, plus a peak z-score."""
    n = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    r = np.fft.rfft(a, n) * np.conj(np.fft.rfft(b, n))
    r /= np.abs(r) + 1e-9
    c = np.abs(np.fft.irfft(r, n))
    c = np.concatenate([c[-len(b):], c[:len(a)]])
    i = int(np.argmax(c))
    return (i - len(b)) / SR, (c[i] - c.mean()) / c.std()


def find_offset(game, voice, window=30):
    """Seconds into face.mov that line up with ipad.mov t=0.

    The facecam mic hears a little game audio from the iPad speaker; match it in
    30 s windows and take the value most windows agree on.
    """
    lags = []
    for start in range(0, int(len(voice) / SR) - window + 1, window):
        seg = voice[start * SR:(start + window) * SR]
        lag, z = gcc_phat(game, seg)
        lags.append(start - lag)
        print(f"  window {start:4d}s: offset {start - lag:+.3f}s (z={z:.1f})", file=sys.stderr)
    lags = np.array(lags)
    best = max(lags, key=lambda x: np.sum(np.abs(lags - x) < 0.1))
    agree = lags[np.abs(lags - best) < 0.1]
    return float(np.median(agree)), len(agree), len(lags)


def glossary_terms():
    """Correct spellings from glossary.md: '- wrong → right' or '- term' bullets in the term sections."""
    if not GLOSSARY.exists():
        return []
    terms, section = [], None
    for line in GLOSSARY.read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = re.match(r"\s*-\s+(?:\[.\]\s+)?(.+)", line)
        if m and section in GLOSSARY_TERM_SECTIONS:
            terms.append(re.split(r"\s*(?:→|->)\s*", m.group(1))[-1].strip())
    return list(dict.fromkeys(terms))


def split_cues(segments, offset):
    """Whisper word timestamps -> short cues on the ipad timeline."""
    words = [w for s in segments for w in s.get("words", [])]
    cues, cur = [], []

    def flush():
        if cur:
            text = "".join(w["word"] for w in cur).strip()
            cues.append({"start": round(max(cur[0]["start"] - offset, 0), 2),
                         "end": round(cur[-1]["end"] - offset, 2), "src": text})
            cur.clear()

    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > PAUSE_SPLIT
                    or len("".join(x["word"] for x in cur + [w]).strip()) > MAX_CHARS
                    or w["end"] - cur[0]["start"] > MAX_DURATION):
            flush()
        cur.append(w)
        if re.search(r"[.!?。！？]$", w["word"].strip()):
            flush()
    flush()
    return [c for c in cues if c["end"] > 0]


def cmd_prep(folder, args):
    work = folder / "work"
    work.mkdir(exist_ok=True)
    print("Extracting audio...", file=sys.stderr)
    game = extract_wav(folder / "ipad.mov", work / "ipad.wav")
    voice = extract_wav(folder / "face.mov", work / "face.wav")

    if args.offset is not None:
        offset = args.offset
        print(f"Using manual offset {offset:+.3f}s", file=sys.stderr)
    else:
        print("Syncing...", file=sys.stderr)
        offset, agree, total = find_offset(game, voice)
        print(f"Offset {offset:+.3f}s ({agree}/{total} windows agree)", file=sys.stderr)
        if agree < max(2, total / 2):
            sys.exit("Sync is unreliable. Find the offset by hand and rerun with --offset SECONDS "
                     "(seconds into face.mov that match ipad.mov t=0).")

    print("Transcribing...", file=sys.stderr)
    import mlx_whisper
    terms = glossary_terms()
    result = mlx_whisper.transcribe(
        str(work / "face.wav"), path_or_hf_repo=WHISPER_MODEL, word_timestamps=True,
        condition_on_previous_text=False, language=args.lang,
        initial_prompt=("Geometry Dash. " + ", ".join(terms)) if terms else "Geometry Dash.")

    cues = split_cues(result["segments"], offset)
    for c in cues:
        c["en"], c["zh"] = "", ""
    data = {"offset": round(offset, 3), "language": result["language"], "cues": cues}
    (work / "subs.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"Wrote {work / 'subs.json'}: {len(cues)} cues, language {result['language']}", file=sys.stderr)


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_srt(cues, path, fields):
    blocks = []
    for c in cues:
        text = "\n".join(c[f] for f in fields if c.get(f))
        if text:
            blocks.append(f"{len(blocks) + 1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{text}\n")
    path.write_text("\n".join(blocks))


def write_ass(cues, path, fields, top):
    """Vertical subtitles: Chinese (white) above English (yellow), centred below the game."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {V_W}
PlayResY: {V_H}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,PingFang SC,64,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,8,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        parts = []
        if "zh" in fields and c.get("zh"):
            parts.append(c["zh"])
        if "en" in fields and c.get("en"):
            parts.append(r"{\fs52\c&H00FFFF&}" + c["en"] + r"{\r}")
        if parts:
            lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Sub,,0,0,0,,"
                         rf"{{\pos({V_W // 2},{top})}}" + r"\N".join(parts))
    path.write_text(head + "\n".join(lines) + "\n")


def encode_args(bitrate):
    return ["-c:v", "h264_videotoolbox", "-b:v", bitrate, "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]


def cmd_render(folder, args):
    work, out = folder / "work", folder / "export"
    out.mkdir(exist_ok=True)
    data = json.loads((work / "subs.json").read_text())
    cues, offset = data["cues"], data["offset"]
    if not any(c.get("en") or c.get("zh") for c in cues):
        sys.exit("subs.json has no cleaned en/zh text yet. Clean it first (see the gd-video skill).")

    gw, gh, dur = probe(folder / "ipad.mov")
    fw, fh, _ = probe(folder / "face.mov")
    gw, gx = detect_side_bars(folder / "ipad.mov", dur)
    game_v = f"[0:v]crop={gw}:{gh}:{gx}:0,fps=60"
    if args.test:
        dur = min(dur, args.test)

    write_srt(cues, out / "en.srt", ["en"])
    write_srt(cues, out / "zh.srt", ["zh"])
    write_srt(cues, out / "bilingual.srt", ["zh", "en"])

    # Facecam aligned to the ipad timeline
    if offset >= 0:
        face_v = f"[1:v]trim=start={offset},setpts=PTS-STARTPTS,fps=60"
        face_a = f"[1:a]atrim=start={offset},asetpts=PTS-STARTPTS"
    else:
        face_v = f"[1:v]tpad=start_duration={-offset}:start_mode=clone,fps=60"
        face_a = f"[1:a]adelay={int(-offset * 1000)}:all=1"
    audio = (f"[0:a]volume={GAME_VOLUME}[ga];{face_a},volume={VOICE_VOLUME}[va];"
             f"[ga][va]amix=inputs=2:duration=first:normalize=0,loudnorm=I={LOUDNESS}:TP=-1.5:LRA=11[a]")
    inputs = ["-i", str(folder / "ipad.mov"), "-i", str(folder / "face.mov")]

    if args.only in (None, "horizontal"):
        pw = int(gw * PIP_WIDTH) // 2 * 2
        vf = (f"{game_v}[g];{face_v},scale={pw}:-2,"
              f"pad=iw+{2 * PIP_BORDER}:ih+{2 * PIP_BORDER}:{PIP_BORDER}:{PIP_BORDER}:white[f];"
              f"[g][f]overlay=W-w-{PIP_MARGIN}:{PIP_TOP}:eof_action=repeat[v]")
        if args.burn_horizontal:
            write_srt(cues, work / "h.srt", args.subs.split(","))
            vf = vf[:-3] + "[v0];[v0]subtitles=h.srt:force_style='FontName=PingFang SC,FontSize=18,Outline=2'[v]"
        run([FFMPEG, "-v", "warning", "-stats", "-y", *inputs, "-filter_complex", f"{vf};{audio}",
             "-map", "[v]", "-map", "[a]", "-t", str(dur), *encode_args("16M"), str(out / "horizontal.mp4")],
            cwd=work)

    if args.only in (None, "vertical"):
        face_h = round(V_W * fh / fw / 2) * 2
        game_h = round(V_W * gh / gw / 2) * 2
        write_ass(cues, work / "v.ass", args.subs.split(","), face_h + game_h + SUB_GAP)
        vf = (f"color=c={V_BG}:s={V_W}x{V_H}:r=60:d={dur}[bg];"
              f"{face_v},scale={V_W}:{face_h}[f];{game_v},scale={V_W}:{game_h}[g];"
              f"[bg][f]overlay=0:0:eof_action=repeat[b1];[b1][g]overlay=0:{face_h}:eof_action=repeat,"
              f"subtitles=v.ass[v]")
        run([FFMPEG, "-v", "warning", "-stats", "-y", *inputs, "-filter_complex", f"{vf};{audio}",
             "-map", "[v]", "-map", "[a]", "-t", str(dur), *encode_args("12M"), str(out / "vertical.mp4")],
            cwd=work)

    print(f"Done: {out}", file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("prep", help="sync + transcribe")
    pp.add_argument("folder")
    pp.add_argument("--offset", type=float, help="manual sync: seconds into face.mov matching ipad.mov t=0")
    pp.add_argument("--lang", help="force speech language, e.g. en or zh (default: auto)")
    pr = sub.add_parser("render", help="render both videos")
    pr.add_argument("folder")
    pr.add_argument("--subs", default="zh,en", help="burned-in subtitle languages for vertical: zh,en | en | zh")
    pr.add_argument("--only", choices=["horizontal", "vertical"])
    pr.add_argument("--burn-horizontal", action="store_true", help="also burn subtitles into the horizontal video")
    pr.add_argument("--test", type=float, help="render only the first N seconds (quick check)")
    args = p.parse_args()
    folder = Path(os.path.expanduser(args.folder)).resolve()
    {"prep": cmd_prep, "render": cmd_render}[args.cmd](folder, args)


if __name__ == "__main__":
    main()
