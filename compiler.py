import os
import subprocess
import tempfile

_XFADE_TYPES = {"crossfade", "fadeblack", "fadewhite", "distance",
                "slideleft", "slideright", "slidetop", "slidebottom",
                "fade", "fadegrays", "hblur", "wipetl", "wipetr",
                "wipebl", "wipebr", "squeezeh", "squeezev", "zoomin"}


def _get_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def compile_clips(
    clip_paths: list[str],
    transition: str = "cut",
    duration: float = 0.3,
    output_path: str = "output/reel.mp4",
) -> str | None:
    if not clip_paths:
        return None

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if len(clip_paths) == 1:
        cmd = ["ffmpeg", "-i", clip_paths[0], "-c", "copy", output_path, "-y"]
        subprocess.run(cmd, check=True, timeout=7200, capture_output=True)
        return output_path

    if transition == "cut":
        return _concat_lossless(clip_paths, output_path)

    return _xfade_compile(clip_paths, transition, duration, output_path)


def _concat_lossless(clip_paths: list[str], output_path: str) -> str:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_path = f.name
        for p in clip_paths:
            escaped = p.replace("\\", "\\\\").replace("'", "\\'")
            f.write(f"file '{escaped}'\n")

    try:
        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", concat_path,
            "-c", "copy",
            output_path, "-y",
        ]
        subprocess.run(cmd, check=True, timeout=7200, capture_output=True)
        return output_path
    finally:
        os.unlink(concat_path)


def _xfade_compile(
    clip_paths: list[str],
    transition: str,
    xfade_duration: float,
    output_path: str,
) -> str:
    if transition not in _XFADE_TYPES:
        transition = "crossfade"

    durations = [_get_duration(p) for p in clip_paths]

    inputs: list[str] = []
    for p in clip_paths:
        inputs += ["-i", p]

    parts: list[str] = []
    offset = durations[0] - xfade_duration
    for i in range(1, len(clip_paths)):
        prev_v = f"v{i-1}" if i > 1 else "0:v"
        cur_v = f"{i}:v"
        parts.append(f"[{prev_v}][{cur_v}]xfade=transition={transition}:duration={xfade_duration}:offset={offset}[v{i}]")

        prev_a = f"a{i-1}" if i > 1 else "0:a"
        cur_a = f"{i}:a"
        parts.append(f"[{prev_a}][{cur_a}]acrossfade=d={xfade_duration}[a{i}]")

        if i < len(clip_paths) - 1:
            offset += durations[i] - xfade_duration

    last_idx = len(clip_paths) - 1
    filter_complex = ";".join(parts)

    cmd = [
        "ffmpeg",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[v{last_idx}]",
        "-map", f"[a{last_idx}]",
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac",
        "-max_muxing_queue_size", "1024",
        output_path, "-y",
    ]

    subprocess.run(cmd, check=True, timeout=7200, capture_output=True)
    return output_path
