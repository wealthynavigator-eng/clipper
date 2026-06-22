import os
import subprocess
import tempfile
from unittest.mock import patch

from config import settings
from cutter import _escape_drawtext, slice_video


class TestEscapeDrawtext:
    def test_escapes_backslash(self) -> None:
        assert _escape_drawtext("a\\b") == "a\\\\b"

    def test_escapes_colon(self) -> None:
        assert _escape_drawtext("a:b") == "a\\:b"

    def test_escapes_both(self) -> None:
        assert _escape_drawtext("a\\:b") == "a\\\\\\:b"

    def test_no_special_chars(self) -> None:
        assert _escape_drawtext("hello world") == "hello world"

    def test_empty_string(self) -> None:
        assert _escape_drawtext("") == ""

    def test_unicode_preserved(self) -> None:
        assert _escape_drawtext("don\u2019t stop") == "don\u2019t stop"


class TestSliceVideoCommandArgs:
    """Verify ffmpeg command lists handle paths with spaces and Unicode chars."""

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_video_path_with_spaces_is_single_arg(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        video_path = "/path/to/my video file.mp4"
        clips = [{"start": 10, "end": 20, "hook_text": "test"}]
        saved = _save_settings()

        try:
            _set_minimal_settings()
            slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        cmd = mock_run.call_args[0][0]
        i = cmd.index("-i")
        assert cmd[i + 1] == video_path

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_bgm_path_with_spaces_is_single_arg(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        bgm_path = "/path/to/my background music.mp3"
        video_path = "/tmp/video.mp4"
        clips = [{"start": 0, "end": 10, "hook_text": "test"}]
        saved = _save_settings()

        try:
            _set_minimal_settings()
            settings.bgm_path = bgm_path
            with patch("os.path.exists", return_value=True):
                slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        cmds = [call[0][0] for call in mock_run.call_args_list]
        ffmpeg_calls = [c for c in cmds if c[0] == "ffmpeg"]
        assert len(ffmpeg_calls) >= 1
        cmd = ffmpeg_calls[0]
        inputs = []
        for i, arg in enumerate(cmd):
            if arg == "-i":
                inputs.append(cmd[i + 1])
        assert video_path in inputs
        assert bgm_path in inputs

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_path_with_unicode_apostrophe(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        video_path = "/path/to/Don\u2019t Stop Me Now.mp4"
        clips = [{"start": 10, "end": 20, "hook_text": "test"}]
        saved = _save_settings()

        try:
            _set_minimal_settings()
            slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        cmd = mock_run.call_args[0][0]
        i = cmd.index("-i")
        assert cmd[i + 1] == video_path

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_output_path_with_spaces(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        video_path = "/tmp/video.mp4"
        clips = [{"start": 10, "end": 20, "hook_text": "test"}]
        saved = _save_settings()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = os.path.join(tmpdir, "my output dir")
                settings.output_dir = output_dir
                settings.thumbnail = False
                settings.bgm_path = ""
                settings.watermark_path = ""
                settings.face_tracking = False
                settings.hook_overlay = False

                results = slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        assert len(results) == 1
        assert "my output dir" in results[0]

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_output_path_is_last_arg_before_y(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        video_path = "/tmp/video.mp4"
        clips = [{"start": 10, "end": 20, "hook_text": "test"}]
        saved = _save_settings()

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                settings.output_dir = tmpdir
                settings.thumbnail = False
                settings.bgm_path = ""
                settings.watermark_path = ""
                settings.face_tracking = False
                settings.hook_overlay = False

                slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        cmd = mock_run.call_args[0][0]
        y_idx = cmd.index("-y")
        output_path = cmd[y_idx - 1]
        assert output_path.endswith(".mp4")

    @patch("cutter._detect_video_size", return_value=(1920, 1080))
    @patch("cutter.subprocess.run")
    def test_path_with_trailing_space(self, mock_run, mock_detect_size):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        video_path = "/path/to/video .mp4"
        clips = [{"start": 10, "end": 20, "hook_text": "test"}]
        saved = _save_settings()

        try:
            _set_minimal_settings()
            slice_video(video_path, clips)
        finally:
            _restore_settings(saved)

        cmd = mock_run.call_args[0][0]
        i = cmd.index("-i")
        assert cmd[i + 1] == video_path


def _save_settings() -> dict:
    return {
        k: getattr(settings, k)
        for k in ["output_dir", "thumbnail", "bgm_path", "watermark_path",
                   "face_tracking", "hook_overlay", "hook_duration",
                   "subtitle_style", "fade_duration", "audio_normalize",
                   "parallel_workers"]
    }


def _set_minimal_settings() -> None:
    settings.output_dir = tempfile.mkdtemp()
    settings.thumbnail = False
    settings.bgm_path = ""
    settings.watermark_path = ""
    settings.face_tracking = False
    settings.hook_overlay = True
    settings.hook_duration = 3.0
    settings.subtitle_style = "default"
    settings.fade_duration = 0.5
    settings.audio_normalize = False
    settings.parallel_workers = 1


def _restore_settings(saved: dict) -> None:
    for k, v in saved.items():
        setattr(settings, k, v)
