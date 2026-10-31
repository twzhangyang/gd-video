from gdvideo.post import fit_tags, fix_chapters, format_post, hashtags

CHAPTERS = [{"start": 0, "title": "Intro"}, {"start": 22, "title": "First coin"}, {"start": 105, "title": "Practice"}]


def test_fix_chapters_keeps_valid_set():
    assert fix_chapters(CHAPTERS, duration=171) == CHAPTERS


def test_fix_chapters_drops_too_close_and_too_short():
    chapters = [{"start": 0, "title": "Intro"}, {"start": 9, "title": "Coins"}, {"start": 20, "title": "Orb"},
                {"start": 36, "title": "Portal"}, {"start": 165, "title": "Outro"}]
    assert [c["title"] for c in fix_chapters(chapters, duration=171)] == ["Intro", "Orb", "Portal"]


def test_fix_chapters_moves_first_to_zero():
    chapters = [{"start": 3, "title": "Intro"}, *CHAPTERS[1:]]
    assert fix_chapters(chapters, 171)[0]["start"] == 0


def test_fix_chapters_needs_three():
    assert fix_chapters(CHAPTERS[:2], 171) == []


def test_fit_tags_respects_total_length():
    tags = ["geometry dash", "#electroman adventures", "x" * 480]
    assert fit_tags(tags) == ["geometry dash", "electroman adventures"]


def test_hashtags_dedupes_strips_and_limits():
    assert hashtags(["#geometrydash", "geometry dash", "geometrydash", "gd"], limit=2) == "#geometrydash #gd"


def test_format_post_includes_every_platform_and_chapters():
    data = {
        "level": "Electroman Adventures",
        "youtube": {"title": "Electroman Adventures guide", "description": "How to beat it.",
                    "tags": ["geometry dash"], "chapters": CHAPTERS},
        "douyin": {"title": "电人冒险攻略", "caption": "冲！", "hashtags": ["几何冲刺"]},
        "tiktok": {"caption": "Too easy?", "hashtags": ["geometrydash"]},
        "instagram": {"caption": "Coin route", "hashtags": ["gd"]},
    }
    text = format_post(data, duration=171)
    for heading in ("## YouTube", "## 抖音", "## TikTok", "## Instagram Reels"):
        assert heading in text
    assert "How to beat it.\n\n0:00 Intro\n0:22 First coin\n1:45 Practice" in text
    assert "冲！\n#几何冲刺" in text
