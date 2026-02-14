# Pocket TTS

<img width="1446" height="622" alt="pocket-tts-logo-v2-transparent" src="https://github.com/user-attachments/assets/637b5ed6-831f-4023-9b4c-741be21ab238" />

A lightweight text-to-speech (TTS) application designed to run efficiently on CPUs.
Forget about the hassle of using GPUs and web APIs serving TTS models. With Kyutai's Pocket TTS, generating audio is just a pip install and a function call away.

Supports Python 3.10, 3.11, 3.12, 3.13 and 3.14. Requires PyTorch 2.5+. Does not require the gpu version of PyTorch.

[🔊 Demo](https://kyutai.org/pocket-tts) | 
[🐱‍💻GitHub Repository](https://github.com/kyutai-labs/pocket-tts) | 
[🤗 Hugging Face Model Card](https://huggingface.co/kyutai/pocket-tts) | 
[⚙️ Tech report](https://kyutai.org/blog/2026-01-13-pocket-tts) |
[📄 Paper](https://arxiv.org/abs/2509.06926) | 
[📚 Documentation](https://github.com/kyutai-labs/pocket-tts/tree/main/docs)


## Main takeaways
* Runs on CPU
* Small model size, 100M parameters
* Audio streaming
* Low latency, ~200ms to get the first audio chunk
* Faster than real-time, ~6x real-time on a CPU of MacBook Air M4
* Uses only 2 CPU cores
* OpenAI-compatible HTTP API and CLI
* Voice cloning
* English only at the moment
* Can handle infinitely long text inputs
* [Can run on client-side in the browser](#in-browser-implementations)

More languages are planned: See our [official announcement](https://github.com/kyutai-labs/pocket-tts/issues/118)

## Trying it from the website, without installing anything

Navigate to the [Kyutai website](https://kyutai.org/pocket-tts) to try it out directly in your browser. You can input text, select different voices, and generate speech without any installation.

## Trying it with the CLI

### The `generate` command
You can use pocket-tts directly from the command line. We recommend using
`uv` as it installs any dependencies on the fly in an isolated environment (uv installation instructions [here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)).
You can also use `pip install pocket-tts` to install it manually.

This will generate a wav file `./tts_output.wav` saying the default text with the default voice, and display some speed statistics.
```bash
uvx pocket-tts generate
# or if you installed it manually with pip:
pocket-tts generate
```
Modify the voice with `--voice` and the text with `--text`. We provide a small catalog of voices.

You can take a look at [this page](https://huggingface.co/kyutai/tts-voices) which details the licenses
for each voice.

* [alba](https://huggingface.co/kyutai/tts-voices/blob/main/alba-mackenna/casual.wav)
* [marius](https://huggingface.co/kyutai/tts-voices/blob/main/voice-donations/Selfie.wav)
* [javert](https://huggingface.co/kyutai/tts-voices/blob/main/voice-donations/Butter.wav)
* [jean](https://huggingface.co/kyutai/tts-voices/blob/main/ears/p010/freeform_speech_01.wav)
* [fantine](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p244_023.wav)
* [cosette](https://huggingface.co/kyutai/tts-voices/blob/main/expresso/ex04-ex02_confused_001_channel1_499s.wav)
* [eponine](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p262_023.wav)
* [azelma](https://huggingface.co/kyutai/tts-voices/blob/main/vctk/p303_023.wav)

The `--voice` argument can also take a plain wav file as input for voice cloning.
You can use your own or check out our [voice repository](https://huggingface.co/kyutai/tts-voices).
We recommend [cleaning the sample](https://podcast.adobe.com/en/enhance) before using it with Pocket TTS, because the audio quality of the sample is also reproduced.

Feel free to check out the [generate documentation](https://github.com/kyutai-labs/pocket-tts/tree/main/docs/generate.md) for more details and examples.
For trying multiple voices and prompts quickly, prefer using the `serve` command.

### The `serve` command

You can also run a local server to generate audio via HTTP requests.
```bash
uvx pocket-tts serve
# or if you installed it manually with pip:
pocket-tts serve
```
Navigate to `http://localhost:8000` to try the web interface, it's faster than the command line as the model is kept in memory between requests.

You can check out the [serve documentation](https://github.com/kyutai-labs/pocket-tts/tree/main/docs/serve.md) for more details and examples.

### Docker / Podman

You can also run the server using Docker or Podman:

```bash
# Using Docker
docker compose up -d

# Using Podman
podman compose up -d
```

Navigate to `http://localhost:8000` to access the web interface.

### OpenAI-Compatible API

The server also provides an OpenAI-compatible TTS endpoint at `/v1/audio/speech`:

```bash
# Start the server
uvx pocket-tts serve

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

Processing an audio file (e.g., a .wav or .mp3) for voice cloning is relatively slow, but loading a safetensors file -- a voice embedding converted from an audio file -- is very fast. You can use the `export-voice` command to do this conversion. See the [export-voice documentation](https://github.com/kyutai-labs/pocket-tts/tree/main/docs/export_voice.md) for more details and examples.


## Unsupported features

At the moment, we do not support (but would love pull requests adding):

- [Adding silence in the text input to generate pauses.](https://github.com/kyutai-labs/pocket-tts/issues/6)
- [Quantization to run the computation in int8.](https://github.com/kyutai-labs/pocket-tts/issues/7)

We tried running this TTS model on the GPU but did not observe a speedup compared to CPU execution,
notably because we use a batch size of 1 and a very small model.

## Development and local setup

We accept contributions! Feel free to open issues or pull requests on GitHub.

You can find development instructions in the [CONTRIBUTING.md](https://github.com/kyutai-labs/pocket-tts/tree/main/CONTRIBUTING.md) file. You'll also find there how to have an editable install of the package for local development.

## In-browser implementations

Pocket TTS is small enough to run directly in your browser in WebAssembly/JavaScript.
We don't have official support for this yet, but you can try out one of these community implementations:

- [pocket-tts-onnx-export](https://github.com/KevinAHM/pocket-tts-onnx-export) by @KevinAHM: Model exported to .onnx and run using [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/). Demo [here](https://huggingface.co/spaces/KevinAHM/pocket-tts-web)
- [pocket-tts](https://github.com/babybirdprd/pocket-tts) by @babybirdprd: Candle version (Rust) with WebAssembly and PyO3 bindings, meaning it can run on the web too.
- [jax-js](https://github.com/ekzhang/jax-js/tree/main/website/src/routes/tts) by @ekzhang: Using jax-js, a ML library for the web. Demo [here](https://jax-js.com/tts)


## Alterative implementations
- [pocket-tts-mlx](https://github.com/jishnuvenugopal/pocket-tts-mlx) by @jishnuvenugopal - MLX backend optimized for Apple Silicon
- [pocket-tts](https://github.com/babybirdprd/pocket-tts) by @babybirdprd - Candle version (Rust) with WebAssembly and PyO3 bindings.

## Projects using Pocket TTS

- [pocket-reader](https://github.com/lukasmwerner/pocket-reader) by @lukasmwerner- Browser screen reader
- [pocket-tts-wyoming](https://github.com/ikidd/pocket-tts-wyoming) by @ikidd - Docker container for pocket-tts using Wyoming protocol, ready for Home Assistant Voice use.
- [Sonorus](https://www.nexusmods.com/hogwartslegacy/mods/2409) by @KevinAHM - Talk to any named character in Hogwarts Legacy with their original voice.
- [Mac pocket-tts](https://github.com/slaughters85j/pocket-tts) by @slaughters85j - Mac Desktop App + macOS Quick Action
- [pocket-tts-openai_streaming_server](https://github.com/teddybear082/pocket-tts-openai_streaming_server) by @teddybear082 - OpenAI-compatible streaming server, dockerized and with an `.exe` release
- [pocket-tts-unity](https://github.com/lookbe/pocket-tts-unity) by @lookbe - A Unity 6 integration for Pocket-TTS.

## Prohibited use

Use of our model must comply with all applicable laws and regulations and must not result in, involve, or facilitate any illegal, harmful, deceptive, fraudulent, or unauthorized activity. Prohibited uses include, without limitation, voice impersonation or cloning without explicit and lawful consent; misinformation, disinformation, or deception (including fake news, fraudulent calls, or presenting generated content as genuine recordings of real people or events); and the generation of unlawful, harmful, libelous, abusive, harassing, discriminatory, hateful, or privacy-invasive content. We disclaim all liability for any non-compliant use.


## Authors

Manu Orsini*, Simon Rouard*, Gabriel De Marmiesse*, Václav Volhejn, Neil Zeghidour, Alexandre Défossez

*equal contribution
