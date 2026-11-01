"""post: Claude writes titles, descriptions and hashtags for each platform -> <folder>/post.md."""
import json
import sys

from gdvideo.claude import ask_json
from gdvideo.config import CHANNEL, IG_MAX_HASHTAGS, YT_MAX_TAG_CHARS, YT_MAX_TITLE
from gdvideo.media import probe, recording
from gdvideo.subtitles import starts

_TEXT = {"type": "string"}
_LIST = {"type": "array", "items": _TEXT}


def _obj(**props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


POST_SCHEMA = _obj(
    level=_TEXT,
    youtube=_obj(title=_TEXT, description=_TEXT, tags=_LIST,
                 chapters={"type": "array", "items": _obj(start={"type": "number"}, title=_TEXT)}),
    douyin=_obj(title=_TEXT, caption=_TEXT, hashtags=_LIST),
    tiktok=_obj(caption=_TEXT, hashtags=_LIST),
    instagram=_obj(caption=_TEXT, hashtags=_LIST),
)

POST_PROMPT = """Write the posting text for a Geometry Dash gameplay video with live commentary. The same session is
posted as a horizontal video on YouTube and as vertical short videos on 抖音 (Douyin), TikTok and Instagram Reels.
Base everything on what actually happens in the transcript below; don't invent achievements.

Video length: {duration}. {level_hint}{notes}

Return:
- `level`: the Geometry Dash level name played
- `youtube`: `title` (at most {yt_title} characters, level name included, searchable), `description` (2-4 short
  paragraphs: what the video covers, key tips from the commentary, a call to like/subscribe; no hashtags and no
  chapter list, those are added separately), `tags` (10-15 search keywords, lowercase, no #), `chapters` (3-8 key
  moments with start time in seconds; the first must start at 0, each at least 10 s apart, titles in English;
  return an empty list if the video is too short for that)
- `douyin`: `title` (short, punchy Chinese title), `caption` (1-2 casual Chinese sentences), `hashtags` (5-8, Chinese
  and English mixed, e.g. 几何冲刺, 游戏, geometrydash)
- `tiktok`: `caption` (1-2 short English sentences with a hook), `hashtags` (4-6)
- `instagram`: `caption` (1-3 short English sentences), `hashtags` (5-10)
Write hashtags without the # sign. Follow the channel notes.

<channel>
{channel}
</channel>

<transcript>
{transcript}
</transcript>"""


def mmss(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def fix_chapters(chapters, duration):
    """Make chapters meet YouTube's rules: first at 0:00, each at least 10 s long, at least 3 in total.

    Chapters that start too soon after the previous one are dropped; returns [] if fewer than 3 remain.
    """
    kept = []
    for c in sorted(chapters, key=lambda c: c["start"]):
        if not kept:
            kept.append({**c, "start": 0})
        elif c["start"] - kept[-1]["start"] >= 10:
            kept.append(c)
    while kept and duration - kept[-1]["start"] < 10:
        kept.pop()
    return kept if len(kept) >= 3 else []


def fit_tags(tags, limit=YT_MAX_TAG_CHARS):
    """Keep tags in order until YouTube's total length limit."""
    kept, total = [], 0
    for tag in tags:
        tag = tag.strip().lstrip("#")
        if tag and total + len(tag) + (1 if kept else 0) <= limit:
            total += len(tag) + (1 if kept else 0)
            kept.append(tag)
    return kept


def hashtags(tags, limit=None):
    tags = [t.strip().lstrip("#").replace(" ", "") for t in tags if t.strip()]
    return " ".join("#" + t for t in list(dict.fromkeys(tags))[:limit])


def format_post(data, duration):
    yt, dy, tt, ig = data["youtube"], data["douyin"], data["tiktok"], data["instagram"]
    description = yt["description"].strip()
    chapters = fix_chapters(yt["chapters"], duration)
    if chapters:
        description += "\n\n" + "\n".join(f"{mmss(c['start'])} {c['title']}" for c in chapters)
    return f"""# Posting: {data['level']}

## YouTube (horizontal.mp4, captions: en.srt + zh.srt)

**Title**

```
{yt['title'][:YT_MAX_TITLE]}
```

**Description**

```
{description}
```

**Tags** (paste into the Tags field)

```
{", ".join(fit_tags(yt['tags']))}
```

## 抖音 (vertical-zh-en.mp4)

**标题**

```
{dy['title']}
```

**描述**

```
{dy['caption']}
{hashtags(dy['hashtags'])}
```

## TikTok (vertical-en.mp4)

```
{tt['caption']}
{hashtags(tt['hashtags'])}
```

## Instagram Reels (vertical-en.mp4)

```
{ig['caption']}
{hashtags(ig['hashtags'], IG_MAX_HASHTAGS)}
```
"""


def post(folder, level=None, notes=None, force=False):
    subs_path = folder / "subs.json"
    if not subs_path.exists():
        sys.exit(f"{subs_path} not found. Run prep and clean first.")
    out = folder / "post.md"
    if out.exists() and not force:
        sys.exit(f"{out} already exists. Use --force to write a new one.")

    subs = json.loads(subs_path.read_text())
    cues = subs["cues"]
    duration = probe(recording(folder, "ipad"))[2] - starts(subs)[0]  # output length: the iPad part used
    transcript = "\n".join(f"[{mmss(c['start'])}] {c['en'] or c['zh']}" for c in cues)
    prompt = POST_PROMPT.format(
        duration=mmss(duration),
        level_hint=f"The level is {level}. " if level else "",
        notes=f"Extra notes from the creator: {notes}" if notes else "",
        yt_title=YT_MAX_TITLE,
        channel=CHANNEL.read_text() if CHANNEL.exists() else "",
        transcript=transcript)
    data = ask_json(prompt, POST_SCHEMA, "Writing posting text")

    (folder / "work").mkdir(exist_ok=True)
    (folder / "work" / "post.json").write_text(json.dumps(data, ensure_ascii=False, indent=1))
    out.write_text(format_post(data, duration))
    print(f"Wrote {out}", file=sys.stderr)
