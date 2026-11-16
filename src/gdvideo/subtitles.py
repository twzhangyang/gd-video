"""Subtitle file writers: SRT for platforms and 剪映, ASS for the burned-in vertical subtitles."""
from gdvideo.config import SUB_EN_SIZE, SUB_END_STRIP, SUB_FONT, SUB_ZH_SIZE, V_H, V_W


def is_cleaned(data):
    return any(c.get("en") or c.get("zh") for c in data["cues"])


def line(cue, field):
    """A cue's text in one language, without the full stop / comma at the end."""
    return (cue.get(field) or "").strip().rstrip(SUB_END_STRIP).rstrip()


def srt_time(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def ass_time(t):
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def write_srt(cues, path, fields, shift=0.0):
    """shift: seconds added to every time, for videos that start with the cover."""
    blocks = []
    for c in cues:
        text = "\n".join(line(c, f) for f in fields if line(c, f))
        if text:
            blocks.append(f"{len(blocks) + 1}\n{srt_time(c['start'] + shift)} --> {srt_time(c['end'] + shift)}\n{text}\n")
    path.write_text("\n".join(blocks))


def write_ass(cues, path, fields, top=None, bottom=None, size=(V_W, V_H), zh_size=SUB_ZH_SIZE, en_size=SUB_EN_SIZE):
    """Burned-in subtitles: Chinese (white) above English (yellow), centred on a canvas of `size`.

    top: y of the top of the first line (vertical layout, below the game). bottom: px from the bottom edge of the
    canvas to the bottom of the last line instead (single recording), so one and two lines end at the same place.
    """
    width, height = size
    place = rf"{{\an2\pos({width // 2},{height - bottom})}}" if bottom is not None else rf"{{\pos({width // 2},{top})}}"
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{SUB_FONT},{zh_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,8,60,60,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for c in cues:
        parts = []
        if "zh" in fields and line(c, "zh"):
            parts.append(line(c, "zh"))
        if "en" in fields and line(c, "en"):
            parts.append(rf"{{\fs{en_size}\c&H00FFFF&}}" + line(c, "en") + r"{\r}")
        if parts:
            lines.append(f"Dialogue: 0,{ass_time(c['start'])},{ass_time(c['end'])},Sub,,0,0,0,,"
                         + place + r"\N".join(parts))
    path.write_text(head + "\n".join(lines) + "\n")


def starts(data):
    """(ipad_start, face_start): seconds into each recording at video t=0. Reads older subs.json files too."""
    if "ipad_start" in data:
        return data["ipad_start"], data["face_start"]
    start = data.get("start", 0)
    return start, data["offset"] + start
