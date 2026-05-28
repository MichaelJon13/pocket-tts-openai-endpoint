import asyncio
import base64
import io
import json
import logging
import os
import random
import re
import string
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from queue import Queue
from typing import AsyncGenerator

import httpx
import typer
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing_extensions import Annotated

from pocket_tts.data.audio import StreamingWAVWriter, stream_audio_chunks
from pocket_tts.default_parameters import (
    DEFAULT_EOS_THRESHOLD,
    DEFAULT_FRAMES_AFTER_EOS,
    DEFAULT_LSD_DECODE_STEPS,
    DEFAULT_NOISE_CLAMP,
    DEFAULT_TEMPERATURE,
    MAX_TOKEN_PER_CHUNK,
    get_default_text_for_language,
    get_default_voice_for_language,
)
from pocket_tts.models.tts_model import TTSModel, export_model_state
from pocket_tts.utils.logging_utils import enable_logging
from pocket_tts.utils.utils import _ORIGINS_OF_PREDEFINED_VOICES

OPENAI_VOICE_TO_POCKET_VOICE = {
    "alloy": "alba",
    "ash": "marius",
    "ballad": "javert",
    "coral": "jean",
    "echo": "fantine",
    "fable": "cosette",
    "onyx": "eponine",
    "nova": "azelma",
    "sage": "alba",
    "shimmer": "marius",
    "verse": "javert",
    "marin": "jean",
    "cedar": "fantine",
}

OPENAI_SUPPORTED_FORMATS = {"mp3", "opus", "aac", "flac", "wav", "pcm"}

OPENAI_SUPPORTED_MODELS = {"tts-1", "tts-1-hd", "gpt-4o-mini-tts", "gpt-4o-mini-tts-2025-12-15"}

CUSTOM_VOICES: dict[str, str] = {}

REQUIRE_API_KEYS = os.environ.get("REQUIRE_API_KEYS", "false").lower() == "true"
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
API_KEYS_FILE = Path.home() / ".cache" / "pocket_tts" / "api_keys.json"


def generate_api_key(length: int = 32) -> str:
    """Generate a random API key."""
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def load_api_keys() -> list[str]:
    """Load API keys from file, or generate new ones if file doesn't exist."""
    if API_KEYS_FILE.exists():
        try:
            data = json.loads(API_KEYS_FILE.read_text())
            return data.get("keys", [])
        except (json.JSONDecodeError, IOError):
            pass

    API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    keys = [generate_api_key() for _ in range(3)]
    API_KEYS_FILE.write_text(json.dumps({"keys": keys}))
    logger.info(f"Generated new API keys: {keys}")
    return keys


def get_api_keys() -> list[str]:
    """Get all valid API keys."""
    return load_api_keys()


def verify_api_key(key: str) -> bool:
    """Verify an API key."""
    if not REQUIRE_API_KEYS:
        return True
    return key in get_api_keys()


def convert_audio_format(wav_data: bytes, output_format: str) -> bytes:
    """Convert WAV audio to different formats using pydub."""
    try:
        from pydub import AudioSegment
    except ImportError:
        return wav_data

    audio = AudioSegment.from_file(io.BytesIO(wav_data), format="wav")

    if output_format == "mp3":
        output = io.BytesIO()
        audio.export(output, format="mp3", bitrate="128k")
        return output.getvalue()
    elif output_format == "opus":
        output = io.BytesIO()
        audio.export(output, format="ogg", codec="libopus")
        return output.getvalue()
    elif output_format == "aac":
        output = io.BytesIO()
        audio.export(output, format="adts")
        return output.getvalue()
    elif output_format == "flac":
        output = io.BytesIO()
        audio.export(output, format="flac")
        return output.getvalue()
    elif output_format == "pcm":
        return wav_data
    else:
        return wav_data


class SpeechRequest(BaseModel):
    input: str
    model: str = "tts-1"
    voice: str | dict = "alloy"
    response_format: str | None = None
    speed: float | None = None
    instructions: str | None = None
    stream_format: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    voice: str = "alloy"
    tts_enabled: bool = True
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None


