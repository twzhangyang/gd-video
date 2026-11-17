"""Command line: gdvideo {all,prep,clean,post,cover,render,pack} <folder>."""
import argparse
import os
import sys
from pathlib import Path

from gdvideo.clean import clean
from gdvideo.cover import cover
from gdvideo.pack import pack
from gdvideo.post import post
from gdvideo.render import TARGETS, render
from gdvideo.transcribe import prep

DESCRIPTION = """Geometry Dash video pipeline: two OBS recordings of one session -> subtitles, covers, posting text and a
video per platform.

Folder layout (one folder per session), the two recordings straight from OBS:
    <folder>/<date>.mov            horizontal recording (game + facecam)  -> YouTube as is, with en/zh captions
    <folder>/<date>-vertical.mov   vertical recording (Aitum Vertical; any video with "vertical" in its name)
                                   -> export/tiktok.mp4 (en burned in), douyin.mp4 (zh + en), both starting with
                                      the cover
    .mov, .mp4 or .m4v

Commands:
    all    <folder>   prep + clean + post + cover + render + pack, skipping prep/clean/post/cover if done
    prep   <folder>   line up the vertical recording + transcribe -> work/subs.raw.json
    clean  <folder>   Claude cleans + translates the raw cues -> <folder>/subs.json
    post   <folder>   Claude writes titles, descriptions and hashtags -> <folder>/post.md
    cover  <folder>   thumbnails with logo + title -> <folder>/export/cover-{horizontal,vertical}.jpg
    render <folder>   subs.json -> <folder>/export/{tiktok,douyin}.mp4 + {en,zh,bilingual}.srt
    pack   <folder>   one upload folder per platform (video, cover, captions, text) -> <folder>/export/pack/

work/ and export/ are disposable; subs.json and post.md live next to the recordings.
clean and post need Anthropic API credentials (ANTHROPIC_API_KEY).
"""


def run_all(folder, args):
    if (folder / "work" / "subs.raw.json").exists() and not args.force:
        print("Skipping prep: work/subs.raw.json exists", file=sys.stderr)
    else:
        prep(folder, args.vertical_start, args.lang)
    if (folder / "subs.json").exists() and not args.force:
        print("Skipping clean: subs.json exists", file=sys.stderr)
    else:
        clean(folder, args.force)
    if (folder / "post.md").exists() and not args.force:
        print("Skipping post: post.md exists", file=sys.stderr)
    else:
        post(folder, args.level, args.notes, args.force)
    # The vertical videos start with the cover, so the covers come before the render (and are needed for --test too)
    formats = [f for f in ("horizontal", "vertical") if args.force or not (folder / "export" / f"cover-{f}.jpg").exists()]
    if formats:
        cover(folder, formats=formats)
    else:
        print("Skipping cover: export/cover-*.jpg exist (gdvideo cover <folder> to remake)", file=sys.stderr)
    render(folder, args.only, args.test)
    if args.test:
        print("Skipping pack: --test renders only a clip", file=sys.stderr)
    else:
        pack(folder)


def main():
    p = argparse.ArgumentParser(prog="gdvideo", description=DESCRIPTION,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_prep_args(sp):
        sp.add_argument("--vertical-start", type=float, help="seconds into the vertical recording when the "
                        "horizontal one starts, negative if it started later (default: measured from the audio)")
        sp.add_argument("--lang", help="force speech language, e.g. en or zh (default: auto)")

    def add_render_args(sp):
        sp.add_argument("--only", choices=list(TARGETS), help="render one video: " + " | ".join(TARGETS))
        sp.add_argument("--test", type=float, help="render only the first N seconds to *-test.mp4 (quick check)")

    def add_post_args(sp):
        sp.add_argument("--level", help="level name, if the transcript doesn't make it clear")
        sp.add_argument("--notes", help="extra context for the posting text, e.g. \"first try at all 3 coins\"")

    pa = sub.add_parser("all", help="prep + clean + post + cover + render + pack")
    pa.add_argument("folder")
    pa.add_argument("--force", action="store_true", help="redo prep, clean, post and cover even if their output exists")
    add_prep_args(pa)
    add_post_args(pa)
    add_render_args(pa)
    pp = sub.add_parser("prep", help="line up the recordings + transcribe")
    pp.add_argument("folder")
    add_prep_args(pp)
    pc = sub.add_parser("clean", help="clean + translate subtitles with Claude")
    pc.add_argument("folder")
    pc.add_argument("--force", action="store_true", help="replace an existing subs.json")
    po = sub.add_parser("post", help="write titles, descriptions and hashtags with Claude")
    po.add_argument("folder")
    po.add_argument("--force", action="store_true", help="replace an existing post.md")
    add_post_args(po)
    pv = sub.add_parser("cover", help="make cover images for the horizontal and vertical videos")
    pv.add_argument("folder")
    pv.add_argument("--text", help="cover title (default: the level name from gdvideo post)")
    pv.add_argument("--at", help="time of the frame to use, e.g. 1:05 (default: 30%% into the video)")
    pv.add_argument("--only", choices=["horizontal", "vertical"], help="make only one of the two covers")
    pr = sub.add_parser("render", help="render the TikTok and 抖音 videos and the caption files")
    pr.add_argument("folder")
    add_render_args(pr)
    pk = sub.add_parser("pack", help="make one upload folder per platform")
    pk.add_argument("folder")
    pk.add_argument("--open", action="store_true", help="open the pack folder in Finder")
    args = p.parse_args()
    folder = Path(os.path.expanduser(args.folder)).resolve()

    commands = {
        "all": lambda: run_all(folder, args),
        "prep": lambda: prep(folder, args.vertical_start, args.lang),
        "clean": lambda: clean(folder, args.force),
        "post": lambda: post(folder, args.level, args.notes, args.force),
        "cover": lambda: cover(folder, args.text, args.at, [args.only] if args.only else ["horizontal", "vertical"]),
        "render": lambda: render(folder, args.only, args.test),
        "pack": lambda: pack(folder, args.open),
    }
    commands[args.cmd]()
