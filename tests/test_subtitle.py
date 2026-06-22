import os
import tempfile

from subtitle import _ass_time, _make_ass, _make_srt_content, _srt_time, write_subtitles

_SEGMENTS = [
    {"start": 0.0, "end": 2.5, "text": "Hello world"},
    {"start": 2.5, "end": 5.0, "text": "This is a test"},
    {"start": 5.0, "end": 8.0, "text": "Of the subtitle system"},
]

_CLIP_START = 2.0
_CLIP_END = 7.0


class TestSrtTime:
    def test_basic(self):
        assert _srt_time(0) == "00:00:00,000"
        assert _srt_time(1.5) == "00:00:01,500"
        assert _srt_time(3661.0) == "01:01:01,000"


class TestAssTime:
    def test_basic(self):
        assert _ass_time(0) == "0:00:00.00"
        assert _ass_time(1.5) == "0:00:01.50"
        assert _ass_time(3661.0) == "1:01:01.00"


class TestMakeSrtContent:
    def test_generates_entries(self):
        content = _make_srt_content(_SEGMENTS, _CLIP_START, _CLIP_END)
        assert "00:00:00,000 --> 00:00:00,500" in content
        assert "Hello world" in content
        assert "This is a test" in content
        assert "Of the subtitle system" in content

    def test_empty_segments(self):
        assert _make_srt_content([], 0, 10) == ""

    def test_none_segments(self):
        assert _make_srt_content(None, 0, 10) == ""
        assert _srt_time(0) == "00:00:00,000"

    def test_clip_outside_range(self):
        segments = [{"start": 100, "end": 110, "text": "far away"}]
        assert _make_srt_content(segments, 0, 10) == ""

    def test_removes_empty_text(self):
        segments = [{"start": 0, "end": 5, "text": "   "}]
        assert _make_srt_content(segments, 0, 10) == ""


class TestMakeAss:
    def test_default_style(self):
        content = _make_ass(_SEGMENTS, _CLIP_START, _CLIP_END, "default")
        assert "[Script Info]" in content
        assert "[V4+ Styles]" in content
        assert "[Events]" in content
        assert "Default" in content
        assert "Hello world" in content

    def test_karaoke_style(self):
        content = _make_ass(_SEGMENTS, _CLIP_START, _CLIP_END, "karaoke")
        assert "\\k" in content

    def test_empty_segments(self):
        content = _make_ass([], 0, 10)
        assert "[Events]" in content

    def test_unknown_style_falls_back(self):
        content = _make_ass(_SEGMENTS, _CLIP_START, _CLIP_END, "nonexistent")
        assert "Default" in content


class TestWriteSubtitles:
    def test_writes_srt_for_default_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_subtitles(_SEGMENTS, 0, 10, os.path.join(tmp, "test"))
            assert path.endswith(".srt")
            assert os.path.exists(path)
            with open(path) as f:
                assert "00:00:00,000" in f.read()

    def test_writes_ass_for_custom_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_subtitles(_SEGMENTS, 0, 10, os.path.join(tmp, "test"), style="mrbeast")
            assert path.endswith(".ass")
            assert os.path.exists(path)
            with open(path) as f:
                assert "[Script Info]" in f.read()

    def test_cleanup_on_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_subtitles(_SEGMENTS, 0, 10, os.path.join(tmp, "test"))
            assert os.path.exists(path)
