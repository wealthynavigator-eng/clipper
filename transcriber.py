import mlx_whisper

def transcribe_audio(filepath: str, language: str = "en") -> dict:
    "Transcribe audio using mlx_whisper"

    result = {"error": None}

    try:
        raw_result = mlx_whisper.transcribe(
            filepath,
            model="mlx-community/whisper-base",
            language=language
        )
        result["text"] = raw_result.get("text")
        result["segments"] = raw_result.get("segments")
    except Exception as e:
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    # Test block
    test_file = "downloads/If I Started Over, This is Exactly How I'd Get Good at Guitar.webm"
    result = transcribe_audio(test_file)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print(f"Transcription: {result['text']}")
        if result["segments"]:
            print("First segment:")
            print(result["segments"][0])
