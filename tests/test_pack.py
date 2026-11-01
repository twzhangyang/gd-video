import os

from gdvideo.pack import pack, parse_post_md
from gdvideo.post import format_post

DATA = {
    "level": "Electroman Adventures",
    "youtube": {"title": "Electroman Adventures guide", "description": "How to beat it.\n\nSecond paragraph.",
                "tags": ["geometry dash", "electroman"], "chapters": []},
    "douyin": {"title": "电人冒险攻略", "caption": "冲！", "hashtags": ["几何冲刺"]},
    "tiktok": {"caption": "Too easy?", "hashtags": ["geometrydash"]},
    "instagram": {"caption": "Coin route", "hashtags": ["gd"]},
}


def test_parse_post_md_reads_format_post_output():
    sections = parse_post_md(format_post(DATA, duration=171))
    blocks = {h.split()[0]: b for h, b in sections.items()}
    assert blocks["YouTube"] == ["Electroman Adventures guide", "How to beat it.\n\nSecond paragraph.",
                                 "geometry dash, electroman"]
    assert blocks["抖音"] == ["电人冒险攻略", "冲！\n#几何冲刺"]
    assert blocks["TikTok"] == ["Too easy?\n#geometrydash"]


def test_pack_links_files_writes_texts_and_reports_missing(tmp_path, capsys):
    (tmp_path / "post.md").write_text(format_post(DATA, duration=171).replace("Too easy?", "Edited by hand"))
    export = tmp_path / "export"
    export.mkdir()
    for name in ("horizontal.mp4", "cover-horizontal.jpg", "en.srt", "zh.srt", "vertical-zh-en.mp4"):
        (export / name).write_text(name)

    pack(tmp_path)

    yt = export / "pack" / "youtube"
    assert sorted(p.name for p in yt.iterdir()) == ["captions-en.srt", "captions-zh.srt", "cover.jpg",
                                                    "post.txt", "video.mp4"]
    assert os.stat(yt / "video.mp4").st_ino == os.stat(export / "horizontal.mp4").st_ino  # hard link, no copy
    assert (yt / "post.txt").read_text() == ("[Title]\nElectroman Adventures guide\n\n"
                                             "[Description]\nHow to beat it.\n\nSecond paragraph.\n\n"
                                             "[Tags]\ngeometry dash, electroman\n")
    assert (export / "pack" / "tiktok" / "post.txt").read_text() == "[Caption]\nEdited by hand\n#geometrydash\n"
    err = capsys.readouterr().err
    assert "vertical-en.mp4" in err and "cover-vertical.jpg" in err


def test_pack_puts_cover_at_start_of_douyin_and_tiktok_only(tmp_path, monkeypatch):
    (tmp_path / "post.md").write_text(format_post(DATA, duration=171))
    export = tmp_path / "export"
    export.mkdir()
    for name in ("horizontal.mp4", "cover-horizontal.jpg", "en.srt", "zh.srt", "vertical-zh-en.mp4",
                 "vertical-en.mp4", "cover-vertical.jpg"):
        (export / name).write_text(name)

    def fake_intro(video, cover):
        out = video.with_name(f"{video.stem}-cover.mp4")
        out.write_text("cover + " + video.read_text())
        return out
    monkeypatch.setattr("gdvideo.pack.with_cover_intro", fake_intro)

    pack(tmp_path)

    out = export / "pack"
    assert (out / "douyin" / "video.mp4").read_text() == "cover + vertical-zh-en.mp4"
    assert (out / "tiktok" / "video.mp4").read_text() == "cover + vertical-en.mp4"
    assert (out / "instagram" / "video.mp4").read_text() == "vertical-en.mp4"
    assert (out / "youtube" / "video.mp4").read_text() == "horizontal.mp4"
