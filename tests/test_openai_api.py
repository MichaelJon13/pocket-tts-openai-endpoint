"""Tests for the OpenAI-compatible TTS API endpoints."""

import pytest
from fastapi.testclient import TestClient

from pocket_tts.main import web_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(web_app)


def test_health_endpoint(client):
    """Test the /health endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_root_endpoint(client):
    """Test the root endpoint returns the web interface."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_auth_endpoint_no_keys_required(client, monkeypatch):
    """Test /v1/auth returns keys not required when REQUIRE_API_KEYS is false."""
    monkeypatch.setenv("REQUIRE_API_KEYS", "false")
    response = client.get("/v1/auth")
    assert response.status_code == 200
    data = response.json()
    assert data["enabled"] is False
    assert "not required" in data["message"].lower()


@pytest.mark.skip(reason="Env vars loaded at module import, requires restart")
def test_auth_endpoint_keys_required():
    """Test /v1/auth when API keys are required."""
    pass


def test_speech_endpoint_missing_input(client):
    """Test /v1/audio/speech returns 422 for missing input."""
    response = client.post("/v1/audio/speech", json={})
    assert response.status_code == 422


def test_speech_endpoint_empty_input(client):
    """Test /v1/audio/speech returns 400 for empty input."""
    response = client.post("/v1/audio/speech", json={"input": "", "voice": "alloy"})
    assert response.status_code == 400


def test_speech_endpoint_long_input(client):
    """Test /v1/audio/speech returns 400 for too long input."""
    long_input = "a" * 5000
    response = client.post("/v1/audio/speech", json={"input": long_input, "voice": "alloy"})
    assert response.status_code == 400
    assert "4096" in response.json()["detail"]


def test_speech_endpoint_invalid_voice(client):
    """Test /v1/audio/speech returns 400 for invalid voice."""
    response = client.post(
        "/v1/audio/speech", json={"input": "Hello", "voice": "invalid_voice_name"}
    )
    assert response.status_code == 400
    assert "voice" in response.json()["detail"].lower()


def test_speech_endpoint_invalid_response_format(client):
    """Test /v1/audio/speech returns 400 for invalid response_format."""
    response = client.post(
        "/v1/audio/speech", json={"input": "Hello", "voice": "alloy", "response_format": "invalid"}
    )
    assert response.status_code == 400
    assert "response_format" in response.json()["detail"].lower()


def test_speech_endpoint_invalid_speed(client):
    """Test /v1/audio/speech returns 400 for invalid speed."""
    response = client.post(
        "/v1/audio/speech", json={"input": "Hello", "voice": "alloy", "speed": 5.0}
    )
    assert response.status_code == 400


def test_speech_endpoint_speed_too_low(client):
    """Test /v1/audio/speech returns 400 for speed too low."""
    response = client.post(
        "/v1/audio/speech", json={"input": "Hello", "voice": "alloy", "speed": 0.1}
    )
    assert response.status_code == 400


def test_speech_endpoint_invalid_stream_format(client):
    """Test /v1/audio/speech returns 400 for invalid stream_format."""
    response = client.post(
        "/v1/audio/speech", json={"input": "Hello", "voice": "alloy", "stream_format": "invalid"}
    )
    assert response.status_code == 400


@pytest.mark.skip(reason="Requires model to be loaded")
def test_speech_endpoint_all_valid_voices_validation():
    """Test /v1/audio/speech validates voices correctly - skip without model."""
    pass


@pytest.mark.skip(reason="Requires model to be loaded")
def test_speech_endpoint_invalid_voice_gives_error():
    """Test /v1/audio/speech returns proper error for invalid voice - skip without model."""
    pass


def test_openapi_schema(client):
    """Test the OpenAPI schema is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "info" in data
    assert data["info"]["title"] == "Kyutai Pocket TTS API"


def test_docs_endpoint(client):
    """Test the /docs endpoint redirects to Swagger UI."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
