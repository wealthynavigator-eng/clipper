import mlx_whisper

def transcribe_audio(filepath: str, language: str = "en") -> dict:
    "Transcribe audio using mlx_whisper"

    result = {"error": None}

    try:
        model, _ = mlx_whisper.load("tiny")
        result["text"] = mlx_whisper.transcribe(model, filepath, language=language)
    except Exception as e:
        result["error"] = str(e)

    return result

if __name__ == "__main__":
    # Test block
    test_file = "test_audio.mp3"
    result = transcribe_audio(test_file)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print(f"Transcription: {result['text']}")
