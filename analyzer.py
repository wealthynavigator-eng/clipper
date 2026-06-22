import json
import os
import time
from collections.abc import Callable
from typing import Any

import httpx
from dotenv import load_dotenv
from mistralai.client import Mistral as MistralClient
from mistralai.client.errors import MistralError
from openai import OpenAI as OpenAIClient

from config import LLMProvider, settings

load_dotenv()

_clients: dict[str, object] = {}


def _get_mistral() -> MistralClient:
    if "mistral" not in _clients:
        _clients["mistral"] = MistralClient(
            api_key=os.environ.get("MISTRAL_API_KEY"),
            timeout_ms=settings.llm_timeout_ms,
        )
    return _clients["mistral"]  # type: ignore[return-value]


def _get_groq() -> OpenAIClient:
    if "groq" not in _clients:
        _clients["groq"] = OpenAIClient(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
    return _clients["groq"]  # type: ignore[return-value]


def _get_openai() -> OpenAIClient:
    if "openai" not in _clients:
        _clients["openai"] = OpenAIClient(
            api_key=os.environ.get("OPENAI_API_KEY"),
        )
    return _clients["openai"]  # type: ignore[return-value]


def _get_ollama() -> OpenAIClient:
    if "ollama" not in _clients:
        _clients["ollama"] = OpenAIClient(
            api_key="ollama",
            base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434/v1"),
        )
    return _clients["ollama"]  # type: ignore[return-value]


def _complete_mistral(client: MistralClient, model: str, messages: list[dict]) -> Any:
    return client.chat.complete(
        model=model,
        messages=messages,  # type: ignore[arg-type]
        response_format={"type": "json_object"},
    )


def _complete_openai_like(client: OpenAIClient, model: str, messages: list[dict]) -> Any:
    resp = client.chat.completions.create(  # type: ignore[call-overload]
        model=model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    return resp


_PROVIDER_CLIENTS: dict[LLMProvider, tuple[Callable, Callable]] = {
    "mistral": (_get_mistral, _complete_mistral),
    "groq": (_get_groq, _complete_openai_like),
    "openai": (_get_openai, _complete_openai_like),
    "ollama": (_get_ollama, _complete_openai_like),
}


def _parse_response(response: Any) -> list:
    return json.loads(response.choices[0].message.content)


_SYSTEM_PROMPT = """
You are a professional video editor specializing in virality optimization.
Analyze the transcription segments and identify between {min_clips} to {max_clips} distinct clip moments.
Each clip should have an average duration of {min_dur}-{max_dur} seconds. Look for:
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


_REQUIRED_KEYS = {
    "mistral": "MISTRAL_API_KEY",
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def find_clip_moments(
    transcription: dict,
    provider: LLMProvider | None = None,
) -> list:
    provider = provider or settings.llm_provider

    key_name = _REQUIRED_KEYS.get(provider)
    if key_name and not os.environ.get(key_name):
        raise ValueError(f"Missing API key: {key_name} (set in .env or environment)")

    get_client, complete_fn = _PROVIDER_CLIENTS[provider]
    client = get_client()

    system_prompt = _SYSTEM_PROMPT.format(
        min_clips=settings.min_clips,
        max_clips=settings.max_clips,
        min_dur=int(settings.clip_min_duration),
        max_dur=int(settings.clip_max_duration),
    )

    if isinstance(transcription, dict) and "segments" in transcription:
        segments = transcription["segments"]
    else:
        segments = transcription

    lean_segments = [
        {
            "start": round(segment["start"], 2),
            "end": round(segment["end"], 2),
            "text": segment["text"].strip(),
        }
        for segment in segments
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(lean_segments)},
    ]

    exceptions = (MistralError, httpx.HTTPError, json.JSONDecodeError, KeyError)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = complete_fn(client, settings.llm_model, messages)
            return _parse_response(response)
        except exceptions:
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)
    return []


if __name__ == "__main__":
    from transcriber import transcribe_audio

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