logger = logging.getLogger(__name__)


cli_app = typer.Typer(
    help="Kyutai Pocket TTS - Text-to-Speech generation tool", pretty_exceptions_show_locals=False
)


# ------------------------------------------------------
# The pocket-tts server implementation
# ------------------------------------------------------

# Global model instance
tts_model: TTSModel | None = None

web_app = FastAPI(
    title="Kyutai Pocket TTS API",
    description="Text-to-Speech generation API with OpenAI-compatible endpoint",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)
web_app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pod1-10007.internal.kyutai.org",
        "https://kyutai.org",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@web_app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    static_path = Path(__file__).parent / "static" / "index.html"
    content = static_path.read_text()
    # Replace the placeholder with the actual default text prompt
    origin = str(tts_model.origin) if tts_model is not None else "english"
    print(origin)
    content = content.replace(
        "DEFAULT_TEXT_PROMPT", get_default_text_for_language(origin)
    )
    return content


@web_app.get("/health")
async def health():
    return {"status": "healthy"}


@web_app.get("/v1/auth")
async def get_auth_status(http_request: Request):
    """Get authentication status and API keys (if enabled)."""
    if not REQUIRE_API_KEYS:
        return {"enabled": False, "message": "API keys are not required"}

    if ADMIN_API_KEY:
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != ADMIN_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid admin key")

    keys = get_api_keys()
    return {"enabled": True, "message": "API keys are required", "keys": keys}


def write_to_queue(queue, text_to_generate, model_state):
    """Allows writing to the StreamingResponse as if it were a file."""

    class FileLikeToQueue(io.IOBase):
        def __init__(self, queue):
            self.queue = queue

        def write(self, data):
            self.queue.put(data)

        def flush(self):
            pass

        def close(self):
            self.queue.put(None)

    audio_chunks = tts_model.generate_audio_stream(
        model_state=model_state, text_to_generate=text_to_generate
    )
    stream_audio_chunks(FileLikeToQueue(queue), audio_chunks, tts_model.config.mimi.sample_rate)


def generate_data_with_state(text_to_generate: str, model_state: dict):
    queue = Queue()

    # Run your function in a thread
    thread = threading.Thread(target=write_to_queue, args=(queue, text_to_generate, model_state))
    thread.start()

    # Yield data as it becomes available
    i = 0
    while True:
        data = queue.get()
        if data is None:
            break
        i += 1
        yield data

    thread.join()


@web_app.post("/tts")
def text_to_speech(
    text: str = Form(...),
    voice_url: str | None = Form(None),
    voice_wav: UploadFile | None = File(None),
):
    """
    Generate speech from text using the pre-loaded voice prompt or a custom voice.

    Args:
        text: Text to convert to speech
        voice_url: Optional built-in voice name (e.g., "alba"), or voice URL (http://, https://, or hf://)
        voice_wav: Optional uploaded voice file (mutually exclusive with voice_url)
    """
    logging.info("Received web UI /tts request for text: '%s'", text[:50])
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if voice_url is None and voice_wav is None:
        voice_url = get_default_voice_for_language(str(tts_model.origin))

    if voice_url is not None and voice_wav is not None:
        raise HTTPException(status_code=400, detail="Cannot provide both voice_url and voice_wav")

    # Use the appropriate model state
    if voice_url is not None:
        if not (
            voice_url.startswith("http://")
            or voice_url.startswith("https://")
            or voice_url.startswith("hf://")
            or voice_url in _ORIGINS_OF_PREDEFINED_VOICES
        ):
            raise HTTPException(
                status_code=400, detail="voice_url must start with http://, https://, or hf://"
            )
        model_state = tts_model._cached_get_state_for_audio_prompt(voice_url)
        logging.warning("Using voice from URL: %s", voice_url)
    elif voice_wav is not None:
        # Use uploaded voice file - preserve extension for format detection
        suffix = Path(voice_wav.filename).suffix if voice_wav.filename else ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = voice_wav.file.read()
            temp_file.write(content)
            temp_file.flush()
            temp_file_path = temp_file.name

        # Close the file before reading it back (required on Windows)
        try:
            model_state = tts_model.get_state_for_audio_prompt(Path(temp_file_path), truncate=True)
        finally:
            os.unlink(temp_file_path)
    else:
        raise HTTPException(status_code=500, detail="This should never happen.")

    return StreamingResponse(
        generate_data_with_state(text, model_state),
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=generated_speech.wav",
            "Transfer-Encoding": "chunked",
        },
    )


