"""Command line: gdvideo {all,prep,clean,post,render,cover,pack} <folder>."""
import argparse
import os
import sys
from pathlib import Path

from gdvideo.clean import clean
from gdvideo.cover import cover
from gdvideo.pack import pack
from gdvideo.post import post
from gdvideo.render import render
from gdvideo.transcribe import prep

ALL_SUBS = ["zh,en", "en"]  # `all` renders these verticals: 抖音 (zh,en), TikTok/Instagram (en)

DESCRIPTION = """Geometry Dash video pipeline: sync iPad gameplay + facecam, transcribe, render two layouts.

Folder layout (one folder per video):
    <folder>/ipad.mov   gameplay (game audio only)
    <folder>/face.mov   facecam (voice only)

Commands:
    all    <folder>   prep + clean + post + render + cover + pack, skipping prep/clean/post/cover if done
    prep   <folder>   sync + transcribe -> <folder>/work/subs.raw.json
    clean  <folder>   Claude cleans + translates the raw cues -> <folder>/subs.json
    post   <folder>   Claude writes titles, descriptions and hashtags -> <folder>/post.md
    render <folder>   subs.json -> <folder>/export/{horizontal,vertical-<langs>}.mp4 + .srt files
    cover  <folder>   thumbnails with logo + title -> <folder>/export/cover-{horizontal,vertical}.jpg
    pack   <folder>   one upload folder per platform (video, cover, captions, text) -> <folder>/export/pack/

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

    # Render what pack needs: horizontal once, then one vertical per subtitle variant
    variants = args.subs or ALL_SUBS
    if args.only != "vertical":
        render(folder, variants[0], "horizontal", args.burn_horizontal, args.test)
    if args.only != "horizontal":
        for subs in variants:
            render(folder, subs, "vertical", False, args.test)
    if args.test:
        print("Skipping cover and pack: --test renders only a clip", file=sys.stderr)
        return

    formats = [f for f in ([args.only] if args.only else ["horizontal", "vertical"])
               if args.force or not (folder / "export" / f"cover-{f}.jpg").exists()]
    if formats:
        cover(folder, formats=formats)
    else:
        print("Skipping cover: export/cover-*.jpg exist (gdvideo cover <folder> to remake)", file=sys.stderr)
    pack(folder)


def run_render(folder, args):
    render(folder, args.subs, args.only, args.burn_horizontal, args.test)


def main():
    p = argparse.ArgumentParser(prog="gdvideo", description=DESCRIPTION,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_prep_args(sp):
        sp.add_argument("--offset", type=float, help="manual sync: seconds into face.mov matching ipad.mov t=0")
        sp.add_argument("--lang", help="force speech language, e.g. en or zh (default: auto)")

    def add_render_args(sp, many=False):
        if many:
            sp.add_argument("--subs", action="append", help="vertical subtitle variant to render, repeatable "
                            "(default: zh,en and en, the two that pack uses)")
        else:
            sp.add_argument("--subs", default="zh,en", help="burned-in subtitle languages for vertical: zh,en | en | zh | none; output is vertical-<langs>.mp4, e.g. vertical-zh-en.mp4")
        sp.add_argument("--only", choices=["horizontal", "vertical"])
        sp.add_argument("--burn-horizontal", action="store_true", help="also burn subtitles into the horizontal video")
        sp.add_argument("--test", type=float, help="render only the first N seconds to *-test.mp4 (quick check)")

    def add_post_args(sp):
        sp.add_argument("--level", help="level name, if the transcript doesn't make it clear")
        sp.add_argument("--notes", help="extra context for the posting text, e.g. \"first try at all 3 coins\"")

    pa = sub.add_parser("all", help="prep + clean + post + render + cover + pack")
    pa.add_argument("folder")
    pa.add_argument("--force", action="store_true", help="redo prep, clean, post and cover even if their output exists")
    add_prep_args(pa)
    add_post_args(pa)
    add_render_args(pa, many=True)
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
    pk = sub.add_parser("pack", help="make one upload folder per platform")
    pk.add_argument("folder")
    pk.add_argument("--open", action="store_true", help="open the pack folder in Finder")
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
        "pack": lambda: pack(folder, args.open),
        "cover": lambda: cover(folder, args.text, args.at, [args.only] if args.only else ["horizontal", "vertical"]),
    }
    commands[args.cmd]()
