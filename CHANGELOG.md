# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.0] - 2025-02-14

### Added
- **OpenAI-Compatible API**: New `/v1/audio/speech` endpoint that accepts OpenAI-compatible requests
  - Supports `input`, `model`, `voice`, `response_format`, `speed`, `stream_format`, and `instructions` parameters
  - Voice mapping from OpenAI voices (alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse, marin, cedar) to pocket-tts voices
- **SSE Streaming**: Support for `stream_format: sse` to stream audio chunks as Server-Sent Events
- **Audio Format Encoding**: Support for mp3, opus, aac, flac, and pcm output formats (via pydub)
- **Custom Voice IDs**: Support for custom voice objects `{ "id": "voice_1234" }`
- **API Key Authentication**: Optional API key authentication for the `/v1/audio/speech` endpoint
  - Enable with `REQUIRE_API_KEYS=true` environment variable
  - API keys stored in volume and persist across restarts
  - 3 API keys generated on first startup
- **Admin Key Protection**: Admin key support to protect the `/v1/auth` endpoint
  - Set via `ADMIN_API_KEY` environment variable
- **FastAPI Documentation**: Enabled `/docs` (Swagger UI), `/redoc` (ReDoc), and `/openapi.json` endpoints
- **Docker/Podman Support**: Added docker-compose.yaml with proper container naming
  - Image name: `localhost/pocket-tts-openai:latest`
  - Container name: `pocket-tts-openai`
- **Voice Recording Script**: Added `voice_recording_script.txt` with a 30-second script for creating custom voice samples

### Changed
- README.md updated with OpenAI-compatible API documentation
- README.md updated with Docker/Podman usage instructions
- README.md updated with API authentication documentation

### Removed
- Python library section removed from README (no longer the primary use case)

### Dependencies
- Added `pydub>=0.25.1` as optional dependency for audio encoding

## [1.0.3] - 2025-01-XX

### Added
- Initial release
