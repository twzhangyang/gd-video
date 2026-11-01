"""prep: sync the recordings and transcribe the voice into raw subtitle cues."""
import json
import re
import sys

from gdvideo.config import GLOSSARY, GLOSSARY_TERM_SECTIONS, MAX_CHARS, MAX_DURATION, PAUSE_SPLIT, WHISPER_MODEL
from gdvideo.media import extract_wav, recording
from gdvideo.sync import find_offset


def glossary_terms(path=GLOSSARY):
    """Correct spellings from glossary.md: '- wrong → right' or '- term' bullets in the term sections."""
    if not path.exists():
        return []
    terms, section = [], None
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        m = re.match(r"\s*-\s+(?:\[.\]\s+)?(.+)", line)
        if m and section in GLOSSARY_TERM_SECTIONS:
            terms.append(re.split(r"\s*(?:→|->)\s*", m.group(1))[-1].strip())
    return list(dict.fromkeys(terms))


def split_cues(segments, offset):
    """Whisper word timestamps -> short cues on the ipad timeline."""
    words = [w for s in segments for w in s.get("words", [])]
    cues, cur = [], []

    def flush():
        if cur:
            text = "".join(w["word"] for w in cur).strip()
            cues.append({"start": round(max(cur[0]["start"] - offset, 0), 2),
                         "end": round(cur[-1]["end"] - offset, 2), "src": text})
            cur.clear()

    for w in words:
        if cur and (w["start"] - cur[-1]["end"] > PAUSE_SPLIT
                    or len("".join(x["word"] for x in cur + [w]).strip()) > MAX_CHARS
                    or w["end"] - cur[0]["start"] > MAX_DURATION):
            flush()
        cur.append(w)
        if re.search(r"[.!?。！？]$", w["word"].strip()):
            flush()
    flush()
    return [c for c in cues if c["end"] > 0]


def prep(folder, ipad_start=0.0, face_start=0.0, auto_sync=False, lang=None):
    """Video t=0 is ipad_start seconds into the ipad recording and face_start into the face one (default: both
    start together). auto_sync measures face_start from the audio instead."""
    work = folder / "work"
    work.mkdir(exist_ok=True)
    print("Extracting audio...", file=sys.stderr)
    game = extract_wav(recording(folder, "ipad"), work / "ipad.wav")
    voice = extract_wav(recording(folder, "face"), work / "face.wav")

    if auto_sync:
        print("Syncing...", file=sys.stderr)
        offset, agree, total = find_offset(game, voice)
        print(f"Offset {offset:+.3f}s ({agree}/{total} windows agree)", file=sys.stderr)
        if agree < max(2, total / 2):
            sys.exit("Sync is unreliable. Set the starts by hand: --ipad-start SECONDS / --face-start SECONDS.")
        face_start = ipad_start + offset  # negative: facecam started later, its first frame is held
    print(f"Video starts at ipad {ipad_start:.2f}s, face {face_start:.2f}s", file=sys.stderr)

    print("Transcribing...", file=sys.stderr)
    import mlx_whisper
    terms = glossary_terms()
    result = mlx_whisper.transcribe(
        str(work / "face.wav"), path_or_hf_repo=WHISPER_MODEL, word_timestamps=True,
        condition_on_previous_text=False, language=lang,
        initial_prompt=("Geometry Dash. " + ", ".join(terms)) if terms else "Geometry Dash.")

    cues = split_cues(result["segments"], face_start)  # cue times are on the output video's timeline
    data = {"ipad_start": round(ipad_start, 3), "face_start": round(face_start, 3), "language": result["language"],
            "cues": cues}
    (work / "subs.raw.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"Wrote {work / 'subs.raw.json'}: {len(cues)} cues, language {result['language']}", file=sys.stderr)
