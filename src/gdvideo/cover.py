"""cover: thumbnails with the logo, an emoji and the title -> export/cover-horizontal.jpg, cover-vertical.jpg."""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

from gdvideo.config import (COVER_AT, COVER_EMOJI, COVER_FONT, COVER_LAYOUT, COVER_LOGO, COVER_MAX_WIDTH, COVER_TILT,
                            EMOJI_FONT, FFMPEG, V_BG, V_H, V_W)
from gdvideo.media import detect_side_bars, probe, run
from gdvideo.render import vertical_sizes


def parse_time(s):
    """'1:05' or '65' -> 65.0"""
    parts = [float(p) for p in str(s).split(":")]
    return sum(p * 60 ** i for i, p in enumerate(reversed(parts)))


def wrap_title(text, font, max_width):
    """Split the title into at most two lines that fit max_width; None if it doesn't fit."""
    if font.getlength(text) <= max_width:
        return [text]
    words = text.split()
    for i in sorted(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(text) / 2)):
        lines = [" ".join(words[:i]), " ".join(words[i:])]
        if all(font.getlength(line) <= max_width for line in lines):
            return lines
    return None


def fit_title(text, max_width, max_size):
    """Largest font size (and line split) at which the title fits; one line is preferred down to 70% size."""
    for size in range(max_size, round(max_size * 0.7), -2):
        font = ImageFont.truetype(str(COVER_FONT), size)
        if font.getlength(text) <= max_width:
            return font, [text]
    for size in range(max_size, 20, -4):
        font = ImageFont.truetype(str(COVER_FONT), size)
        lines = wrap_title(text, font, max_width)
        if lines:
            return font, lines
    return ImageFont.truetype(str(COVER_FONT), 20), [text]


def emoji_image(emoji, height):
    """Apple Color Emoji only renders at its bitmap size (160 px); draw there and scale."""
    font = ImageFont.truetype(EMOJI_FONT, 160)
    img = Image.new("RGBA", (200, 200))
    ImageDraw.Draw(img).text((100, 100), emoji, font=font, embedded_color=True, anchor="mm")
    img = img.crop(img.getbbox())
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def title_layer(text, max_width, max_size):
    """Emoji + title, white brush lettering with a black outline, on a transparent layer, tilted."""
    font, lines = fit_title(text, max_width, max_size)
    stroke = max(4, font.size // 12)
    line_h = round(font.size * 1.15)
    text_w = round(max(font.getlength(line) for line in lines)) + 2 * stroke
    text_h = line_h * len(lines) + 2 * stroke
    emoji = emoji_image(COVER_EMOJI, round(min(text_h, font.size * 1.9))) if COVER_EMOJI else None
    gap = font.size // 6 if emoji else 0
    emoji_w = emoji.width if emoji else 0

    layer = Image.new("RGBA", (emoji_w + gap + text_w, max(text_h, emoji.height if emoji else 0)))
    if emoji:
        layer.alpha_composite(emoji, (0, (layer.height - emoji.height) // 2))
    draw = ImageDraw.Draw(layer)
    top = (layer.height - text_h) // 2 + stroke
    for i, line in enumerate(lines):
        draw.text((emoji_w + gap + stroke, top + i * line_h), line, font=font, fill="white",
                  stroke_width=stroke, stroke_fill="black")
    return layer.rotate(COVER_TILT, resample=Image.BICUBIC, expand=True)


def compose(frame, title, logo_path=COVER_LOGO, layout="horizontal"):
    pos = COVER_LAYOUT[layout]
    img = frame.convert("RGBA")
    if img.width > COVER_MAX_WIDTH:
        img = img.resize((COVER_MAX_WIDTH, round(img.height * COVER_MAX_WIDTH / img.width)), Image.LANCZOS)
    w, h = img.size

    if logo_path.exists():
        logo = Image.open(logo_path)
        if "A" not in logo.getbands():
            print(f"Warning: {logo_path.name} has no transparent background, so it will show as a box. "
                  "Download it from Canva as PNG with 'Transparent background'.", file=sys.stderr)
        logo = logo.convert("RGBA")
        logo = logo.crop(logo.getchannel("A").getbbox() or (0, 0, *logo.size))  # trim empty margins
        logo_w = round(w * pos["logo_w"])
        if logo.width < logo_w / 2:
            print(f"Warning: {logo_path.name} is only {logo.width} px wide and will look blurry; "
                  f"export it at least {logo_w} px wide.", file=sys.stderr)
        logo = logo.resize((logo_w, round(logo.height * logo_w / logo.width)), Image.LANCZOS)
        img.alpha_composite(logo, (round(w * pos["logo_x"]), round(h * pos["logo_y"])))
    else:
        print(f"No logo at {logo_path}: cover made without it", file=sys.stderr)

    layer = title_layer(title, w * pos["title_w"], round(h * pos["title_size"]))
    y = min(round(h * pos["title_y"]), round(h * pos["title_bottom"]) - layer.height)
    img.alpha_composite(layer, (round(w * pos["title_x"]), y))
    return img.convert("RGB")


def cover_title(folder):
    """Default title: the level name that `gdvideo post` found."""
    post_json = folder / "work" / "post.json"
    if post_json.exists():
        return json.loads(post_json.read_text())["level"]
    sys.exit("No title: pass --text \"...\" or run `gdvideo post` first (the cover uses its level name).")


def frame_time(at, duration):
    return parse_time(at) if at is not None else duration * COVER_AT


def horizontal_frame(folder, at, path):
    video = folder / "export" / "horizontal.mp4"
    if not video.exists():
        sys.exit(f"{video} not found. Render it first: gdvideo render <folder> --only horizontal")
    t = frame_time(at, probe(video)[2])
    run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", str(path)])
    return t


def vertical_frame(folder, at, path):
    """The vertical layout (facecam on top, game below) built from the recordings, without subtitles."""
    subs = folder / "subs.json"
    if not subs.exists():
        sys.exit(f"{subs} not found. Run prep and clean first (the cover needs the sync offset).")
    offset = json.loads(subs.read_text())["offset"]
    gw, gh, dur = probe(folder / "ipad.mov")
    fw, fh, _ = probe(folder / "face.mov")
    gw, gx = detect_side_bars(folder / "ipad.mov", dur)
    face_h, game_h = vertical_sizes(gw, gh, fw, fh)
    t = frame_time(at, dur)
    vf = (f"[1:v]scale={V_W}:{face_h}[f];[0:v]crop={gw}:{gh}:{gx}:0,scale={V_W}:{game_h}[g];"
          f"[f][g]vstack,pad={V_W}:{V_H}:0:0:{V_BG}")
    run([FFMPEG, "-v", "error", "-y", "-ss", str(t), "-i", str(folder / "ipad.mov"),
         "-ss", str(max(t + offset, 0)), "-i", str(folder / "face.mov"),
         "-filter_complex", vf, "-frames:v", "1", str(path)])
    return t


def cover(folder, text=None, at=None, formats=("horizontal", "vertical")):
    title = text or cover_title(folder)
    (folder / "work").mkdir(exist_ok=True)
    (folder / "export").mkdir(exist_ok=True)
    for fmt in formats:
        frame_path = folder / "work" / f"cover-frame-{fmt}.png"
        t = (horizontal_frame if fmt == "horizontal" else vertical_frame)(folder, at, frame_path)
        out = folder / "export" / f"cover-{fmt}.jpg"
        compose(Image.open(frame_path), title, layout=fmt).save(out, quality=90)
        print(f"Wrote {out} (frame at {int(t) // 60}:{int(t) % 60:02d}, title \"{title}\")", file=sys.stderr)
