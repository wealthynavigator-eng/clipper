from typing import Any

import mlx_whisper


def transcribe_audio(filepath: str, language: str = "en") -> dict[str, Any]:
    "Transcribe audio using mlx_whisper"

    result: dict[str, Any] = {"error": None}

    try:
        raw_result = mlx_whisper.transcribe(
            filepath,
            path_or_hf_repo="mlx-community/whisper-base-mlx"
        )
        result["text"] = raw_result.get("text")
        result["segments"] = raw_result.get("segments")
    except Exception as e:
        result["error"] = str(e)

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
