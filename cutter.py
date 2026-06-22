import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from config import settings
from reframer import crop_filter as face_crop_filter
from subtitle import write_subtitles
from thumbnailer import generate_thumbnail
from watermarker import build_watermark_filter

MAC_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

_DEFAULT_FONT = next((f for f in MAC_FONTS if os.path.exists(f)), None)

Clip = dict[str, Any]
Segment = dict[str, Any]


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:")


def _hook_filter(clip: Clip, duration: float) -> str | None:
    hook_text = clip.get("hook_text", "")
    if not hook_text or not settings.hook_overlay:
        return None
    hook_dur = min(settings.hook_duration, duration)
    escaped = _escape_drawtext(hook_text)
    font_part = f":fontfile={_DEFAULT_FONT}" if _DEFAULT_FONT else ""
    return (
        f"drawtext=text='{escaped}'{font_part}"
        ":fontsize=28:fontcolor=white:box=1:boxcolor=black@0.6"
        ":x=(w-text_w)/2:y=20"
        f":enable='between(t,0,{hook_dur})'"
    )


def _detect_video_size(video_path: str) -> tuple[int | None, int | None]:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        video_path,
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
        parts = out.split(",")
        return int(parts[0]), int(parts[1])
    except Exception:
        return None, None


def slice_video(
    video_path: str,
    clips: list[Clip],
    segments: list[Segment] | None = None,
) -> list[str]:
    if not clips:
        return []

    output_dir = settings.output_dir
    os.makedirs(output_dir, exist_ok=True)

    video_w, video_h = _detect_video_size(video_path)

    def _process(i: int, clip: Clip) -> tuple[int, str] | None:
        start = clip.get("start", 0)
        end = clip.get("end", 0)
        duration = end - start
        if duration <= 0:
            return None

        output_path = os.path.join(output_dir, f"clip_{i+1}.mp4")
        sub_style = settings.subtitle_style

        crop_f = settings.crop_filter
        if settings.face_tracking and video_w and video_h:
            crop_f = face_crop_filter(video_path, start, end, video_w, video_h)

        video_filters = [
            crop_f,
            f"fade=t=in:st=0:d={settings.fade_duration}",
        ]

        if duration > settings.fade_duration * 2:
            video_filters.append(
                f"fade=t=out:st={duration-settings.fade_duration}:d={settings.fade_duration}"
            )

        hook = _hook_filter(clip, duration)
        if hook:
            video_filters.append(hook)

        sub_path = None
        if segments:
            sub_path = write_subtitles(
                segments, start, end,
                os.path.join(output_dir, f"clip_{i+1}"),
                style=sub_style,
            )
            video_filters.append(f"subtitles={sub_path}")

        af_src = "[0:a]"
        af_chain = [f for f in [settings.loudnorm_filter] if f]
        has_bgm = bool(settings.bgm_path and os.path.exists(settings.bgm_path))

        duck = ""
        if has_bgm:
            bgm_filters = [f"[1:a]volume={settings.bgm_volume}[bgm]"]
            if af_chain:
                af_str = ",".join(af_chain)
                duck = (
                    ";".join(bgm_filters)
                    + f";{af_src}{af_str}[main]"
                    + ";[main][bgm]sidechaincompress="
                    "threshold=-18dB:ratio=6:attack=1:release=100[audio]"
                )
            else:
                duck = (
                    ";".join(bgm_filters)
                    + f";{af_src}[main]"
                    + ";[main][bgm]sidechaincompress="
                    "threshold=-18dB:ratio=6:attack=1:release=100[audio]"
                )

        if video_w and video_h:
            out_w = min(video_w, int(video_h * 9 / 16))
        else:
            out_w = 1080
        watermark_input_idx = 1 + (1 if has_bgm else 0)
        watermark_filter = build_watermark_filter(settings, out_w, input_idx=watermark_input_idx)
        has_watermark = watermark_filter is not None

        cmd = ["ffmpeg"]
        cmd += ["-i", video_path]
        if has_bgm:
            cmd += ["-i", settings.bgm_path]
        if has_watermark:
            cmd += ["-i", settings.watermark_path]

        cmd += ["-ss", str(start), "-t", str(duration)]

        if has_watermark:
            chains = []
            chains.append(f"[0:v]{','.join(video_filters)}[vid];{watermark_filter}")
            if has_bgm:
                chains.append(duck)
            elif af_chain:
                chains.append(f"[0:a]{','.join(af_chain)}[audio]")
            cmd += ["-filter_complex", ";".join(chains)]
            cmd += ["-map", "[out]"]
            cmd += ["-map", "[audio]" if (has_bgm or af_chain) else "0:a"]
        elif has_bgm:
            cmd += ["-vf", ",".join(video_filters)]
            cmd += ["-filter_complex", duck]
            cmd += ["-map", "0:v:0", "-map", "[audio]"]
        else:
            cmd += ["-vf", ",".join(video_filters)]
            if af_chain:
                cmd += ["-af", ",".join(af_chain)]

        cmd += [
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "fast",
            "-c:a", "aac",
            "-max_muxing_queue_size", "1024",
            output_path, "-y",
        ]

        try:
            subprocess.run(cmd, check=True, timeout=7200, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if settings.thumbnail:
                generate_thumbnail(i, video_path, start, duration, clip.get("hook_text", ""), output_dir)
            return (i, output_path)
        except subprocess.CalledProcessError as e:
            print(f"Error slicing clip {i+1}: {e.stderr.decode()}")
            return None
        finally:
            if sub_path and os.path.exists(sub_path):
                os.unlink(sub_path)

    paths: list[tuple[int, str]] = []
    max_workers = min(settings.parallel_workers, 2)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process, i, clip): i
            for i, clip in enumerate(clips)
        }
        for future in as_completed(futures):
            result = future.result()
            if result:
                paths.append(result)

    paths.sort(key=lambda x: x[0])
    return [p for _, p in paths]
