import os
from typing import Any

import yt_dlp


def download_video(url: str, output_dir: str = "downloads") -> dict[str, Any]:
    "Download a video from a URL using yt-dlp"

    result: dict[str, Any] = {"error": None}

    try:
        os.makedirs(output_dir, exist_ok=True)

        ydl_opts = {
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "quiet": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            result["title"] = info.get("title", "Unknown Title")
            result["filepath"] = ydl.prepare_filename(info)
            result["duration_seconds"] = info.get("duration", 0)

        if not os.path.exists(result["filepath"]):
            candidates = [f for f in os.listdir(output_dir) if f.startswith(info.get("title", ""))]
            if candidates:
                result["filepath"] = os.path.join(output_dir, candidates[0])

    except Exception as e:
        result["error"] = str(e)

    return result
