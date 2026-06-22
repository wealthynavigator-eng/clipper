import os
import subprocess

MAC_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

_DEFAULT_FONT = next((f for f in MAC_FONTS if os.path.exists(f)), None)


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:")


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

    escaped = _escape_drawtext(hook_text or "")
    font_part = f":fontfile={_DEFAULT_FONT}" if _DEFAULT_FONT else ""

    cmd = [
        "ffmpeg",
        "-ss", str(mid_time),
        "-i", video_path,
        "-vframes", "1",
        "-vf", (
            f"crop=w='min(iw,ih*9/16)':h=ih,"
            f"drawtext=text='{escaped}'{font_part}"
            ":fontsize=36:fontcolor=white:box=1:boxcolor=black@0.7"
            ":x=(w-text_w)/2:y=h-th-40"
        ),
        thumb_path,
        "-y",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return thumb_path
    except subprocess.CalledProcessError:
        return None
