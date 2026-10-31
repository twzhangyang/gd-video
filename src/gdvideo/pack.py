"""pack: one upload folder per platform with the right video, cover, captions and text -> export/pack/<platform>/."""
import os
import re
import shutil
import subprocess
import sys

# Per platform: files to put in its folder (name in pack <- file in export/), and the text blocks of its
# post.md section in order (each saved as <name>.txt).
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
    },
    "tiktok": {
        "heading": "TikTok",
        "files": {"video.mp4": "vertical-en.mp4", "cover.jpg": "cover-vertical.jpg"},
        "texts": ["caption"],
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
                link_or_copy(export / export_name, dest / pack_name)
            else:
                missing.setdefault(export_name, []).append(name)

        blocks = find_section(sections, spec["heading"])
        if blocks is None or len(blocks) != len(spec["texts"]):
            sys.exit(f"post.md: the '{spec['heading']}' section should have {len(spec['texts'])} code block(s) "
                     f"({', '.join(spec['texts'])}). Fix it or rerun: gdvideo post <folder> --force")
        for field, block in zip(spec["texts"], blocks):
            (dest / f"{field}.txt").write_text(block + "\n")

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
