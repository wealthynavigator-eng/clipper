import os
import json
from dotenv import load_dotenv
from groq import Groq
from transcriber import transcribe_audio

def find_clip_moments(segments: list) -> list:
    "Find interesting moments in the transcription using Groq API"

    load_dotenv()
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    system_prompt = """
    You are an expert video editor. Analyze the transcription segments and identify
    interesting moments to clip. Return a raw JSON array of objects with "start",
    "end", and "reason" keys. The "start" and "end" values should be in seconds.
    The "reason" should be a brief explanation of why this moment is interesting.
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(segments)}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
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
