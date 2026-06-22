import os
import subprocess
import tempfile
from typing import Any

import mlx_whisper

_MAX_CHUNK_SECONDS = 1800  # 30 minutes


def _get_duration(filepath: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        filepath,
    ]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()
    return float(out)


def _extract_audio_chunk(input_path: str, start: float, duration: float, output_path: str) -> None:
    cmd = [
        "ffmpeg",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
        "-y",
    ]
    subprocess.run(cmd, check=True, timeout=600, capture_output=True)


def _merge_chunks(chunks: list[dict[str, Any]]) -> dict[str, Any]:
    text_parts: list[str] = []
    all_segments: list[dict[str, Any]] = []

    for raw in chunks:
        text = raw.get("text")
        if text:
            text_parts.append(text)

        offset = raw.get("_chunk_offset", 0.0)
        segments = raw.get("segments") or []
        for seg in segments:
            seg = dict(seg)
            seg["start"] += offset
            seg["end"] += offset
            all_segments.append(seg)

    return {"text": " ".join(text_parts), "segments": all_segments}


def transcribe_audio(filepath: str, language: str = "en") -> dict[str, Any]:
    result: dict[str, Any] = {"error": None}

    try:
        duration = _get_duration(filepath)
    except Exception as e:
        result["error"] = str(e)
        return result

    if duration <= _MAX_CHUNK_SECONDS:
        try:
            raw = mlx_whisper.transcribe(filepath, path_or_hf_repo="mlx-community/whisper-base-mlx")
            result["text"] = raw.get("text")
            result["segments"] = raw.get("segments")
        except Exception as e:
            result["error"] = str(e)
        return result

    chunks: list[dict[str, Any]] = []
    tmp_paths: list[str] = []
    try:
        start = 0.0
        while start < duration:
            chunk_len = min(_MAX_CHUNK_SECONDS, duration - start)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp.close()
            tmp_paths.append(tmp.name)
            _extract_audio_chunk(filepath, start, chunk_len, tmp.name)
            raw = mlx_whisper.transcribe(tmp.name, path_or_hf_repo="mlx-community/whisper-base-mlx")
            raw["_chunk_offset"] = start
            chunks.append(raw)
            start += chunk_len

        merged = _merge_chunks(chunks)
        result["text"] = merged["text"]
        result["segments"] = merged["segments"]
    except Exception as e:
        result["error"] = str(e)
    finally:
        for p in tmp_paths:
            if os.path.exists(p):
                os.unlink(p)

    return result

if __name__ == "__main__":
    # Test block
    import os

    downloads_dir = "downloads"
    test_file = None

    if os.path.exists(downloads_dir):
        for filename in os.listdir(downloads_dir):
            if filename.endswith((".webm", ".mp4")):
                test_file = os.path.join(downloads_dir, filename)
                break

    if not test_file:
        print("Error: No .webm or .mp4 files found in the downloads directory")
    else:
        result = transcribe_audio(test_file)

        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            print(f"Transcription: {result['text']}")
            if result["segments"]:
                print("First segment:")
                print(result["segments"][0])
