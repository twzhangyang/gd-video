from pathlib import Path

from PIL import Image, ImageFont

from gdvideo.config import COVER_FONT
from gdvideo.cover import compose, parse_time, wrap_title


def test_parse_time():
    assert parse_time("1:05") == 65
    assert parse_time("45") == 45
    assert parse_time("1:00:30") == 3630


def test_wrap_title_one_line_when_it_fits():
    font = ImageFont.truetype(str(COVER_FONT), 40)
    assert wrap_title("Electroman Adventures", font, 2000) == ["Electroman Adventures"]


def test_wrap_title_splits_into_two_balanced_lines():
    font = ImageFont.truetype(str(COVER_FONT), 40)
    width = font.getlength("Electroman Adventures") * 0.7
    assert wrap_title("Electroman Adventures", font, width) == ["Electroman", "Adventures"]


def test_wrap_title_none_when_a_word_is_too_long():
    font = ImageFont.truetype(str(COVER_FONT), 40)
    assert wrap_title("Electroman", font, 50) is None


def test_compose_without_logo_keeps_size_and_scales_down(tmp_path):
    frame = Image.new("RGB", (2184, 1640), "purple")
    out = compose(frame, "Electroman Adventures", logo_path=Path(tmp_path / "missing.png"))
    assert out.size == (1920, 1442)
    assert out.mode == "RGB"


def test_compose_trims_transparent_logo_margins(tmp_path):
    logo = Image.new("RGBA", (400, 400))
    logo.paste((0, 120, 255, 255), (100, 150, 300, 200))  # 200x50 logo in the middle of empty space
    logo.save(tmp_path / "logo.png")
    frame = Image.new("RGB", (1920, 1440), "black")
    out = compose(frame, "X", logo_path=tmp_path / "logo.png")
    # trimmed logo is scaled to COVER_LOGO_WIDTH of the cover; its blue reaches the left margin at 3%
    assert out.getpixel((round(1920 * 0.03) + 5, round(1440 * 0.22) + 5))[2] > 200


def test_compose_vertical_keeps_1080x1920(tmp_path):
    frame = Image.new("RGB", (1080, 1920), "purple")
    out = compose(frame, "Electroman Adventures", logo_path=tmp_path / "missing.png", layout="vertical")
    assert out.size == (1080, 1920)


def test_fit_title_prefers_one_line():
    from gdvideo.cover import fit_title
    font, lines = fit_title("Electroman Adventures", max_width=1500, max_size=130)
    assert lines == ["Electroman Adventures"] and font.size > 90


def test_output_duration_ends_with_the_shorter_recording():
    from gdvideo.render import output_duration
    assert output_duration(200, 150, 0, 0) == 150       # facecam stopped first: cut the iPad
    assert output_duration(171.6, 300, 0, 1.09) == 171.6  # iPad stopped first
    assert output_duration(200, 190, 11, 0) == 189       # both trimmed at the start
    assert output_duration(200, 150, 0, -5) == 155      # auto-sync: facecam started 5 s later (held frame)
