"""prep: line up the vertical recording with the horizontal one and transcribe the voice into raw cues."""
import json
import re
import sys

from gdvideo.config import (GLOSSARY, GLOSSARY_TERM_SECTIONS, MAX_CHARS, MAX_DURATION, PAUSE_SPLIT, SR, SYNC_WINDOW,
                            WHISPER_MODEL)
from gdvideo.media import audio_tracks, extract_wav, recordings
from gdvideo.sync import find_offset, sync_window


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
    """Whisper word timestamps -> short cues, `offset` seconds earlier."""
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


def measure_vertical_start(horizontal, vertical, work):
    """Seconds into the vertical recording at horizontal t=0. Both recordings carry the same audio (OBS records the
    same sources on both canvases), so it is found by matching their first audio tracks."""
    if not audio_tracks(vertical):
        sys.exit(f"{vertical.name} has no audio, so it can't be lined up. Set it by hand: --vertical-start SECONDS "
                 "(seconds into the vertical recording when the horizontal one starts; 0 if they started together)")
    ref = extract_wav(horizontal, work / "horizontal-sync.wav")
    other = extract_wav(vertical, work / "vertical-sync.wav")
    window = sync_window(min(len(ref), len(other)) / SR, SYNC_WINDOW)
    offset, agree, total = find_offset(ref, other, window)
    print(f"Vertical recording offset {offset:+.3f}s ({agree}/{total} windows agree)", file=sys.stderr)
    if agree < max(2, total / 2):
        sys.exit("Lining up the vertical recording is unreliable. Set it by hand: --vertical-start SECONDS")
    return offset


def prep(folder, vertical_start=None, lang=None):
    """Transcribe the horizontal recording; cue times are on its timeline. vertical_start (seconds into the vertical
    recording at horizontal t=0) is measured from the audio unless given."""
    work = folder / "work"
    work.mkdir(exist_ok=True)
    horizontal, vertical = recordings(folder)
    print("Extracting audio...", file=sys.stderr)
    tracks = audio_tracks(horizontal)
    if not tracks:
        sys.exit(f"{horizontal} has no audio track to transcribe.")
    if tracks > 1:
        # OBS can record the mic on its own track; the voice-only track (the last one) gives cleaner subtitles
        print(f"Using audio track {tracks} of {tracks} as the voice", file=sys.stderr)
    extract_wav(horizontal, work / "voice.wav", tracks - 1)

    if vertical_start is None:
        print("Lining up the vertical recording...", file=sys.stderr)
        vertical_start = measure_vertical_start(horizontal, vertical, work)

    print("Transcribing...", file=sys.stderr)
    import mlx_whisper
    terms = glossary_terms()
    result = mlx_whisper.transcribe(
        str(work / "voice.wav"), path_or_hf_repo=WHISPER_MODEL, word_timestamps=True,
        condition_on_previous_text=False, language=lang,
        initial_prompt=("Geometry Dash. " + ", ".join(terms)) if terms else "Geometry Dash.")

    cues = split_cues(result["segments"], 0)
    data = {"vertical_start": round(vertical_start, 3), "language": result["language"], "cues": cues}
    (work / "subs.raw.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"Wrote {work / 'subs.raw.json'}: {len(cues)} cues, language {result['language']}", file=sys.stderr)
