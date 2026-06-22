
import os

from config import Settings

_POSITIONS: dict[str, str] = {
    "top-left": "10:10",
    "top-right": "W-w-10:10",
    "bottom-left": "10:H-h-10",
    "bottom-right": "W-w-10:H-h-10",
    "center": "(W-w)/2:(H-h)/2",
    "top-center": "(W-w)/2:10",
    "bottom-center": "(W-w)/2:H-h-10",
    "left-center": "10:(H-h)/2",
    "right-center": "W-w-10:(H-h)/2",
}


def build_watermark_filter(settings: Settings, output_width: int = 1080, input_idx: int = 1) -> str | None:
    path = settings.watermark_path
    if not path or not os.path.exists(path):
        return None

    scale = settings.watermark_scale
    wm_w = int(output_width * scale)

    xy = _POSITIONS.get(settings.watermark_position, "W-w-10:10")

    chain = f"[{input_idx}:v]scale={wm_w}:-1"
    if settings.watermark_opacity < 1.0:
        chain += f",format=rgba,colorchannelmixer=aa={settings.watermark_opacity}"
    chain += f"[wm];[vid][wm]overlay={xy}[out]"

    return chain