@web_app.post("/v1/audio/speech")
async def create_speech(request: SpeechRequest, http_request: Request):
    """
    OpenAI-compatible TTS endpoint.
    Generate speech from text using the specified voice.
    """
    if REQUIRE_API_KEYS:
        auth_header = http_request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        api_key = auth_header[7:]
        if not verify_api_key(api_key):
            raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.input.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    if len(request.input) > 4096:
        raise HTTPException(status_code=400, detail="Input text cannot exceed 4096 characters")

    if (
        request.response_format is not None
        and request.response_format not in OPENAI_SUPPORTED_FORMATS
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response_format. Supported: {', '.join(OPENAI_SUPPORTED_FORMATS)}",
        )

    if request.speed is not None and (request.speed < 0.25 or request.speed > 4.0):
        raise HTTPException(status_code=400, detail="Speed must be between 0.25 and 4.0")

    if request.stream_format not in (None, "sse", "audio"):
        raise HTTPException(status_code=400, detail="stream_format must be 'sse' or 'audio'")

    if request.instructions:
        logger.warning("instructions parameter is not supported, ignoring")

    if isinstance(request.voice, dict) and "id" in request.voice:
        voice_id = request.voice["id"]
        if voice_id not in CUSTOM_VOICES:
            raise HTTPException(
                status_code=400,
                detail=f"Custom voice '{voice_id}' not found. Available: {list(CUSTOM_VOICES.keys())}",
            )
        pocket_voice = CUSTOM_VOICES[voice_id]
    elif isinstance(request.voice, str):
        pocket_voice = OPENAI_VOICE_TO_POCKET_VOICE.get(request.voice)
        if pocket_voice is None:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid voice. Supported: {', '.join(OPENAI_VOICE_TO_POCKET_VOICE.keys())}",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid voice format. Must be a string or object with 'id' field",
        )

    model_state = tts_model._cached_get_state_for_audio_prompt(pocket_voice)

    response_format = request.response_format or "wav"
    use_sse = request.stream_format == "sse"

    def generate_audio():
        import numpy as np
        import wave

        queue = Queue()
        thread = threading.Thread(target=write_to_queue, args=(queue, request.input, model_state))
        thread.start()

        audio_chunks = []
        while True:
            data = queue.get()
            if data is None:
                break
            audio_chunks.append(data)

        thread.join()

        wav_data = b"".join(audio_chunks)

        if request.speed is not None and request.speed != 1.0 and wav_data:
            with wave.open(io.BytesIO(wav_data), "rb") as wav_in:
                sample_rate = wav_in.getframerate()
                n_frames = wav_in.getnframes()
                audio_int16 = np.frombuffer(wav_in.readframes(n_frames), dtype=np.int16)

            audio_float = audio_int16.astype(np.float32) / 32768.0

            speed = request.speed
            if speed > 1.0:
                indices = np.arange(0, len(audio_float), int(speed))
            else:
                repeat = int(1 / speed)
                indices = np.repeat(np.arange(len(audio_float)), repeat)
            indices = indices[indices < len(audio_float)]
            audio_float = audio_float[indices]

            audio_int16 = (audio_float * 32767).astype(np.int16)

            output = io.BytesIO()
            with wave.open(output, "wb") as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(2)
                wav_out.setframerate(sample_rate)
                wav_out.writeframes(audio_int16.tobytes())

            wav_data = output.getvalue()

        if response_format != "wav" and wav_data:
            wav_data = convert_audio_format(wav_data, response_format)

        return wav_data

    use_sse = request.stream_format == "sse"

    if use_sse:

        async def sse_generator():
            wav_data = generate_audio()
            if wav_data:
                audio_b64 = base64.b64encode(wav_data).decode("utf-8")
                yield f'data: {{"audio": "{audio_b64}", "done": false}}\n\n'
            yield 'data: {"audio": "", "done": true}\n\n'

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    media_type = {
        "mp3": "audio/mpeg",
        "opus": "audio/opus",
        "aac": "audio/aac",
        "flac": "audio/flac",
        "wav": "audio/wav",
        "pcm": "audio/wav",
    }.get(response_format, "audio/wav")

    def audio_generator():
        wav_data = generate_audio()
        if wav_data:
            yield wav_data

    return StreamingResponse(
        audio_generator(),
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename=speech.{response_format}",
            "Transfer-Encoding": "chunked",
        },
    )


