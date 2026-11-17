import pytest

from gdvideo.media import recordings


def test_recordings_finds_obs_names_any_extension_and_case(tmp_path):
    (tmp_path / "2026-11-17 21-07-00.MOV").write_text("")
    (tmp_path / "2026-11-17 21-07-02-vertical.mov").write_text("")
    (tmp_path / "voice.wav").write_text("")     # not a video
    (tmp_path / "export").mkdir()               # outputs are in subfolders
    horizontal, vertical = recordings(tmp_path)
    assert horizontal.name == "2026-11-17 21-07-00.MOV"
    assert vertical.name == "2026-11-17 21-07-02-vertical.mov"


def test_recordings_plain_names(tmp_path):
    (tmp_path / "horizontal.mp4").write_text("")
    (tmp_path / "Vertical.mp4").write_text("")
    assert [p.name for p in recordings(tmp_path)] == ["horizontal.mp4", "Vertical.mp4"]


def test_recordings_missing_or_ambiguous_exits(tmp_path):
    (tmp_path / "a.mov").write_text("")
    with pytest.raises(SystemExit, match="Found: a.mov"):
        recordings(tmp_path)                    # no vertical recording
    (tmp_path / "a-vertical.mov").write_text("")
    (tmp_path / "b.mov").write_text("")
    with pytest.raises(SystemExit, match="two videos"):
        recordings(tmp_path)                    # two horizontal candidates
