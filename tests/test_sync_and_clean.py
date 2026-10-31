import numpy as np

from gdvideo.clean import tidy_cues
from gdvideo.config import SR
from gdvideo.sync import find_offset


def test_find_offset_recovers_known_shift():
    rng = np.random.default_rng(0)
    game = rng.standard_normal(100 * SR)
    shift = 1.25  # face.mov started 1.25 s before ipad.mov
    voice = np.concatenate([rng.standard_normal(int(shift * SR)), game[:90 * SR] * 0.05])
    voice += rng.standard_normal(len(voice)) * 0.5  # the voice is much louder than the game bleed
    offset, agree, total = find_offset(game, voice)
    assert abs(offset - shift) < 0.01
    assert agree == total


def test_tidy_cues_sorts_removes_overlap_and_empty():
    cues = tidy_cues([
        {"start": 5.0, "end": 6.0, "en": "b", "zh": "乙"},
        {"start": 1.0, "end": 5.5, "en": "a", "zh": "甲"},
        {"start": 7.0, "end": 8.0, "en": "", "zh": ""},
    ])
    assert [(c["start"], c["end"], c["en"]) for c in cues] == [(1.0, 5.0, "a"), (5.0, 6.0, "b")]
