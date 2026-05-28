# Generate

The `generate` command allows you to generate speech from text directly from the command line using Kyutai Pocket TTS.

## Basic Usage

```bash
# From the repo root:
uv run pocket-tts generate
```

This will generate a WAV file `./tts_output.wav` with the default text and voice.

## Command Options

### Core Options

- `--text TEXT`: Text to generate (default: "Hello world! I am Kyutai Pocket TTS. I'm fast enough to run on small CPUs. I hope you'll like me.")
- `--voice VOICE`: Path to audio conditioning file (voice to clone). Defaults to a built-in voice chosen from the language: `giovanni` (it) for italian, `lola` (es) for spanish, `juergen` (de) for german, `rafael` (pt) for portuguese, `estelle` (fr) for french, `alba` (en) otherwise. Urls and local paths are supported.
- `--output-path OUTPUT_PATH`: Output path for generated audio (default: "./tts_output.wav")
- `--language LANGUAGE`: Language for the TTS model, one of `'english_2026-01'`, `'english_2026-04'`, `'english'`, `'french_24l'`, `'german'`, `'german_24l'`, `'portuguese'`, `'portuguese_24l'`, `'italian'`, `'italian_24l'`, `'spanish'`, `'spanish_24l'` (default: `english`, which is the same model as `'english_2026-04'`). Incompatible with `--config`. The "24l" variants are bigger models, not distilled yet and here only as preview.

### Generation Parameters

- `--config CONFIG_PATH`: Path to custom config.yaml (for loading local model files). Incompatible with `--language`.
- `--lsd-decode-steps LSD_DECODE_STEPS`: Number of generation steps (default: 1)
- `--temperature TEMPERATURE`: Temperature for generation (default: 0.7)
- `--noise-clamp NOISE_CLAMP`: Noise clamp value (default: None)
- `--eos-threshold EOS_THRESHOLD`: EOS threshold (default: -4.0)
- `--frames-after-eos FRAMES_AFTER_EOS`: Number of frames to generate after EOS (default: None, auto-calculated based on the text length). Each frame is 80ms.

### Performance Options

- `--device DEVICE`: Device to use (default: "cpu", you may not get a speedup by using a gpu since it's a small model)
- `--quantize`: Use int8 quantization for the model (default: False). This can reduce memory usage and increase speed, with minimal impact on audio quality.
- `--quiet`, `-q`: Disable logging output

## Examples

### Basic Generation

```bash
# Generate with default settings

# Custom text

# Custom output path
```

### Voice Selection

```bash
# Use different voice from HuggingFace

# Use local voice file

# Use a safetensors file (such as one created using `pocket-tts export-voice`)
```

### Quality Tuning

```bash
# Higher quality (more steps)

# More expressive (higher temperature)

# Adjust EOS threshold, smaller means finishing earlier.
```

### Custom Model Config

If you'd like to override the paths from which the models are loaded, you can provide a custom YAML configuration.

Copy one of the files in `pocket_tts/config` (for example `pocket_tts/config/english.yaml`) and change `weights_path`, `weights_path_without_voice_cloning`, and `tokenizer_path` to the paths of the models you want to load.

Then, use the --config option to point to your newly created config.

```bash
# Use a different config
```

## Output Format

The generate command always outputs WAV files in the following format:

- **Sample Rate**: 24kHz
- **Channels**: Mono
- **Bit Depth**: 16-bit PCM
- **Format**: Standard WAV file

For more advanced usage, see the [Python API documentation](python-api.md) or consider using the [serve command](serve.md) for web-based generation and quick iteration.
