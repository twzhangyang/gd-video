"""Command line: gdvideo {all,prep,clean,render} <folder>."""
import argparse
import os
import sys
from pathlib import Path

from gdvideo.clean import clean
from gdvideo.render import render
from gdvideo.transcribe import prep

DESCRIPTION = """Geometry Dash video pipeline: sync iPad gameplay + facecam, transcribe, render two layouts.

Folder layout (one folder per video):
    <folder>/ipad.mov   gameplay (game audio only)
    <folder>/face.mov   facecam (voice only)

Commands:
    all    <folder>   prep + clean + render, skipping steps whose output already exists
    prep   <folder>   sync + transcribe -> <folder>/work/subs.raw.json
    clean  <folder>   Claude cleans + translates the raw cues -> <folder>/subs.json
    render <folder>   subs.json -> <folder>/export/{horizontal,vertical}.mp4 + .srt files

work/ and export/ are disposable; the cleaned subs.json lives next to the recordings.
clean needs Anthropic API credentials (ANTHROPIC_API_KEY).
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
        sp.add_argument("--subs", default="zh,en", help="burned-in subtitle languages for vertical: zh,en | en | zh | none")
        sp.add_argument("--only", choices=["horizontal", "vertical"])
        sp.add_argument("--burn-horizontal", action="store_true", help="also burn subtitles into the horizontal video")
        sp.add_argument("--test", type=float, help="render only the first N seconds (quick check)")

    pa = sub.add_parser("all", help="prep + clean + render")
    pa.add_argument("folder")
    pa.add_argument("--force", action="store_true", help="redo prep and clean even if their output exists")
    add_prep_args(pa)
    add_render_args(pa)
    pp = sub.add_parser("prep", help="sync + transcribe")
    pp.add_argument("folder")
    add_prep_args(pp)
    pc = sub.add_parser("clean", help="clean + translate subtitles with Claude")
    pc.add_argument("folder")
    pc.add_argument("--force", action="store_true", help="replace an existing subs.json")
    pr = sub.add_parser("render", help="render both videos")
    pr.add_argument("folder")
    add_render_args(pr)
    args = p.parse_args()
    folder = Path(os.path.expanduser(args.folder)).resolve()

    commands = {
        "all": lambda: run_all(folder, args),
        "prep": lambda: prep(folder, args.offset, args.lang),
        "clean": lambda: clean(folder, args.force),
        "render": lambda: run_render(folder, args),
    }
    commands[args.cmd]()
