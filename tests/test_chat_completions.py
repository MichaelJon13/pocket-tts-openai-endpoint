"""Tests for the /v1/chat/completions and /v1/audio/voices endpoints."""

import pytest
from fastapi.testclient import TestClient

from pocket_tts.main import web_app, _split_sentences


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(web_app)


class TestSplitSentences:
    def test_simple_sentences(self):
        result = _split_sentences("Hello world. How are you? I'm fine.")
        assert result == ["Hello world.", "How are you?", "I'm fine."]

    def test_single_sentence(self):
        result = _split_sentences("Just one sentence here.")
        assert result == ["Just one sentence here."]

    def test_no_punctuation(self):
        result = _split_sentences("This has no punctuation at all")
        assert result == ["This has no punctuation at all"]

    def test_exclamation_and_question(self):
        result = _split_sentences("Wow! Really? Yes.")
        assert result == ["Wow!", "Really?", "Yes."]

    def test_empty_text(self):
        result = _split_sentences("")
        assert result == []

    def test_abbreviation_preserved(self):
        result = _split_sentences("Dr. Smith went to Washington. He arrived at 10 a.m.")
        assert result == ["Dr. Smith went to Washington.", "He arrived at 10 a.m."]


class TestVoicesEndpoint:
    def test_list_voices_returns_mapping(self, client):
        response = client.get("/v1/audio/voices")
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        voices = data["voices"]
        assert "alloy" in voices
        assert "ash" in voices
        assert voices["alloy"]["pocket_voice"] == "alba"
        assert voices["alloy"]["type"] == "builtin"

    def test_voices_include_all_openai_voices(self, client):
        response = client.get("/v1/audio/voices")
        data = response.json()
        expected = {"alloy", "ash", "ballad", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer", "verse", "marin", "cedar"}
        assert expected.issubset(data["voices"].keys())


class TestChatCompletionsValidation:
    def test_no_api_key_returns_400(self, client):
        """Should fail when no LLM is configured."""
        response = client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        assert response.status_code == 400
        assert "LLM" in response.json()["detail"]

    def test_invalid_messages_format(self, client):
        """Missing messages field should return 422."""
        response = client.post("/v1/chat/completions", json={})
        assert response.status_code == 422


@pytest.mark.skip(reason="Requires an LLM backend to be configured")
class TestChatCompletionsWithLLM:
    """Integration tests that require OPENAI_API_KEY env var."""

    def test_nonstreaming_returns_text(self, client):
        pass

    def test_streaming_returns_events(self, client):
        pass
