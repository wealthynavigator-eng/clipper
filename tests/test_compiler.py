import os
import subprocess
from unittest.mock import patch

from compiler import _concat_lossless, _xfade_compile, compile_clips


class TestCompileClips:
    @patch("compiler.subprocess.run")
    def test_single_clip_path_with_space(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        clip_path = "/path/to/my clip.mp4"
        result = compile_clips([clip_path], output_path="/tmp/reel.mp4")
        assert result == "/tmp/reel.mp4"
        cmd = mock_run.call_args[0][0]
        i = cmd.index("-i")
        assert cmd[i + 1] == clip_path

    @patch("compiler.subprocess.run")
    def test_single_clip_unicode_apostrophe(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        clip_path = "/path/to/Don\u2019t Stop Me Now.mp4"
        result = compile_clips([clip_path], output_path="/tmp/reel.mp4")
        assert result == "/tmp/reel.mp4"
        cmd = mock_run.call_args[0][0]
        i = cmd.index("-i")
        assert cmd[i + 1] == clip_path

    @patch("compiler.subprocess.run")
    def test_no_clips_returns_none(self, mock_run):
        assert compile_clips([]) is None
        mock_run.assert_not_called()

    @patch("compiler.subprocess.run")
    def test_single_clip_uses_copy_codec(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        compile_clips(["/tmp/clip.mp4"], output_path="/tmp/reel.mp4")
        cmd = mock_run.call_args[0][0]
        assert cmd == ["ffmpeg", "-i", "/tmp/clip.mp4",
                       "-c", "copy", "/tmp/reel.mp4", "-y"]


class TestConcatLossless:
    @patch("compiler.subprocess.run")
    def test_clip_paths_with_spaces_in_concat_file(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        paths = ["/path/to/my clip 1.mp4", "/path/to/my clip 2.mp4"]
        result = _concat_lossless(paths, "/tmp/reel.mp4")
        assert result == "/tmp/reel.mp4"

        cmd = mock_run.call_args[0][0]
        assert "-f" in cmd
        assert "concat" in cmd
        concat_idx = cmd.index("-i")
        concat_path = cmd[concat_idx + 1]
        assert os.path.exists(concat_path) is False

    @patch("compiler.subprocess.run")
    def test_concat_ffmpeg_command_structure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        paths = ["/tmp/a.mp4", "/tmp/b.mp4"]
        _concat_lossless(paths, "/tmp/reel.mp4")

        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"
        assert "-f" in cmd
        assert "concat" in cmd
        assert "-safe" in cmd
        assert "0" in cmd
        assert "-c" in cmd
        assert "copy" in cmd


class TestXfadeCompile:
    @patch("compiler.subprocess.run")
    @patch("compiler._get_duration", side_effect=[10.0, 15.0])
    def test_paths_with_spaces(self, mock_dur, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        paths = ["/path/to/my clip 1.mp4", "/path/to/my clip 2.mp4"]
        result = _xfade_compile(paths, "crossfade", 0.5, "/tmp/reel.mp4")

        assert result == "/tmp/reel.mp4"
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffmpeg"

        input_indices = [i for i, a in enumerate(cmd) if a == "-i"]
        assert len(input_indices) == 2
        assert cmd[input_indices[0] + 1] == paths[0]
        assert cmd[input_indices[1] + 1] == paths[1]

    @patch("compiler.subprocess.run")
    @patch("compiler._get_duration", side_effect=[10.0, 15.0])
    def test_filter_complex_includes_xfade(self, mock_dur, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        _xfade_compile(["/tmp/a.mp4", "/tmp/b.mp4"],
                       "crossfade", 0.5, "/tmp/reel.mp4")

        cmd = mock_run.call_args[0][0]
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert "xfade" in filter_str
        assert "acrossfade" in filter_str
        assert "transition=crossfade" in filter_str
        assert "duration=0.5" in filter_str

    @patch("compiler.subprocess.run")
    @patch("compiler._get_duration", side_effect=[10.0, 15.0])
    def test_invalid_transition_falls_back_to_crossfade(self, mock_dur, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        _xfade_compile(["/tmp/a.mp4", "/tmp/b.mp4"],
                       "invalid_transition", 0.5, "/tmp/reel.mp4")

        cmd = mock_run.call_args[0][0]
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert "transition=crossfade" in filter_str

    @patch("compiler.subprocess.run")
    @patch("compiler._get_duration", side_effect=[10.0, 15.0, 20.0])
    def test_three_clip_xfade_structure(self, mock_dur, mock_run):
        mock_run.return_value = subprocess.CompletedProcess([], returncode=0)
        _xfade_compile(
            ["/tmp/a.mp4", "/tmp/b.mp4", "/tmp/c.mp4"],
            "crossfade", 0.5, "/tmp/reel.mp4",
        )

        cmd = mock_run.call_args[0][0]
        fc_idx = cmd.index("-filter_complex")
        filter_str = cmd[fc_idx + 1]
        assert filter_str.count("xfade") == 2
        assert filter_str.count("acrossfade") == 2
        assert "[v2]" in filter_str
        assert "[a2]" in filter_str
        assert "-map" in cmd
        assert "[v2]" in cmd
        assert "[a2]" in cmd
