import base64
import io
import json
import logging
import os
import random
import string
import sys
import tempfile
import threading
from pathlib import Path
from queue import Queue

import typer
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing_extensions import Annotated

from pocket_tts.data.audio import stream_audio_chunks
from pocket_tts.default_parameters import (
    DEFAULT_AUDIO_PROMPT,
    DEFAULT_EOS_THRESHOLD,
    DEFAULT_FRAMES_AFTER_EOS,
    DEFAULT_LSD_DECODE_STEPS,
    DEFAULT_NOISE_CLAMP,
    DEFAULT_TEMPERATURE,
    DEFAULT_VARIANT,
    MAX_TOKEN_PER_CHUNK,
)
from pocket_tts.models.tts_model import TTSModel
from pocket_tts.utils.logging_utils import enable_logging
from pocket_tts.utils.utils import PREDEFINED_VOICES, size_of_dict

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


logger = logging.getLogger(__name__)


cli_app = typer.Typer(
    help="Kyutai Pocket TTS - Text-to-Speech generation tool", pretty_exceptions_show_locals=False
)


# ------------------------------------------------------
# The pocket-tts server implementation
# ------------------------------------------------------

# Global model instance
tts_model: TTSModel | None = None
global_model_state = None

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


@web_app.get("/")
async def root():
    """Serve the frontend."""
    static_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(static_path)


@web_app.get("/health")
async def health():
    return {"status": "healthy"}


@web_app.get("/v1/auth")
async def get_auth_status():
    """Get authentication status and API keys (if enabled)."""
    if not REQUIRE_API_KEYS:
        return {"enabled": False, "message": "API keys are not required"}
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
        voice_url: Optional voice URL (http://, https://, or hf://)
        voice_wav: Optional uploaded voice file (mutually exclusive with voice_url)
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if voice_url is not None and voice_wav is not None:
        raise HTTPException(status_code=400, detail="Cannot provide both voice_url and voice_wav")

    # Use the appropriate model state
    if voice_url is not None:
        if not (
            voice_url.startswith("http://")
            or voice_url.startswith("https://")
            or voice_url.startswith("hf://")
            or voice_url in PREDEFINED_VOICES
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
        # Use default global model state
        model_state = global_model_state

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


@cli_app.command()
def serve(
    voice: Annotated[
        str, typer.Option(help="Path to voice prompt audio file (voice to clone)")
    ] = DEFAULT_AUDIO_PROMPT,
    host: Annotated[str, typer.Option(help="Host to bind to")] = "localhost",
    port: Annotated[int, typer.Option(help="Port to bind to")] = 8000,
    reload: Annotated[bool, typer.Option(help="Enable auto-reload")] = False,
    config: Annotated[
        str,
        typer.Option(
            help="Path to locally-saved model config .yaml file or model variant signature"
        ),
    ] = DEFAULT_VARIANT,
):
    """Start the FastAPI server."""

    global tts_model, global_model_state
    tts_model = TTSModel.load_model(config)

    # Pre-load the voice prompt
    global_model_state = tts_model.get_state_for_audio_prompt(voice)
    logger.info(f"The size of the model state is {size_of_dict(global_model_state) // 1e6} MB")

    uvicorn.run("pocket_tts.main:web_app", host=host, port=port, reload=reload)


# ------------------------------------------------------
# The pocket-tts single generation CLI implementation
# ------------------------------------------------------


@cli_app.command()
def generate(
    text: Annotated[
        str, typer.Option(help="Text to generate")
    ] = "Hello world. I am Kyutai's Pocket TTS. I'm fast enough to run on small CPUs. I hope you'll like me.",
    voice: Annotated[
        str, typer.Option(help="Path to audio conditioning file (voice to clone)")
    ] = DEFAULT_AUDIO_PROMPT,
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Disable logging output")] = False,
    config: Annotated[
        str, typer.Option(help="Model signature or path to config .yaml file")
    ] = DEFAULT_VARIANT,
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
):
    """Generate speech using Kyutai Pocket TTS."""
    log_level = logging.ERROR if quiet else logging.INFO
    with enable_logging("pocket_tts", log_level):
        if text == "-":
            # Read text from stdin
            text = sys.stdin.read()

        if not text.strip():
            logger.error("No input received from stdin.")
            raise typer.Exit(code=1)
        tts_model = TTSModel.load_model(
            config, temperature, lsd_decode_steps, noise_clamp, eos_threshold
        )
        tts_model.to(device)

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
    truncate: Annotated[
        bool, typer.Option("-tr", "--truncate", help="Truncate long audio")
    ] = False,
    quiet: Annotated[bool, typer.Option("-q", "--quiet", help="Disable logging output")] = False,
    config: Annotated[str, typer.Option(help="Model config path or signature")] = DEFAULT_VARIANT,
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
    device: Annotated[str, typer.Option(help="Device to use")] = "cpu",
):
    """Convert and save audio to .safetensors file"""
    import re

    def url(path):
        return path.startswith(("http:", "https:", "hf:"))

    def normalize_url(url):
        # utils.py expects urls to be xxx:// so normalize them
        return re.sub(r"^(http|https|hf)\:\/*(.+)$", r"\1://\2", url)

    def likely_file(path):
        return not url(path) and not likely_dir(path)

    def likely_dir(path):
        return not url(path) and (path.endswith(("/", "\\")) or path == ".")

    def convert_one(in_path, out_path, join_path):
        """helper convert function"""
        voice = in_path.stem
        if url(str(in_path)):
            in_path = normalize_url(str(in_path))
        if join_path:
            out_path = out_path / f"{voice}.safetensors"
        else:
            # ensure output file has correct extension
            out_path = out_path.with_suffix(".safetensors")
        try:
            tts_model.save_audio_prompt(in_path, out_path, truncate)
        except Exception as e:
            logger.error(f"❌ Unable to export voice '{in_path}': {e}")
            return False
        logger.info(f"✅ Successfully exported voice '{voice}' to '{out_path}'")
        return True

    log_level = logging.ERROR if quiet else logging.INFO
    success_count = 0

    with enable_logging("pocket_tts", log_level):
        tts_model = TTSModel.load_model(
            config, temperature, lsd_decode_steps, noise_clamp, eos_threshold
        )
        tts_model.to(device)

        in_path = Path(audio_path)
        out_path = Path(export_path)
        if likely_dir(export_path):
            # make sure output dir exists
            out_path.mkdir(parents=True, exist_ok=True)

        if likely_dir(audio_path):  # batch convert whole directory
            if not in_path.is_dir():
                logger.error(f"Input dir '{audio_path}' does not exists")
                exit(1)
            if not likely_dir(export_path):
                # batch convert, output path must be directory, not file
                out_path = Path("./")
            for path in Path(in_path).iterdir():
                if path.is_file() and path.suffix.lower() in [
                    ".wav",
                    ".mp3",
                    ".flac",
                    ".ogg",
                    ".aiff",
                ]:
                    if convert_one(path, out_path, True):
                        success_count += 1
        else:  # convert single file
            if likely_file(audio_path) and not in_path.exists():
                logger.error(f"Input file '{in_path}'' does not exists")
                exit(1)
            if convert_one(in_path, out_path, likely_dir(export_path)):
                success_count += 1

        if success_count > 0:
            logger.info(f"🎉 Successfully exported {success_count} voices.")


if __name__ == "__main__":
    cli_app()
