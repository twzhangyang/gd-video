import os

from gdvideo.pack import pack, parse_post_md
from gdvideo.post import format_post

DATA = {
    "level": "Electroman Adventures",
    "youtube": {"title": "Electroman Adventures guide", "description": "How to beat it.\n\nSecond paragraph.",
                "tags": ["geometry dash", "electroman"], "chapters": []},
    "douyin": {"title": "电人冒险攻略", "caption": "冲！", "hashtags": ["几何冲刺"]},
    "tiktok": {"caption": "Too easy?", "hashtags": ["geometrydash"]},
}


def session(tmp_path, *exports):
    """A session folder with the two recordings, post.md and the given export files (each holding its own name)."""
    (tmp_path / "2026-11-17 21-07-00.mov").write_text("horizontal")
    (tmp_path / "2026-11-17 21-07-02-vertical.mov").write_text("vertical")
    (tmp_path / "post.md").write_text(format_post(DATA, duration=171))
    export = tmp_path / "export"
    export.mkdir()
    for name in exports:
        (export / name).write_text(name)
    return export


def test_parse_post_md_reads_format_post_output():
    sections = parse_post_md(format_post(DATA, duration=171))
    blocks = {h.split()[0]: b for h, b in sections.items()}
    assert blocks["YouTube"] == ["Electroman Adventures guide", "How to beat it.\n\nSecond paragraph.",
                                 "geometry dash, electroman"]
    assert blocks["抖音"] == ["电人冒险攻略", "冲！\n#几何冲刺"]
    assert blocks["TikTok"] == ["Too easy?\n#geometrydash"]


def test_pack_links_files_writes_texts_and_reports_missing(tmp_path, capsys):
    export = session(tmp_path, "cover-horizontal.jpg", "en.srt", "zh.srt", "douyin.mp4")
    post_md = tmp_path / "post.md"
    post_md.write_text(post_md.read_text().replace("Too easy?", "Edited by hand"))

    pack(tmp_path)

    out = export / "pack"
    assert sorted(p.name for p in out.iterdir()) == ["douyin", "tiktok", "youtube"]
    yt = out / "youtube"
    assert sorted(p.name for p in yt.iterdir()) == ["captions-en.srt", "captions-zh.srt", "cover.jpg",
                                                    "post.txt", "video.mov"]
    # YouTube gets the horizontal recording itself, hard linked (no copy, no re-encode)
    assert os.stat(yt / "video.mov").st_ino == os.stat(tmp_path / "2026-11-17 21-07-00.mov").st_ino
    assert (yt / "post.txt").read_text() == ("[Title]\nElectroman Adventures guide\n\n"
                                             "[Description]\nHow to beat it.\n\nSecond paragraph.\n\n"
                                             "[Tags]\ngeometry dash, electroman\n")
    assert (out / "douyin" / "video.mp4").read_text() == "douyin.mp4"
    assert (out / "tiktok" / "post.txt").read_text() == "[Caption]\nEdited by hand\n#geometrydash\n"
    err = capsys.readouterr().err
    assert "gdvideo render <folder> --only tiktok" in err and "cover-vertical.jpg" in err


def test_pack_rebuilds_from_scratch(tmp_path):
    export = session(tmp_path, "tiktok.mp4", "douyin.mp4", "cover-vertical.jpg")
    pack(tmp_path)
    (export / "tiktok.mp4").unlink()
    pack(tmp_path)
    assert not (export / "pack" / "tiktok" / "video.mp4").exists()
    assert (export / "pack" / "douyin" / "cover.jpg").read_text() == "cover-vertical.jpg"
