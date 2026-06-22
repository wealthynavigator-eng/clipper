import os
import subprocess
import tempfile

MAC_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

_DEFAULT_FONT = next((f for f in MAC_FONTS if os.path.exists(f)), None)


def _escape_filter_path(path: str) -> str:
    return path.replace("\\", "\\\\").replace(":", "\\:")


def generate_thumbnail(
    clip_idx: int,
    video_path: str,
    start: float,
    duration: float,
    hook_text: str = "",
    output_dir: str = "output",
) -> str | None:
    thumb_path = os.path.join(output_dir, f"clip_{clip_idx+1}.jpg")
    mid_time = start + duration / 2

    font_part = f":fontfile={_DEFAULT_FONT}" if _DEFAULT_FONT else ""

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
    tmp.write(hook_text or "")
    tmp.close()

    try:
        escaped_path = _escape_filter_path(tmp.name)
        cmd = [
            "ffmpeg",
            "-ss", str(mid_time),
            "-i", video_path,
            "-vframes", "1",
            "-vf", (
                f"crop=w='min(iw,ih*9/16)':h=ih,"
                f"drawtext=textfile={escaped_path}{font_part}"
                ":fontsize=36:fontcolor=white:box=1:boxcolor=black@0.7"
                ":x=(w-text_w)/2:y=h-th-40"
            ),
            thumb_path,
            "-y",
        ]
        subprocess.run(cmd, check=True, timeout=120, capture_output=True)
        return thumb_path
    except subprocess.CalledProcessError:
        return None
    finally:
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)
