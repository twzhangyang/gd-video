from gdvideo.single import bitrate, output_size


def test_output_size_scales_burned_videos_down_to_1080():
    assert output_size(3840, 2160, scale=True) == (1920, 1080)
    assert output_size(2184, 1640, scale=True) == (1438, 1080)   # even width
    assert output_size(3840, 2160, scale=False) == (3840, 2160)  # YouTube keeps the source size
    assert output_size(1280, 720, scale=True) == (1280, 720)     # never scaled up


def test_bitrate_by_height():
    assert (bitrate(2160), bitrate(1640), bitrate(1080)) == ("45M", "16M", "12M")