# ------------------------------------------------------
# /v1/audio/voices — list available voices
# ------------------------------------------------------


@web_app.get("/v1/audio/voices")
async def list_voices():
    """List all available voices (OpenAI-mapped + custom)."""
    openai_voices = {
        v: {"pocket_voice": p, "type": "builtin", "gender": "unknown"}
        for v, p in sorted(OPENAI_VOICE_TO_POCKET_VOICE.items(), key=lambda x: x[1])
    }
    custom_voices = {
        vid: {"path": path, "type": "custom"}
        for vid, path in CUSTOM_VOICES.items()
    }
    return {"voices": {**openai_voices, **custom_voices}}


# ------------------------------------------------------
# /v1/chat/completions — LLM proxy with sentence-level streaming TTS
# ------------------------------------------------------


_ABBREVIATIONS_PATTERN = re.compile(
    r"\b(?:"
    r"Dr|Mr|Ms|Mrs|St|vs|etc|approx|dept|est|govt|mt|ft|in|vol|no"
    r"|Co|Inc|Ltd|Jr|Sr|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    r"|a\.m|p\.m|i\.e|e\.g"
    r")\.(?=\s)"
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on sentence-ending punctuation.

    Preserves common English abbreviations (Dr., Mr., etc.) so they
    don't trigger false splits.
    """
    # Protect abbreviation dots from being treated as sentence boundaries
    placeholders: dict[str, str] = {}

    def _protect(m: re.Match) -> str:
        key = f"\x00{len(placeholders)}\x00"
        placeholders[key] = m.group(0)
        return key

    text = _ABBREVIATIONS_PATTERN.sub(_protect, text)
    parts = re.split(r"(?<=[.!?])\s+", text)

    result = []
    for p in parts:
        p = p.strip()
        # Restore protected abbreviations
        for key, val in placeholders.items():
            p = p.replace(key, val)
        if p:
            result.append(p)
    return result


async def _proxy_llm_stream(
    request: ChatCompletionRequest,
) -> AsyncGenerator[tuple[str, str], None]:
    """Proxy messages to an LLM and yield (sentence_id, sentence) pairs.

    Accumulates text deltas from the streaming LLM response, detects
    sentence boundaries, and yields complete sentences as they arrive.
    """
    base_url = (
        request.llm_base_url
        or os.environ.get("OPENAI_BASE_URL")
        or "https://api.openai.com/v1"
    )
    api_key = request.llm_api_key or os.environ.get("OPENAI_API_KEY", "")
    llm_model = request.llm_model or request.model

    payload: dict = {
        "model": llm_model,
        "messages": [m.model_dump() for m in request.messages],
        "stream": True,
    }
    if request.temperature is not None:
        payload["temperature"] = request.temperature
    if request.max_tokens is not None:
        payload["max_tokens"] = request.max_tokens

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST", f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LLM proxy error: {error_body.decode()}",
                )

            sentence_id = 0
            buffer = ""

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    # Flush remaining buffer
                    remaining = buffer.strip()
                    if remaining:
                        yield (f"sent_{sentence_id}", remaining)
                        sentence_id += 1
                    break

                try:
                    chunk = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if not content:
                    continue

                buffer += content
                sentences = _split_sentences(buffer)

                # If we have complete sentences (all but last may be partial)
                if len(sentences) > 1:
                    for sent in sentences[:-1]:
                        yield (f"sent_{sentence_id}", sent)
                        sentence_id += 1
                    buffer = sentences[-1]

            # Flush any remaining
            remaining = buffer.strip()
            if remaining:
                yield (f"sent_{sentence_id}", remaining)


@web_app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, http_request: Request):
    """
    Chat completion endpoint with optional sentence-level streaming TTS.

    Proxies messages to a configurable LLM backend. When ``tts_enabled`` is true
    (default), each sentence is synthesized to audio as it completes, enabling
    near-real-time voice responses.

    **Non-streaming** returns a standard OpenAI chat completion JSON with the full
    text in ``choices[0].message.content``.

    **Streaming** returns SSE events with two event types:

    * ``data: {"type": "text", "content": "...", "id": "..."}`` — text delta token
    * ``data: {"type": "audio", "content": "<base64>", "text": "...", "id": "..."}``  # noqa: E501
    * ``data: {"type": "done", "id": "..."}`` — signals completion
    """
    if request.llm_base_url is None and not os.environ.get("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=400,
            detail="No LLM configured. Set OPENAI_API_KEY env var or pass llm_base_url + llm_api_key.",
        )

    voice_name = request.voice
    pocket_voice = OPENAI_VOICE_TO_POCKET_VOICE.get(voice_name, voice_name)
    tts_enabled = request.tts_enabled and tts_model is not None

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(__import__("time").time())

    if not request.stream:
        return await _handle_nonstreaming_chat(request, chat_id, created, pocket_voice, tts_enabled)

    return await _handle_streaming_chat(request, chat_id, created, pocket_voice, tts_enabled)


async def _handle_nonstreaming_chat(
    request: ChatCompletionRequest,
    chat_id: str,
    created: int,
    pocket_voice: str,
    tts_enabled: bool,
):
    """Non-streaming: proxy LLM, accumulate full text, optionally TTS entire response."""
    full_text = ""
    try:
        async for _, sentence in _proxy_llm_stream(request):
            full_text += sentence + " "
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM proxy error: {exc}")

    full_text = full_text.strip()

    response: dict = {
        "id": chat_id,
        "object": "chat.completion",
        "created": created,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": full_text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

    # If TTS enabled, generate audio and include it
    if tts_enabled and full_text:
        try:
            model_state = tts_model._cached_get_state_for_audio_prompt(pocket_voice)
            buf = io.BytesIO()
            writer = StreamingWAVWriter(buf, tts_model.config.mimi.sample_rate)
            writer.write_header(tts_model.config.mimi.sample_rate)
            for chunk in tts_model.generate_audio_stream(
                model_state=model_state, text_to_generate=full_text
            ):
                writer.write_pcm_data(chunk)
            writer.finalize()
            wav_data = buf.getvalue()
            response["audio"] = {
                "data": base64.b64encode(wav_data).decode("utf-8"),
                "format": "wav",
            }
        except Exception as exc:
            logger.warning("TTS generation failed in non-streaming chat: %s", exc)

    return response


async def _handle_streaming_chat(
    request: ChatCompletionRequest,
    chat_id: str,
    created: int,
    pocket_voice: str,
    tts_enabled: bool,
):
    """Streaming: proxy LLM, emit text deltas + per-sentence audio events."""

    async def generate() -> AsyncGenerator[str, None]:
        model_state = None
        if tts_enabled:
            try:
                model_state = tts_model._cached_get_state_for_audio_prompt(pocket_voice)
            except Exception as exc:
                logger.warning("Failed to load voice for TTS: %s", exc)
                tts_nonlocal = False
            else:
                tts_nonlocal = True
        else:
            tts_nonlocal = False

        try:
            async for sent_id, sentence in _proxy_llm_stream(request):
                yield f"data: {json.dumps({'type': 'text', 'content': sentence, 'id': sent_id})}\n\n"

                if tts_nonlocal and model_state and sentence.strip():
                    try:
                        buf = io.BytesIO()
                        writer = StreamingWAVWriter(buf, tts_model.config.mimi.sample_rate)
                        writer.write_header(tts_model.config.mimi.sample_rate)
                        for chunk in tts_model.generate_audio_stream(
                            model_state=model_state,
                            text_to_generate=sentence.strip(),
                        ):
                            writer.write_pcm_data(chunk)
                        writer.finalize()
                        wav_data = buf.getvalue()
                        if wav_data:
                            yield f"data: {json.dumps({'type': 'audio', 'content': base64.b64encode(wav_data).decode('utf-8'), 'text': sentence, 'id': sent_id})}\n\n"
                    except Exception as exc:
                        logger.warning("TTS generation failed for sentence: %s", exc)
        except httpx.HTTPStatusError as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': f'LLM returned {exc.response.status_code}: {exc.response.text[:200]}'})}\n\n"
        except httpx.RequestError as exc:
            yield f"data: {json.dumps({'type': 'error', 'content': f'LLM connection failed: {exc}'})}\n\n"
        except Exception as exc:
            logger.exception("Chat streaming error")
            yield f"data: {json.dumps({'type': 'error', 'content': f'Internal error: {exc}'})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'id': chat_id})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@cli_app.command()
def serve(
    host: Annotated[str, typer.Option(help="Host to bind to")] = "localhost",
    port: Annotated[int, typer.Option(help="Port to bind to")] = 8000,
    reload: Annotated[bool, typer.Option(help="Enable auto-reload")] = False,
    language: Annotated[
        str | None,
        typer.Option(
            help="Language for the TTS model. "
            "'english_2026-01', 'english_2026-04', 'english', 'french_24l', 'german_24l', 'portuguese', 'italian', 'spanish'."
            " Incompatible with the config argument. Default is 'english', which is the same model as 'english_2026-04'.",
            show_default=False,
        ),
    ] = None,
    config: Annotated[
        str | None,
        typer.Option(
            help="Path to locally-saved model config .yaml file. "
            "Incompatible with the language argument. If not provided, will use the default English model."
        ),
    ] = None,
    quantize: Annotated[
        bool, typer.Option(help="Apply int8 quantization to reduce memory usage")
    ] = False,
):
    """Start the FastAPI server."""

    global tts_model
    tts_model = TTSModel.load_model(language=language, config=config, quantize=quantize)

    uvicorn.run("pocket_tts.main:web_app", host=host, port=port, reload=reload)


# ------------------------------------------------------
# The pocket-tts single generation CLI implementation
# ------------------------------------------------------


@cli_app.command()
def generate(
    text: Annotated[str, typer.Option(help="Text to generate")] = None,
    voice: Annotated[
        str | None,
        typer.Option(
            help=(
                "Path to audio conditioning file (voice to clone). "
                "Defaults to a built-in voice chosen from the language: "
                "'giovanni' for italian, 'lola' for spanish, 'juergen' for german, "
                "'rafael' for portuguese, 'estelle' for french, 'alba' otherwise."
            ),
            show_default=False,
        ),
    ] = None,
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Disable logging output")] = False,
    language: Annotated[
        str | None,
        typer.Option(
            help=(
                "Language for the TTS model. "
                "'english_2026-01', 'english_2026-04', 'english', 'french_24l', 'spanish_24l',"
                "'german_24l', 'portuguese_24l', 'italian_24l'."
                " Incompatible with the config argument. Default is 'english', which is the same model as 'english_2026-04'. "
                "The '24l' variants are bigger models, "
                "not distilled yet and here only as preview. They're not the final "
                "models for those languages."
            ),
            show_default=False,
        ),
    ] = None,
    config: Annotated[
        str | None,
        typer.Option(
            help="Path to locally-saved model config .yaml file. "
            "Incompatible with the language argument. If not provided, will use the default English model."
        ),
    ] = None,
    lsd_decode_steps: Annotated[
        int, typer.Option(help="Number of generation steps")
    ] = DEFAULT_LSD_DECODE_STEPS,
    temperature: Annotated[
        float, typer.Option(help="Temperature for generation")
    ] = DEFAULT_TEMPERATURE,
    noise_clamp: Annotated[float, typer.Option(help="Noise clamp value")] = DEFAULT_NOISE_CLAMP,
    eos_threshold: Annotated[float, typer.Option(help="EOS threshold")] = DEFAULT_EOS_THRESHOLD,
    frames_after_eos: Annotated[
        int, typer.Option(help="Number of frames to generate after EOS")
    ] = DEFAULT_FRAMES_AFTER_EOS,
    output_path: Annotated[
        str, typer.Option(help="Output path for generated audio")
    ] = "./tts_output.wav",
    device: Annotated[str, typer.Option(help="Device to use")] = "cpu",
    max_tokens: Annotated[
        int, typer.Option(help="Maximum number of tokens per chunk.")
    ] = MAX_TOKEN_PER_CHUNK,
    quantize: Annotated[
        bool, typer.Option(help="Apply int8 quantization to reduce memory usage")
    ] = False,
):
    """Generate speech using Kyutai Pocket TTS."""
    log_level = logging.ERROR if quiet else logging.INFO
    with enable_logging("pocket_tts", log_level):
        if text is None:
            text = get_default_text_for_language(language)
        if text == "-":
            # Read text from stdin
            text = sys.stdin.read()

        if not text.strip():
            logger.error("No input received from stdin.")
            raise typer.Exit(code=1)
        tts_model = TTSModel.load_model(
            language=language,
            config=config,
            temp=temperature,
            lsd_decode_steps=lsd_decode_steps,
            noise_clamp=noise_clamp,
            eos_threshold=eos_threshold,
            quantize=quantize,
        )
        tts_model.to(device)

        if voice is None:
            voice = get_default_voice_for_language(language)
        model_state_for_voice = tts_model.get_state_for_audio_prompt(voice)
        # Stream audio generation directly to file or stdout
        audio_chunks = tts_model.generate_audio_stream(
            model_state=model_state_for_voice,
            text_to_generate=text,
            frames_after_eos=frames_after_eos,
            max_tokens=max_tokens,
        )

        stream_audio_chunks(output_path, audio_chunks, tts_model.config.mimi.sample_rate)

        # Only print the result message if not writing to stdout
        if output_path != "-":
            logger.info("Results written in %s", output_path)
        logger.info("-" * 20)
        logger.info(
            "If you want to try multiple voices and prompts quickly, try the `serve` command."
        )
        logger.info(
            "If you like Kyutai projects, comment, like, subscribe at https://x.com/kyutai_labs"
        )


# ----------------------------------------------
# export audio to safetensors CLI implementation
# ----------------------------------------------


@cli_app.command()
def export_voice(
    audio_path: Annotated[
        str, typer.Argument(help="Audio file or directory to convert and export")
    ],
    export_path: Annotated[str, typer.Argument(help="Output file or directory")],
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Disable logging output")] = False,
    language: Annotated[
        str | None,
        typer.Option(
            help=(
                "Language for the TTS model. "
                "'english_2026-01', 'english_2026-04', 'english', 'french_24l', 'german_24l','spanish_24l',"
                " 'portuguese_24l', 'italian_24l'."
                " Incompatible with the config argument. Default is 'english', which is the same model as 'english_2026-04'. "
                "The '24l' variants are bigger models, "
                "not distilled yet and here only as preview."
            ),
            show_default=False,
        ),
    ] = None,
    config: Annotated[
        str | None,
        typer.Option(
            help="Path to locally-saved model config .yaml file. "
            "Incompatible with the language argument. If not provided, will use the default English model."
        ),
    ] = None,
):
    """Convert and save audio to .safetensors file"""

    log_level = logging.ERROR if quiet else logging.INFO
    with enable_logging("pocket_tts", log_level):
        tts_model = TTSModel.load_model(language=language, config=config)
        model_state = tts_model.get_state_for_audio_prompt(
            audio_conditioning=audio_path, truncate=True
        )
        export_model_state(model_state, export_path)


if __name__ == "__main__":
    cli_app()
