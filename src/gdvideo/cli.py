"""Command line: gdvideo {all,prep,clean,render} <folder>."""
import argparse
import os
import sys
from pathlib import Path

from gdvideo.clean import clean
from gdvideo.cover import cover
from gdvideo.post import post
from gdvideo.render import render
from gdvideo.transcribe import prep

DESCRIPTION = """Geometry Dash video pipeline: sync iPad gameplay + facecam, transcribe, render two layouts.

Folder layout (one folder per video):
    <folder>/ipad.mov   gameplay (game audio only)
    <folder>/face.mov   facecam (voice only)

Commands:
    all    <folder>   prep + clean + post + render, skipping steps whose output already exists
    prep   <folder>   sync + transcribe -> <folder>/work/subs.raw.json
    clean  <folder>   Claude cleans + translates the raw cues -> <folder>/subs.json
    post   <folder>   Claude writes titles, descriptions and hashtags -> <folder>/post.md
    render <folder>   subs.json -> <folder>/export/{horizontal,vertical-<langs>}.mp4 + .srt files
    cover  <folder>   thumbnails with logo + title -> <folder>/export/cover-{horizontal,vertical}.jpg

work/ and export/ are disposable; subs.json and post.md live next to the recordings.
clean and post need Anthropic API credentials (ANTHROPIC_API_KEY).
"""


def run_all(folder, args):
    if (folder / "work" / "subs.raw.json").exists() and not args.force:
        print("Skipping prep: work/subs.raw.json exists", file=sys.stderr)
    else:
        prep(folder, args.offset, args.lang)
    if (folder / "subs.json").exists() and not args.force:
        print("Skipping clean: subs.json exists", file=sys.stderr)
    else:
        clean(folder, args.force)
    if (folder / "post.md").exists() and not args.force:
        print("Skipping post: post.md exists", file=sys.stderr)
    else:
        post(folder, args.level, args.notes, args.force)
    run_render(folder, args)


def run_render(folder, args):
    render(folder, args.subs, args.only, args.burn_horizontal, args.test)


def main():
    p = argparse.ArgumentParser(prog="gdvideo", description=DESCRIPTION,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_prep_args(sp):
        sp.add_argument("--offset", type=float, help="manual sync: seconds into face.mov matching ipad.mov t=0")
        sp.add_argument("--lang", help="force speech language, e.g. en or zh (default: auto)")

    def add_render_args(sp):
        sp.add_argument("--subs", default="zh,en", help="burned-in subtitle languages for vertical: zh,en | en | zh | none; output is vertical-<langs>.mp4, e.g. vertical-zh-en.mp4")
        sp.add_argument("--only", choices=["horizontal", "vertical"])
        sp.add_argument("--burn-horizontal", action="store_true", help="also burn subtitles into the horizontal video")
        sp.add_argument("--test", type=float, help="render only the first N seconds to *-test.mp4 (quick check)")

    def add_post_args(sp):
        sp.add_argument("--level", help="level name, if the transcript doesn't make it clear")
        sp.add_argument("--notes", help="extra context for the posting text, e.g. \"first try at all 3 coins\"")

    pa = sub.add_parser("all", help="prep + clean + post + render")
    pa.add_argument("folder")
    pa.add_argument("--force", action="store_true", help="redo prep, clean and post even if their output exists")
    add_prep_args(pa)
    add_post_args(pa)
    add_render_args(pa)
    pp = sub.add_parser("prep", help="sync + transcribe")
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
    pr = sub.add_parser("render", help="render both videos")
    pr.add_argument("folder")
    add_render_args(pr)
    args = p.parse_args()
    folder = Path(os.path.expanduser(args.folder)).resolve()

    commands = {
        "all": lambda: run_all(folder, args),
        "prep": lambda: prep(folder, args.offset, args.lang),
        "clean": lambda: clean(folder, args.force),
        "post": lambda: post(folder, args.level, args.notes, args.force),
        "render": lambda: run_render(folder, args),
        "cover": lambda: cover(folder, args.text, args.at, [args.only] if args.only else ["horizontal", "vertical"]),
    }
    commands[args.cmd]()
