import json

from analyzer import _REQUIRED_KEYS, _parse_response


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class TestParseResponse:
    def test_parses_valid_json(self):
        data = [{"start": 0, "end": 10, "hook_text": "test"}]
        resp = FakeResponse(json.dumps(data))
        assert _parse_response(resp) == data

    def test_parses_empty_array(self):
        resp = FakeResponse("[]")
        assert _parse_response(resp) == []

    def test_parses_complex_moments(self):
        data = [
            {"start": 1.5, "end": 30.0, "hook_text": "Hook!", "retention_strategy": "Pattern interrupt"},
            {"start": 45.0, "end": 90.0, "hook_text": "Big reveal", "retention_strategy": "Curiosity gap"},
        ]
        resp = FakeResponse(json.dumps(data))
        result = _parse_response(resp)
        assert len(result) == 2
        assert result[0]["retention_strategy"] == "Pattern interrupt"
        assert result[1]["hook_text"] == "Big reveal"

    def test_raises_on_invalid_json(self):
        resp = FakeResponse("not json")
        import json as j
        try:
            _parse_response(resp)
            assert False, "Expected JSONDecodeError"
        except j.JSONDecodeError:
            pass


class TestRequiredKeys:
    def test_mistral_key_name(self):
        assert _REQUIRED_KEYS["mistral"] == "MISTRAL_API_KEY"

    def test_groq_key_name(self):
        assert _REQUIRED_KEYS["groq"] == "GROQ_API_KEY"

    def test_openai_key_name(self):
        assert _REQUIRED_KEYS["openai"] == "OPENAI_API_KEY"

    def test_ollama_not_required(self):
        assert "ollama" not in _REQUIRED_KEYS
