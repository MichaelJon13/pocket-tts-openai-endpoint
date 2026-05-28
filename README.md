# Pocket TTS

<img width="1446" height="622" alt="pocket-tts-logo-v2-transparent" src="https://github.com/user-attachments/assets/637b5ed6-831f-4023-9b4c-741be21ab238" />

A lightweight text-to-speech (TTS) application designed to run efficiently on CPUs.
Forget about the hassle of using GPUs and web APIs serving TTS models. With Kyutai's Pocket TTS, generating audio is just a function call away.

Supports Python 3.10, 3.11, 3.12, 3.13 and 3.14. Requires PyTorch 2.5+. Does not require the gpu version of PyTorch.

[🔊 Demo](https://kyutai.org/pocket-tts) | 
[🐱‍💻GitHub Repository](https://github.com/MichaelJon13/pocket-tts-openai-endpoint) | 
[🤗 Hugging Face Model Card](https://huggingface.co/kyutai/pocket-tts) | 
[⚙️ Tech report](https://kyutai.org/blog/2026-01-13-pocket-tts) |
[📄 Paper](https://arxiv.org/abs/2509.06926) | 
[📚 Documentation](https://kyutai-labs.github.io/pocket-tts/)


## Main takeaways
* Runs on CPU
* Small model size, 100M parameters
* Audio streaming
* Low latency, ~200ms to get the first audio chunk
* Faster than real-time, ~6x real-time on a CPU of MacBook Air M4
* Uses only 2 CPU cores
* OpenAI-compatible HTTP API and CLI
* Voice cloning
* Multi-language support: english, french, german, portuguese, italian, spanish
* Can handle infinitely long text inputs
* [Can run on client-side in the browser](#in-browser-implementations)

Additional languages may be added in the future.

## Trying it from the website, without installing anything

Navigate to the [Kyutai website](https://kyutai.org/pocket-tts) to try it out directly in your browser. You can input text, select different voices, and generate speech without any installation.

## Trying it with the CLI

### The `generate` command
You can use pocket-tts directly from the command line with `uv` (installation instructions [here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)).

This will generate a wav file `./tts_output.wav` saying the default text with the default voice, and display some speed statistics.
```bash
# From the repo root:
uv run pocket-tts generate
# or if installed locally:
uv run pocket-tts generate
```
Modify the voice with `--voice` and the text with `--text`. We provide a small catalog of voices.
Choose a pretrained language model with `--language` when running `generate`, `export-voice`, or `serve` (default: `english`). Non-english languages have also biggers 24 layers variants that are higher quality but slower. You can select them by using for example `--language italian_24l`.
The `--config` option accepts only a local YAML path for custom weights.

You can take a look at [this page](https://huggingface.co/kyutai/tts-voices) which details the licenses
for each voice.

* [alba](https://huggingface.co/kyutai/tts-voices/blob/main/alba-mackenna/casual.wav) (en)
* [giovanni](https://huggingface.co/kyutai/pocket-tts/blob/add_lang_not_documented/common_voice_it_36520747-enhanced-v2.mp3) (it)
* [lola](https://huggingface.co/kyutai/pocket-tts/blob/add_lang_not_documented/common_voice_es_19762977-enhanced-v2.mp3) (es)
* [juergen](https://huggingface.co/kyutai/pocket-tts/blob/add_lang_not_documented/de-DE-juergen.mp3) (de)
* [rafael](https://huggingface.co/kyutai/pocket-tts/blob/add_lang_not_documented/g-Vi8PgmSY0-enhanced-v2.wav) (pt)
* [estelle](https://huggingface.co/kyutai/tts-voices/blob/main/unmute-prod-website/developpeuse-3.wav) (fr)
* [anna](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p228_023_enhanced.wav) (en)
* [azelma](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p303_023_enhanced.wav) (en)
* [bill_boerst](https://huggingface.co/kyutai/tts-voices/blob/main/voice-zero/bill_boerst.wav) (en)
* [caro_davy](https://huggingface.co/kyutai/tts-voices/blob/main/voice-zero/caro_davy.wav) (en)
* [charles](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p254_023_enhanced.wav) (en)
* [cosette](https://huggingface.co/kyutai/tts-voices/blob/main/expresso/ex04-ex02_confused_001_channel1_499s.wav) (en)
* [eponine](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p262_023_enhanced.wav) (en)
* [eve](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p361_023_enhanced.wav) (en)
* [fantine](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p244_023_enhanced.wav) (en)
* [george](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p315_023_enhanced.wav) (en)
* [jane](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p339_023_enhanced.wav) (en)
* [jean](https://huggingface.co/kyutai/tts-voices/blob/main/ears/p010/freeform_speech_01_enhanced.wav) (en)
* [javert](https://huggingface.co/kyutai/tts-voices/blob/main/voice-donations/Butter.wav) (en)
* [marius](https://huggingface.co/kyutai/tts-voices/blob/main/voice-donations/Selfie.wav) (en)
* [mary](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p333_023_enhanced.wav) (en)
* [michael](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p360_023_enhanced.wav) (en)
* [paul](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p259_023_enhanced.wav) (en)
* [peter_yearsley](https://huggingface.co/kyutai/tts-voices/blob/main/voice-zero/peter_yearsley.wav) (en)
* [stuart_bell](https://huggingface.co/kyutai/tts-voices/blob/main/voice-zero/stuart_bell.wav) (en)
* [vera](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p229_023_enhanced.wav) (en)

The `--voice` argument can also take a plain wav file as input for voice cloning.
You can use your own or check out our [voice repository](https://huggingface.co/kyutai/tts-voices).
We recommend [cleaning the sample](https://podcast.adobe.com/en/enhance) before using it with Pocket TTS, because the audio quality of the sample is also reproduced.

Feel free to check out the [generate documentation](docs/CLI%20Commands/generate.md) for more details and examples.
For trying multiple voices and prompts quickly, prefer using the `serve` command.

### The `serve` command

You can run a local server to generate audio via HTTP requests and access a web interface.
```bash
# From the repo root:
uv run pocket-tts serve --host 0.0.0.0 --port 8000 --quantize --language english
```

**Options:**
* `--host`: Host to bind to (default: `localhost`, use `0.0.0.0` in containers).
* `--port`: Port to bind to (default: `8000`).
* `--language`: Model language, e.g., `english`, `french_24l`, `german_24l`, `portuguese`, `italian`, `spanish` (default: `english`).
* `--quantize`: Apply int8 quantization using `torchao` to reduce memory and CPU footprint.

Navigate to `http://127.0.0.1:8000` to try the web interface. It's faster than the command line as the model is kept in memory between requests.

You can check out the [serve documentation](docs/CLI%20Commands/serve.md) for more details and examples.

### Docker / Podman

Voice cloning requires the gated model weights. To access them:
1. Create a Hugging Face account and accept the terms on the [Pocket TTS Model Card](https://huggingface.co/kyutai/pocket-tts).
2. Generate a Hugging Face Access Token (`HF_TOKEN`).

Create a `.env` file (ignored by git):
```env
HF_TOKEN=your_hugging_face_token_here
```

The `docker-compose.yaml` reads `HF_TOKEN` from `.env` automatically:
```bash
docker compose up -d
# or
podman-compose up -d
```

For rootless environments (like Podman), use `http://127.0.0.1:8000` instead of `localhost` to avoid IPv6 conflicts.

Run directly:
```bash
podman run -d \
  --name pocket-tts-openai \
  -p 8000:8000 \
  -e HF_TOKEN=your_huggingface_token_here \
  -v pocket_tts_cache:/root/.cache/pocket_tts \
  -v hf_cache:/root/.cache/huggingface \
  localhost/pocket-tts-openai:latest
```

Run locally with `.env`:
```bash
export $(cat .env | xargs) && uv run pocket-tts serve
```

### OpenAI-Compatible API

The server also provides an OpenAI-compatible TTS endpoint at `/v1/audio/speech`:

```bash
# Start the server (from the repo root, or install locally first)
uv run pocket-tts serve

# Call the API (in another terminal)
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1",
    "input": "Hello world, this is a test!",
    "voice": "alloy"
  }' --output speech.wav
```

**Supported parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `input` | string | Required | Text to synthesize (max 4096 chars) |
| `model` | string | `"tts-1"` | Model identifier (any value accepted) |
| `voice` | string | `"alloy"` | Voice: alloy, ash, ballad, coral, echo, fable, onyx, nova, sage, shimmer, verse, marin, cedar |
| `response_format` | string | `"wav"` | Output format: wav, mp3, opus, aac, flac, pcm |
| `speed` | float | `1.0` | Playback speed: 0.25 to 4.0 |
| `stream_format` | string | `"audio"` | Streaming: "audio" or "sse" |

**Voice mapping:**

| OpenAI Voice | Pocket-TTS Voice |
|--------------|------------------|
| alloy | alba |
| ash | marius |
| ballad | javert |
| coral | jean |
| echo | fantine |
| fable | cosette |
| onyx | eponine |
| nova | azelma |
| sage | alba |
| shimmer | marius |
| verse | javert |
| marin | jean |
| cedar | fantine |

### API Authentication (Optional)

API keys can be optionally required for the `/v1/audio/speech` endpoint.

**Enable API keys:**

```bash
# Using Docker/Podman with environment variable
REQUIRE_API_KEYS=true ADMIN_API_KEY=my-admin-key podman compose up -d
```

**Get your API keys:**

```bash
# Requires admin key in Authorization header
curl -H "Authorization: Bearer my-admin-key" http://localhost:8000/v1/auth
```

Response:
```json
{
  "enabled": true,
  "message": "API keys are required",
  "keys": ["bzgjzmYtckg4skm9I9wuLJtanlXOUMF9", ...]
}
```

**Use API key in requests:**

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": "Hello world!",
    "voice": "alloy"
  }' --output speech.wav
```

**How it works:**
- API keys are stored in `/root/.cache/pocket_tts/api_keys.json`
- Keys persist across container restarts (stored in volume)
- 3 API keys are generated on first startup
- Keys are 32-character random strings
- Set `ADMIN_API_KEY` env var to protect the `/v1/auth` endpoint

### The `export-voice` command

Processing an audio file (e.g., a .wav or .mp3) for voice cloning is relatively slow, but loading a safetensors file -- a voice embedding converted from an audio file -- is very fast. You can use the `export-voice` command to do this conversion. See the [export-voice documentation](docs/CLI%20Commands/export_voice.md) for more details and examples.

### Chat Completions with Voice

The server provides an LLM proxy endpoint at `/v1/chat/completions` that sends your messages to any OpenAI-compatible backend and optionally speaks the response using pocket-tts.

**Non-streaming** returns full LLM text + base64 WAV audio:
```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":"Say hello in 5 words."}],
    "stream": false,
    "voice": "alloy",
    "llm_base_url": "http://localhost:11434/v1",
    "llm_model": "gpt-oss:20b"
  }' | jq '.choices[0].message.content'
```

**Streaming** emits SSE events — each sentence is TTS-synthesized as it arrives:
```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages":[{"role":"user","content":"Tell me a fun fact about space."}],
    "stream": true,
    "voice": "alloy",
    "llm_base_url": "http://localhost:11434/v1",
    "llm_model": "gpt-oss:20b"
  }'
```

Events:
- `{"type": "text", "content": "..."}` — a completed sentence
- `{"type": "audio", "content": "<base64 wav>", "text": "..."}` — audio for that sentence
- `{"type": "done"}` — end of stream

**Configuration:**

The LLM backend defaults to `OPENAI_BASE_URL` / `OPENAI_API_KEY` env vars, or can be set per-request:

| Field | Default | Description |
|-------|---------|-------------|
| `llm_base_url` | `OPENAI_BASE_URL` or `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `llm_api_key` | `OPENAI_API_KEY` | API key for the LLM |
| `llm_model` | (same as `model`) | Model name to use at the LLM |
| `voice` | `"alloy"` | TTS voice for the response |
| `tts_enabled` | `true` | Set to `false` for text-only streaming |

### List Voices

```bash
curl http://localhost:8000/v1/audio/voices | jq .
```


## Using it as a Python library

You can try out the upstream Python library on Colab [here](https://colab.research.google.com/github/kyutai-labs/pocket-tts/blob/main/docs/pocket-tts-example.ipynb).

Install the package from this repo:
```bash
git clone https://github.com/MichaelJon13/pocket-tts-openai-endpoint.git
cd pocket-tts-openai-endpoint
uv sync
```

You can use this package as a simple Python library to generate audio from text.
```python
from pocket_tts import TTSModel
import scipy.io.wavfile

tts_model = TTSModel.load_model()
voice_state = tts_model.get_state_for_audio_prompt(
    "alba"  # One of the pre-made voices, see above
    # You can also use any voice file you have locally or from Hugging Face:
    # "./some_audio.wav"
    # or "hf://kyutai/tts-voices/expresso/ex01-ex02_default_001_channel2_198s.wav"
)
audio = tts_model.generate_audio(voice_state, "Hello world, this is a test.")
# Audio is a 1D torch tensor containing PCM data.
scipy.io.wavfile.write("output.wav", tts_model.sample_rate, audio.numpy())
```

You can have multiple voice states around if
you have multiple voices you want to use. `load_model()`
and `get_state_for_audio_prompt()` are relatively slow operations,
so we recommend to keep the model and voice states in memory if you can.

For faster voice loading, you can export voice states to safetensors files:
```python
from pocket_tts import TTSModel, export_model_state

model = TTSModel.load_model()

# Export a voice state for fast loading later
model_state = model.get_state_for_audio_prompt("some_voice.wav")
export_model_state(model_state, "./some_voice.safetensors")

# Later, load it quickly, this is quite fast as it's just reading the kvcache
# from disk and doesn't do any others computations.
model_state_copy = model.get_state_for_audio_prompt("./some_voice.safetensors")

audio = model.generate_audio(model_state_copy, "Hello world!")
```

You can check out the [Python API documentation](docs/API%20Reference/python-api.md) for more details and examples.

## Offline backup (model weights are downloaded from HuggingFace)

On first run, pocket-tts downloads model weights, tokenizer, and voice samples from
HuggingFace Hub. If those files are ever removed from HuggingFace, new installs
would fail — but existing cached copies continue working indefinitely.

To ensure portability to a new machine, back up these two directories:

```bash
# ~490 MB — model weights, tokenizer, voice embeddings per language
~/.cache/huggingface/

# ~1 MB — cached voice prompts
~/.cache/pocket_tts/
```

**Backup:**
```bash
tar czf pocket-tts-cache.tar.gz \
  ~/.cache/huggingface/hub/models--kyutai--pocket-tts-without-voice-cloning \
  ~/.cache/huggingface/hub/models--kyutai--tts-voices \
  ~/.cache/pocket_tts/
```

**Restore on a new machine:**
```bash
# Extract before first run
tar xzf pocket-tts-cache.tar.gz -C ~/
```

The cache directories are read-only after extraction — no HF token needed.

## Unsupported features

At the moment, we do not support (but would love pull requests adding):

- [Adding silence in the text input to generate pauses.](https://github.com/kyutai-labs/pocket-tts/issues/6)

We tried running this TTS model on the GPU but did not observe a speedup compared to CPU execution,
notably because we use a batch size of 1 and a very small model.

## Development and local setup

We accept contributions! Feel free to open issues or pull requests on GitHub.

You can find development instructions in the [CONTRIBUTING.md](CONTRIBUTING.md) file. You'll also find there how to have an editable install of the package for local development.

## In-browser implementations

Pocket TTS is small enough to run directly in your browser in WebAssembly/JavaScript.
We don't have official support for this yet, but you can try out one of these community implementations:
- [wasm-pocket-tts](https://github.com/LaurentMazare/xn/tree/main/wasm-pocket-tts) by @LaurentMazare: Rust port of pocket TTS with XN. Demo [here](https://laurentmazare.github.io/pocket-tts/)
- [pocket-tts-onnx-export](https://github.com/KevinAHM/pocket-tts-onnx-export) by @KevinAHM: Model exported to .onnx and run using [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/). Demo [here](https://huggingface.co/spaces/KevinAHM/pocket-tts-web)
- [pocket-tts](https://github.com/babybirdprd/pocket-tts) by @babybirdprd: Candle version (Rust) with WebAssembly and PyO3 bindings, meaning it can run on the web too.
- [jax-js](https://github.com/ekzhang/jax-js/tree/main/website/src/routes/tts) by @ekzhang: Using jax-js, a ML library for the web. Demo [here](https://jax-js.com/tts)


## Alternative implementations
- [pocket-tts-mlx](https://github.com/jishnuvenugopal/pocket-tts-mlx) by @jishnuvenugopal - MLX backend optimized for Apple Silicon
- [pocket-tts-xn](https://github.com/LaurentMazare/xn/tree/main/pocket-tts) by @LaurentMazare - A Rust port of Pocket TTS implemented with XN.
- [pocket-tts-candle](https://github.com/babybirdprd/pocket-tts) by @babybirdprd - Candle version (Rust) with WebAssembly and PyO3 bindings.
- [PocketTTS.cpp](https://github.com/VolgaGerm/PocketTTS.cpp) by @VolgaGerm - Single-file C++ runtime using ONNX Runtime, with CLI, HTTP server, and FFI C API.
- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) by @csukuangfj - Run PocketTTS on **Windows, macOS, Linux**, and embedded boards (Raspberry Pi, Jetson, RK3588, etc.) with bindings for 12 programming languages: **C++, C, Python, JavaScript, Java, C#, Kotlin, Swift, Go, Dart, Rust, Pascal**, plus [WebAssembly](https://huggingface.co/spaces/k2-fsa/web-assembly-en-tts-pocket).
- [pocket-tts-csharp](https://github.com/TheAjaykrishnanR/pocket-tts-csharp) by @TheAjaykrishnanR - A C# port of Pocket TTS implemented using [TorchSharp](https://github.com/dotnet/TorchSharp) and [TorchSharp.PyBridge](https://github.com/shaltielshmid/TorchSharp.PyBridge) for ease of use as a library in .NET projects.

## Projects using Pocket TTS

- [pocket-reader](https://github.com/lukasmwerner/pocket-reader) by @lukasmwerner- Browser screen reader
- [pocket-tts-wyoming](https://github.com/ikidd/pocket-tts-wyoming) by @ikidd - Docker container for pocket-tts using Wyoming protocol, ready for Home Assistant Voice use.
- [Sonorus](https://www.nexusmods.com/hogwartslegacy/mods/2409) by @KevinAHM - Talk to any named character in Hogwarts Legacy with their original voice.
- [Mac pocket-tts](https://github.com/slaughters85j/pocket-tts) by @slaughters85j - Mac Desktop App + macOS Quick Action
- [Native macOS App](https://github.com/slaughters85j/pocket-tts-macos) by @slaughters85j - Native macOS app, Python-free. Runs Pocket-TTS via Core ML, fully on-device. Includes signed and notarized .app releases.
- [pocket-tts-openai_streaming_server](https://github.com/teddybear082/pocket-tts-openai_streaming_server) by @teddybear082 - OpenAI-compatible streaming server, dockerized and with an `.exe` release
- [pocket-tts-unity](https://github.com/lookbe/pocket-tts-unity) by @lookbe - A Unity 6 integration for Pocket-TTS.
- [ComfyUI-Pocket-TTS](https://github.com/ai-joe-git/ComfyUI-Pocket-TTS) by @ai-joe-git Lightweight CPU-based Text-to-Speech for ComfyUI
- [pocket-tts-server](https://github.com/ai-joe-git/pocket-tts-server) by @ai-joe-git A lightweight, real-time voice cloning and chat server with OpenAI-compatible API. Clone any voice with just 20 seconds of audio and chat with AI using that voice instantly.
- [discord-tts](https://github.com/alkmei/discord-tts) by @alkmei - Multivoice Discord text-to-speech bot that uses Pocket TTS.
- [cursed-codex](https://github.com/dooart/cursed-codex) by @dooart - AI coding agent with unhinged live football commentary
- [pocket-tts-deno](https://github.com/ohmstone/pocket-tts-deno) Port of [pocket-tts-server](https://github.com/ai-joe-git/pocket-tts-server) as a wasm + onnx deno server with voice TTS API.
- [FrontPocket](https://github.com/markd89/FrontPocket) by @markd89 - Front-end for Pocket-TTS to speak text from clipboard, file, CLI (hotkeys) & GUI toolbar. Change playback speed, voice, and move forward/backward between sentences instantaneously. 
- [openclaw-pockettts](https://github.com/dodgyrabbit/openclaw-pockettts) by @dodgyrabbit - A Docker container with the Python implementation but exposed as an OpenAI TTS API for easy integration with OpenClaw.
- [openclaw-pocketts.cpp](https://github.com/dodgyrabbit/openclaw-pockettts.cpp) by @dodgyrabbit - A Docker container with the PocketTTS.cpp version, packaged for easy integration with OpenClaw.
- [tts-audiobook-tool](https://github.com/zeropointnine/tts-audiobook-tool) by @zeropointnine - Multi-model audiobook generator with automatic error detection, 48khz upscaling, synced browser reader, stand-alone server-mode.


## Prohibited use

Use of our model must comply with all applicable laws and regulations and must not result in, involve, or facilitate any illegal, harmful, deceptive, fraudulent, or unauthorized activity. Prohibited uses include, without limitation, voice impersonation or cloning without explicit and lawful consent; misinformation, disinformation, or deception (including fake news, fraudulent calls, or presenting generated content as genuine recordings of real people or events); and the generation of unlawful, harmful, libelous, abusive, harassing, discriminatory, hateful, or privacy-invasive content. We disclaim all liability for any non-compliant use.


## Authors

Manu Orsini*, Simon Rouard*, Gabriel De Marmiesse*, Václav Volhejn, Neil Zeghidour, Alexandre Défossez

*equal contribution
