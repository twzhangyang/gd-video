"""render: subs.json + recordings -> horizontal.mp4, vertical-<langs>.mp4 and SRT files."""
import json
import re
import subprocess
import sys

from gdvideo.config import (FFMPEG, GAME_VOLUME, LOUDNESS, PIP_BORDER, PIP_MARGIN, PIP_TOP, PIP_WIDTH, SUB_FONT,
                            SUB_GAP, SUB_GAP_EN, TRUE_PEAK, V_BG, V_H, V_W, VOICE_VOLUME)
from gdvideo.media import detect_side_bars, encode_args, probe, recording, run
from gdvideo.subtitles import is_cleaned, starts, write_ass, write_srt


def output_duration(game_dur, face_dur, ipad_start, face_start):
    """The video runs while both recordings do: it ends when the shorter one (after its start) ends."""
    return min(game_dur - ipad_start, face_dur - face_start)


def vertical_sizes(game_w, game_h, face_w, face_h):
    """Heights of the facecam (top) and the game (below it) in the 1080-wide vertical layout."""
    return round(V_W * face_h / face_w / 2) * 2, round(V_W * game_h / game_w / 2) * 2


def loudness(inputs, mix, dur):
    """Integrated loudness (LUFS) of the audio mix, measured before rendering so one fixed gain can be applied."""
    err = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-vn", *inputs, "-filter_complex", f"{mix},ebur128",
                          "-t", str(dur), "-f", "null", "-"], capture_output=True, text=True, check=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def render(folder, subs="zh,en", only=None, burn_horizontal=False, test=None):
    work, out = folder / "work", folder / "export"
    work.mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)
    data = json.loads((folder / "subs.json").read_text())
    cues = data["cues"]
    ipad_start, face_start = starts(data)
    if not is_cleaned(data):
        sys.exit(f"{folder / 'subs.json'} has no en/zh text. Run: gdvideo clean <folder> --force")

    game, face = recording(folder, "ipad"), recording(folder, "face")
    gw, gh, dur = probe(game)
    fw, fh, face_dur = probe(face)
    gw, gx = detect_side_bars(game, dur)
    dur = output_duration(dur, face_dur, ipad_start, face_start)
    game_v = f"[0:v]crop={gw}:{gh}:{gx}:0,fps=60"
    suffix = ""
    if test:
        dur = min(dur, test)
        suffix = "-test"  # never overwrite the full videos with a test clip

    write_srt(cues, out / "en.srt", ["en"])
    write_srt(cues, out / "zh.srt", ["zh"])
    write_srt(cues, out / "bilingual.srt", ["zh", "en"])

    # Facecam aligned to the ipad timeline
    if face_start >= 0:
        face_v = f"[1:v]trim=start={face_start},setpts=PTS-STARTPTS,fps=60"
        face_a = f"[1:a]atrim=start={face_start},asetpts=PTS-STARTPTS"
    else:
        face_v = f"[1:v]tpad=start_duration={-face_start}:start_mode=clone,fps=60"
        face_a = f"[1:a]adelay={int(-face_start * 1000)}:all=1"
    inputs = ["-ss", str(ipad_start), "-i", str(game), "-i", str(face)]
    # One gain for the whole video, then a peak limiter. A single-pass loudnorm would act as an automatic gain
    # control and turn up the pauses between words, and with them the game sound the facecam mic picks up.
    mix = (f"[0:a]volume={GAME_VOLUME}[ga];{face_a},volume={VOICE_VOLUME}[va];"
           f"[ga][va]amix=inputs=2:duration=first:normalize=0")
    gain = LOUDNESS - loudness(inputs, mix, dur)
    audio = f"{mix},volume={gain:.2f}dB,alimiter=limit={10 ** (TRUE_PEAK / 20):.3f}:level=0[a]"

    if only in (None, "horizontal"):
        pw = int(gw * PIP_WIDTH) // 2 * 2
        vf = (f"{game_v}[g];{face_v},scale={pw}:-2,"
              f"pad=iw+{2 * PIP_BORDER}:ih+{2 * PIP_BORDER}:{PIP_BORDER}:{PIP_BORDER}:white[f];"
              f"[g][f]overlay=W-w-{PIP_MARGIN}:{PIP_TOP}:eof_action=repeat[v]")
        if burn_horizontal:
            write_srt(cues, work / "h.srt", subs.split(","))
            vf = vf[:-3] + f"[v0];[v0]subtitles=h.srt:force_style='FontName={SUB_FONT},FontSize=18,Outline=2'[v]"
        run([FFMPEG, "-v", "warning", "-stats", "-y", *inputs, "-filter_complex", f"{vf};{audio}",
             "-map", "[v]", "-map", "[a]", "-t", str(dur), *encode_args("16M"), str(out / f"horizontal{suffix}.mp4")],
            cwd=work)

    if only in (None, "vertical"):
        face_h, game_h = vertical_sizes(gw, gh, fw, fh)
        write_ass(cues, work / "v.ass", subs.split(","), face_h + game_h + (SUB_GAP_EN if subs == "en" else SUB_GAP))
        vf = (f"color=c={V_BG}:s={V_W}x{V_H}:r=60:d={dur}[bg];"
              f"{face_v},scale={V_W}:{face_h}[f];{game_v},scale={V_W}:{game_h}[g];"
              f"[bg][f]overlay=0:0:eof_action=repeat[b1];[b1][g]overlay=0:{face_h}:eof_action=repeat,"
              f"subtitles=v.ass[v]")
        run([FFMPEG, "-v", "warning", "-stats", "-y", *inputs, "-filter_complex", f"{vf};{audio}",
             "-map", "[v]", "-map", "[a]", "-t", str(dur), *encode_args("12M"), str(out / f"vertical-{subs.replace(',', '-')}{suffix}.mp4")],
            cwd=work)

    print(f"Done: {out}", file=sys.stderr)
