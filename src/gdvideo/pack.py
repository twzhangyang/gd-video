"""pack: one upload folder per platform with the right video, cover, captions and post.txt -> export/pack/<platform>/."""
import os
import re
import shutil
import subprocess
import sys

from gdvideo.config import COVER_INTRO, FFMPEG, FFPROBE
from gdvideo.media import encode_args, probe, run

# Per platform: files to put in its folder (name in pack <- file in export/), the text blocks of its post.md
# section in order (together saved as post.txt), and whether the cover is put at the start of the video
# (抖音 and TikTok take the cover from a video frame; YouTube and Instagram take an uploaded image).
PLATFORMS = {
    "youtube": {
        "heading": "YouTube",
        "files": {"video.mp4": "horizontal.mp4", "cover.jpg": "cover-horizontal.jpg",
                  "captions-en.srt": "en.srt", "captions-zh.srt": "zh.srt"},
        "texts": ["title", "description", "tags"],
    },
    "douyin": {
        "heading": "抖音",
        "files": {"video.mp4": "vertical-zh-en.mp4", "cover.jpg": "cover-vertical.jpg"},
        "texts": ["title", "caption"],
        "cover_intro": True,
    },
    "tiktok": {
        "heading": "TikTok",
        "files": {"video.mp4": "vertical-en.mp4", "cover.jpg": "cover-vertical.jpg"},
        "texts": ["caption"],
        "cover_intro": True,
    },
    "instagram": {
        "heading": "Instagram",
        "files": {"video.mp4": "vertical-en.mp4", "cover.jpg": "cover-vertical.jpg"},
        "texts": ["caption"],
    },
}

# How to make each export file if it's missing
MAKE = {
    "horizontal.mp4": "gdvideo render <folder> --only horizontal",
    "vertical-zh-en.mp4": "gdvideo render <folder> --only vertical --subs zh,en",
    "vertical-en.mp4": "gdvideo render <folder> --only vertical --subs en",
    "cover-horizontal.jpg": "gdvideo cover <folder> --only horizontal",
    "cover-vertical.jpg": "gdvideo cover <folder> --only vertical",
    "en.srt": "gdvideo render <folder> --only horizontal",
    "zh.srt": "gdvideo render <folder> --only horizontal",
}


def parse_post_md(text):
    """post.md -> {heading: [code block, ...]} for each '## ' section, so hand edits to post.md are kept."""
    sections = {}
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        heading = part.split("\n", 1)[0].strip()
        sections[heading] = [b.strip("\n") for b in re.findall(r"^```[^\n]*\n(.*?)^```", part, flags=re.M | re.S)]
    return sections


def find_section(sections, heading):
    return next((blocks for h, blocks in sections.items() if h.startswith(heading)), None)


def link_or_copy(src, dst):
    """Hard link so big videos take no extra space; copy if linking isn't possible."""
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def with_cover_intro(video, cover):
    """export/<video>-cover.mp4: the cover for COVER_INTRO seconds, then the video. Remade only when the video or
    the cover is newer, since it re-encodes the whole video."""
    out = video.with_name(f"{video.stem}-cover.mp4")
    if out.exists() and out.stat().st_mtime > max(video.stat().st_mtime, cover.stat().st_mtime):
        return out
    w, h, _ = probe(video)
    rate = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
                           "stream=sample_rate", "-of", "csv=p=0", str(video)],
                          capture_output=True, text=True, check=True).stdout.strip() or "48000"
    vf = (f"[0:v]scale={w}:{h}:out_range=tv,setsar=1,fps=60,format=yuv420p,trim=duration={COVER_INTRO}[cv];"
          f"anullsrc=r={rate}:cl=stereo,atrim=duration={COVER_INTRO}[ca];"
          f"[1:v]setsar=1[v];[1:a]aresample={rate}[a];[cv][ca][v][a]concat=n=2:v=1:a=1[ov][oa]")
    run([FFMPEG, "-v", "error", "-stats", "-y", "-loop", "1", "-i", str(cover), "-i", str(video),
         "-filter_complex", vf, "-map", "[ov]", "-map", "[oa]", *encode_args("12M"), str(out)])
    return out


def post_txt(fields, blocks):
    """All text for one platform in one file, each field under a [Label] line."""
    return "\n\n".join(f"[{field.capitalize()}]\n{block}" for field, block in zip(fields, blocks)) + "\n"


def pack(folder, open_folder=False):
    post_md = folder / "post.md"
    if not post_md.exists():
        sys.exit(f"{post_md} not found. Run: gdvideo post <folder>")
    sections = parse_post_md(post_md.read_text())
    export = folder / "export"
    out = export / "pack"
    if out.exists():
        shutil.rmtree(out)  # generated folder; rebuilt from export/ and post.md every time

    missing = {}
    for name, spec in PLATFORMS.items():
        dest = out / name
        dest.mkdir(parents=True)
        for pack_name, export_name in spec["files"].items():
            if (export / export_name).exists():
                src = export / export_name
                cover = export / spec["files"]["cover.jpg"]
                if pack_name == "video.mp4" and spec.get("cover_intro") and cover.exists():
                    src = with_cover_intro(src, cover)
                link_or_copy(src, dest / pack_name)
            else:
                missing.setdefault(export_name, []).append(name)

        blocks = find_section(sections, spec["heading"])
        if blocks is None or len(blocks) != len(spec["texts"]):
            sys.exit(f"post.md: the '{spec['heading']}' section should have {len(spec['texts'])} code block(s) "
                     f"({', '.join(spec['texts'])}). Fix it or rerun: gdvideo post <folder> --force")
        (dest / "post.txt").write_text(post_txt(spec["texts"], blocks))

    print(f"Packed {out}", file=sys.stderr)
    for name, spec in PLATFORMS.items():
        have = sorted(p.name for p in (out / name).iterdir())
        print(f"  {name:10s} {', '.join(have)}", file=sys.stderr)
    if missing:
        print("\nMissing (make them, then run pack again):", file=sys.stderr)
        for export_name, platforms in missing.items():
            print(f"  {export_name:22s} for {', '.join(platforms):28s} -> {MAKE[export_name]}", file=sys.stderr)
    if open_folder:
        subprocess.run(["open", str(out)])
