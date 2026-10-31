"""clean: Claude cleans and translates the raw cues into subs.json."""
import json
import sys

from gdvideo.claude import ask_json
from gdvideo.config import GLOSSARY

CLEAN_SCHEMA = {
    "type": "object",
    "properties": {
        "cues": {"type": "array", "items": {
            "type": "object",
            "properties": {"start": {"type": "number"}, "end": {"type": "number"},
                           "en": {"type": "string"}, "zh": {"type": "string"}},
            "required": ["start", "end", "en", "zh"], "additionalProperties": False}},
        "review": {"type": "array", "items": {
            "type": "object",
            "properties": {"start": {"type": "number"}, "text": {"type": "string"}, "note": {"type": "string"}},
            "required": ["start", "text", "note"], "additionalProperties": False}},
    },
    "required": ["cues", "review"],
    "additionalProperties": False,
}

CLEAN_PROMPT = """You are cleaning auto-generated subtitles for a Geometry Dash gameplay video. The speaker is
commentating while playing. Below are the raw Whisper cues (times in seconds on the video timeline,
speech language: {language}) and the channel's subtitle glossary.

Return cleaned cues with both English (`en`) and Simplified Chinese (`zh`) text:
- Fix mishearings using the glossary (`wrong → right`) and the gameplay context; use its zh translations for game terms
- Drop filler-only cues ("okay okay okay", "whatever", "um") and filler inside lines
- Rejoin sentences Whisper split badly, then re-split so each cue holds one idea and `en` is at most 45 characters
- Keep timings inside the original cue boundaries: you may merge or split cues, but never move speech in time.
  Cues must be in order and must not overlap
- Keep the speaker's voice and reactions; don't make it formal
- `zh`: natural, casual Simplified Chinese; level names stay in English
- If the speech is Chinese, `zh` is the cleaned source and `en` the translation

In `review`, list only the lines where you guessed (unclear words, possible mishearings), with the cue start time,
the cleaned text and a short note on what you were unsure about. Leave it empty if nothing was unclear.

<glossary>
{glossary}
</glossary>

<raw_cues>
{cues}
</raw_cues>"""


def tidy_cues(cues):
    """Sort, round, remove overlaps and drop empty or zero-length cues."""
    cues = sorted(cues, key=lambda c: c["start"])
    for c in cues:
        c["start"], c["end"] = round(c["start"], 2), round(c["end"], 2)
    for a, b in zip(cues, cues[1:]):
        a["end"] = min(a["end"], b["start"])
    return [c for c in cues if c["end"] > c["start"] and (c["en"] or c["zh"])]


def clean(folder, force=False):
    raw_path = folder / "work" / "subs.raw.json"
    if not raw_path.exists():
        sys.exit(f"{raw_path} not found. Run prep first (or use: gdvideo all <folder>).")
    raw = json.loads(raw_path.read_text())
    subs = folder / "subs.json"
    if subs.exists() and not force:
        sys.exit(f"{subs} already exists. Use --force to replace it with a fresh cleanup.")

    cues_in = [{"start": c["start"], "end": c["end"], "text": c["src"]} for c in raw["cues"]]
    prompt = CLEAN_PROMPT.format(language=raw["language"], glossary=GLOSSARY.read_text() if GLOSSARY.exists() else "",
                                 cues=json.dumps(cues_in, ensure_ascii=False, indent=1))
    result = ask_json(prompt, CLEAN_SCHEMA, f"Cleaning {len(raw['cues'])} cues")

    cues = tidy_cues(result["cues"])
    subs.write_text(json.dumps({"offset": raw["offset"], "language": raw["language"], "cues": cues},
                               ensure_ascii=False, indent=1))
    print(f"Wrote {subs}: {len(cues)} cues", file=sys.stderr)

    lines = [f"{int(r['start']) // 60}:{int(r['start']) % 60:02d}  {r['text']}  ({r['note']})" for r in result["review"]]
    (folder / "work" / "review.txt").write_text("\n".join(lines) + "\n")
    if lines:
        print("\nCheck these lines (edit subs.json, then run render again):", file=sys.stderr)
        for line in lines:
            print("  " + line, file=sys.stderr)
