# Export Voice

Kyutai Pocket TTS allows you to generate speech with voice cloning from an audio sample. However, processing an audio file each time is relatively slow and inefficient.

The `export-voice` command allows you to convert an audio file to a voice embedding (it's actually the kvcache) in safetensors format. The safetensors file can then be loaded very quickly whenever you generate speech.

## Basic Usage

```bash
# From the repo root:
uv run pocket-tts export-voice audio-path export-path
```

Only the first 30 seconds of the audio file will be processed.

## Command Options

### Required Parameters

- `audio-path`: Path of the audio file to convert. `audio-path` can point to an `http:` or `hf:` (hugging face) file. Supports popular audio file formats like wav and mp3.
- `export-path`: Path of the output safetensors file to write.

### Options

- `--quiet`: Do not print any output except errors.
- `--language`: Language for the TTS model, one of `'english_2026-01'`, `'english_2026-04'`, `'english'`, `'french_24l'`, `'german_24l'`, `'portuguese_24l'`, `'italian_24l'`, `'spanish_24l'` (default: `english`, which is the same model as `'english_2026-04'`). Incompatible with `--config`. The "24l" variants are bigger models, not distilled yet and here only as preview.
- `--config`: Model config local yaml path. Incompatible with `--language`.

## Examples

```bash
# export a single file

# export an online file to current directory

# use the exported safetensors
```
