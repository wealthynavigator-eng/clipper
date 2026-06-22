import tempfile

from config import Settings
from watermarker import build_watermark_filter


class TestBuildWatermarkFilter:
    def test_no_path_returns_none(self):
        s = Settings(watermark_path="")
        assert build_watermark_filter(s) is None

    def test_nonexistent_path_returns_none(self):
        s = Settings(watermark_path="/nonexistent/logo.png")
        assert build_watermark_filter(s) is None

    def test_valid_path_returns_filter_string(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name)
            result = build_watermark_filter(s, output_width=1080)
            assert result is not None
            assert "[1:v]scale=" in result
            assert "[wm]" in result
            assert "[vid][wm]overlay=" in result
            assert "out" in result

    def test_opacity_less_than_one_adds_channel_mixer(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name, watermark_opacity=0.5)
            result = build_watermark_filter(s, output_width=1080)
            assert "colorchannelmixer=aa=0.5" in result

    def test_opacity_of_one_no_channel_mixer(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name, watermark_opacity=1.0)
            result = build_watermark_filter(s, output_width=1080)
            assert "colorchannelmixer" not in result

    def test_position_mapping(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name, watermark_position="top-left")
            result = build_watermark_filter(s, output_width=1080)
            assert "10:10" in result

    def test_output_width_affects_scale(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name, watermark_scale=0.2)
            r1 = build_watermark_filter(s, output_width=1080)
            r2 = build_watermark_filter(s, output_width=1920)
            assert r1 != r2

    def test_custom_input_idx(self):
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            s = Settings(watermark_path=f.name)
            result = build_watermark_filter(s, output_width=1080, input_idx=2)
            assert "[2:v]scale=" in result
