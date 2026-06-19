import os
import json
from dotenv import load_dotenv
from mistralai.client import Mistral
from transcriber import transcribe_audio

def find_clip_moments(transcription: dict) -> list:
    "Find interesting moments in the transcription using Groq API"

    load_dotenv()
    client = Mistral(api_key=os.environ.get("MISTRAL_API_KEY"))

    system_prompt = """
    You are a professional video editor specializing in virality optimization.
    Analyze the transcription segments and identify between 5 to 10 distinct clip moments.
    Each clip should have an average duration of 45-75 seconds. Look for:
    1. High-energy opening hooks or disruptive pattern-interrupt statements
    2. Self-contained narrative arcs (a premise, an explanation, and a clear resolution/punchline)
    3. Highly actionable insights or profound conclusions
    Each clip MUST start at the exact beginning of a complete sentence or thought,
    and must never cut a speaker off mid-word or mid-sentence at the start or end boundaries.
    Map the end time to where that specific thought or payoff naturally concludes,
    merging adjacent text segments together. Return a strict JSON array of objects
    with keys: "start", "end", "hook_text", and "retention_strategy". The
    "retention_strategy" should explain how this clip will maximize viewer
    retention. Ensure the clips are spaced appropriately throughout the content.
    """

    if isinstance(transcription, dict) and "segments" in transcription:
        segments = transcription["segments"]
    else:
        segments = transcription

    lean_segments = [
        {
            "start": round(segment["start"], 2),
            "end": round(segment["end"], 2),
            "text": segment["text"].strip()
        }
        for segment in segments
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(lean_segments)}
    ]

    response = client.chat.complete(
        model="mistral-large-latest",
        messages=messages,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)

if __name__ == "__main__":
    # Test block
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
            clip_moments = find_clip_moments(result["segments"])
            print("Clip moments:")
            print(json.dumps(clip_moments, indent=2))
