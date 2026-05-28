# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- **Native macOS App**: Added link to the upstream's new native macOS Core ML app to the projects list.
- **`/v1/chat/completions`**: New endpoint that proxies to any OpenAI-compatible LLM backend, with sentence-level streaming TTS. Non-streaming returns full text + base64 WAV audio; streaming emits SSE `text` and `audio` events per completed sentence.
- **`/v1/audio/voices`**: New endpoint listing all available voices (OpenAI mapped + custom).
- **`audioop-lts` guard**: Conditional dependency for Python 3.13+ (pydub compatibility fix).

### Changed
- **README.md**: Major cleanup — removed outdated "quantization unsupported" line (now supported via `--quantize`), consolidated two overlapping Docker sections into one, replaced all `uvx pocket-tts` and `pip install pocket-tts` references with `uv run pocket-tts` (since those pull the upstream package, not this fork), fixed all upstream doc links to point to local docs, and updated GitHub repo link to the fork. Added documentation for `/v1/chat/completions` and `/v1/audio/voices`.
- **Doc files**: Updated `docs/CLI Commands/*.md`, `docs/API Reference/python-api.md`, and `docs/quantization.md` to use `uv run pocket-tts` instead of `uvx pocket-tts` or `pip install pocket-tts`.
- **AGENTS.md**: Added mention of the OpenAI endpoint, `export_voice` command, missing utils (`logging_utils.py`, `weights_loading.py`), pydub dependency, and fixed container test commands to use `pocket-tts-openai`. Added chat completions endpoint, quantization migration, tests info.
- **`mkdocs.yml`**: Updated `repo_url` and `repo_name` to point to this fork.
- **Version pinning**: Updated the README's `uv add` and install instructions to explicitly guide users to clone the fork rather than install the upstream PyPI package.
- **Quantization**: Removed deprecated `torch.ao.quantization` fallback. Now `torchao`-only with a clear `ImportError` if missing. Moved `torchao` from main `dependencies` to optional `quantize` group.
- **`pyproject.toml`**: `torchao` moved to optional `[project.optional-dependencies] quantize` group; added to `dev` group for tests. Added `audioop-lts` conditonal dep for Python 3.13+ under `server` group.

### Removed
- `MiniMaxM25.md` — orphaned file.
- `test.mp3` — test artifact.
- `pocket_tts/utils/debugging.py` — dead code (zero imports).
- `deploy.sh`, `swarm-config.yaml`, `docker-bake.hcl` — Kyutai-specific infrastructure files (hardcoded SSH hosts, Docker registries, Swarm TLS config).
- `docs/API Reference/Reference/` — flattened nested directory.
- Quantization from the "Unsupported features" list in README (now supported).

## [2.1.0] - 2026-05-22

### Added
- **Upstream Sync (v2.1.0)**: Integrated the latest upstream release changes.
  - Added new multi-language support for French, German, Italian, Spanish, and Portuguese.
  - Added preview configurations for larger language models (`french_24l`, `german_24l`, `portuguese_24l`, `italian_24l`, `spanish_24l`).
  - Added native int8 weight quantization support via `torchao` to reduce memory and CPU requirements (activated via the `--quantize` CLI option).
  - Upgraded dependencies including support for PyTorch 2.5+.
- **Unified FastAPI Server**:
  - Unified the new upstream web UI application, root interface, and `/health` checker alongside your custom OpenAI `/v1/audio/speech` and `/v1/auth` endpoints.
  - Added request debug logs to `/tts` to trace client requests inside the container.
- **Dockerization**:
  - Exposed the server on `--host 0.0.0.0` by default inside the `Dockerfile` CMD to prevent `Connection reset by peer` errors when running rootless Podman/Docker.
  - Pre-installed `ffmpeg` inside the container to ensure format conversion via `pydub` functions correctly.

### Changed
- **Robust Startup Gating**: Refactored the web application initialization and testing suites to handle uninitialized model states gracefully and automatically skip gated voice cloning tests if HuggingFace credentials are not configured.
- **README.md**: Updated documentation to detail the new serve options (`--language`, `--quantize`) and recommended connecting via `127.0.0.1` to bypass IPv6 loopback conflicts.
- **SSH Authentication**: Switched the primary local `origin` tracking URL from HTTPS to SSH for secure, passwordless authentication using the registered `zerocool_id_rsa` SSH key.

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
