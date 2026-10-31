from gdvideo.transcribe import glossary_terms, split_cues


def words(*items):
    return [{"words": [{"word": w, "start": s, "end": e} for w, s, e in items]}]


def test_split_cues_on_sentence_end_and_offset():
    segs = words((" Hello", 1.0, 1.4), (" there.", 1.5, 2.0), (" Next", 2.1, 2.5), (" one", 2.6, 3.0))
    cues = split_cues(segs, offset=1.0)
    assert cues == [
        {"start": 0.0, "end": 1.0, "src": "Hello there."},
        {"start": 1.1, "end": 2.0, "src": "Next one"},
    ]


def test_split_cues_on_pause():
    segs = words((" one", 0.0, 0.5), (" two", 2.0, 2.5))
    assert [c["src"] for c in split_cues(segs, 0)] == ["one", "two"]


def test_split_cues_drops_speech_before_video_start():
    segs = words((" early.", 0.0, 0.5), (" later", 2.0, 2.5))
    assert [c["src"] for c in split_cues(segs, offset=1.0)] == ["later"]


def test_glossary_terms_only_from_term_sections(tmp_path):
    path = tmp_path / "glossary.md"
    path.write_text(
        "# Glossary\n\n## Levels\n\n- Electro-Ban adventures → Electroman Adventures\n"
        "- ElectraModadventures → Electroman Adventures\n\n"
        "## Game terms\n\n- orb\n- straightfire -> straight fly\n\n"
        "## Cleanup rules\n\n- Remove filler\n"
    )
    assert glossary_terms(path) == ["Electroman Adventures", "orb", "straight fly"]


def test_glossary_terms_missing_file(tmp_path):
    assert glossary_terms(tmp_path / "missing.md") == []
