import pytest

from gdvideo.media import mode, recording


def test_recording_finds_any_extension_and_case(tmp_path):
    (tmp_path / "ipad.MP4").write_text("")
    (tmp_path / "face.mov").write_text("")
    (tmp_path / "ipad.wav").write_text("")  # not a video
    assert recording(tmp_path, "ipad").name == "ipad.MP4"
    assert recording(tmp_path, "face").name == "face.mov"


def test_recording_missing_or_ambiguous_exits(tmp_path):
    with pytest.raises(SystemExit, match="No ipad recording"):
        recording(tmp_path, "ipad")
    (tmp_path / "ipad.mov").write_text("")
    (tmp_path / "ipad.mp4").write_text("")
    with pytest.raises(SystemExit, match="More than one"):
        recording(tmp_path, "ipad")


def test_mode_single_when_there_is_one_video_recording(tmp_path):
    assert mode(tmp_path) == "dual"            # empty folder: the ipad + face errors explain what is missing
    (tmp_path / "video.MOV").write_text("")
    assert mode(tmp_path) == "single"
    (tmp_path / "face.mov").write_text("")
    with pytest.raises(SystemExit, match="both"):
        mode(tmp_path)
