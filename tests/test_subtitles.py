from gdvideo.subtitles import ass_time, is_cleaned, srt_time, write_ass, write_srt

CUES = [
    {"start": 0.81, "end": 3.19, "en": "Hello!", "zh": "大家好！"},
    {"start": 3.19, "end": 7.21, "en": "Electroman Adventures.", "zh": ""},
]


def test_srt_time():
    assert srt_time(0) == "00:00:00,000"
    assert srt_time(3723.456) == "01:02:03,456"


def test_ass_time():
    assert ass_time(0.81) == "0:00:00.81"
    assert ass_time(3723.45) == "1:02:03.45"


def test_is_cleaned():
    assert is_cleaned({"cues": CUES})
    assert not is_cleaned({"cues": [{"start": 0, "end": 1, "src": "raw"}]})


def test_write_srt_bilingual_skips_empty_lines(tmp_path):
    path = tmp_path / "bilingual.srt"
    write_srt(CUES, path, ["zh", "en"])
    assert path.read_text() == (
        "1\n00:00:00,810 --> 00:00:03,190\n大家好！\nHello!\n\n"
        "2\n00:00:03,190 --> 00:00:07,210\nElectroman Adventures.\n"
    )


def test_write_srt_drops_cues_without_text(tmp_path):
    path = tmp_path / "zh.srt"
    write_srt(CUES, path, ["zh"])
    assert path.read_text().count("-->") == 1


def test_write_ass_positions_and_languages(tmp_path):
    path = tmp_path / "v.ass"
    write_ass(CUES, path, ["zh", "en"], top=1510)
    events = [l for l in path.read_text().splitlines() if l.startswith("Dialogue:")]
    assert len(events) == 2
    assert r"{\pos(540,1510)}大家好！\N{\fs52" in events[0]


def test_write_ass_none_has_no_events(tmp_path):
    path = tmp_path / "v.ass"
    write_ass(CUES, path, ["none"], top=1510)
    assert "Dialogue:" not in path.read_text()


def test_starts_reads_new_and_old_subs_json():
    from gdvideo.subtitles import starts
    assert starts({"ipad_start": 11.0, "face_start": 0.0}) == (11.0, 0.0)
    assert starts({"offset": 1.093}) == (0, 1.093)                 # older files: auto-sync offset
    assert starts({"offset": -10.9, "start": 10.9}) == (10.9, 0.0)
