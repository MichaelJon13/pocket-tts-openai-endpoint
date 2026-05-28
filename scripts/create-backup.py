#!/usr/bin/env python3
"""Create a portable tarball of all cached HuggingFace model files.

Downloads the legacy voice-cloning weights from HuggingFace if they aren't
already cached, then bundles everything into a single tarball with MANIFEST.md.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
from datetime import date
from pathlib import Path

CACHE = Path.home() / ".cache"

HF_DIRS = [
    "huggingface/hub/models--kyutai--pocket-tts",
    "huggingface/hub/models--kyutai--pocket-tts-without-voice-cloning",
    "huggingface/hub/models--kyutai--tts-voices",
]

HF_TOKEN_PATH = Path.cwd() / ".env"

LEGACY_REPO = "kyutai/pocket-tts"
LEGACY_COMMIT = "39592ff23c9ef80098bb74895d104c26275fe2c9"
LEGACY_FILE = "languages/english/model.safetensors"

LEGACY_BLOB_SHA = "473f47d99560bd50eb8b4509d3cacfe7f316ab20bdca86505403a2e6a936a6e9"

MANIFEST = """\
# pocket-tts model cache manifest

Created: {date}

This tarball contains all model weights, tokenizers, voice embeddings, and voice
prompts needed for pocket-tts. It mirrors the HuggingFace Hub cache format so you
can extract it directly to `~/.cache/` — no internet or HF token required.

## Contents

### `.cache/huggingface/hub/models--kyutai--pocket-tts/`  (legacy, voice cloning)
Legacy model weights with built-in voice cloning. Loaded via `weights_path`
in `pocket_tts/config/*.yaml`. If missing, the code falls back to the
`without-voice-cloning` variant and disables voice cloning.

### `.cache/huggingface/hub/models--kyutai--pocket-tts-without-voice-cloning/`  (primary)
Primary model weights, tokenizer, and per-language voice embeddings.

### `.cache/huggingface/hub/models--kyutai--tts-voices/`  (voice prompts)
Pre-recorded voice prompt wav files for built-in voices.

### `.cache/pocket_tts/`  (cached prompts)
Cached voice prompt audio downloaded from HuggingFace.

## Restore

```bash
tar xzf {filename} -C ~/
```

## Verification

Run `scripts/check-upstream-changes.py` to verify pinned HF revisions resolve.

## Upstream sources

- https://huggingface.co/kyutai/pocket-tts
- https://huggingface.co/kyutai/pocket-tts-without-voice-cloning
- https://huggingface.co/kyutai/tts-voices
"""


def get_hf_token() -> str | None:
    if HF_TOKEN_PATH.exists():
        for line in HF_TOKEN_PATH.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                return line.split("=", 1)[1].strip()
    return os.environ.get("HF_TOKEN")


def legacy_is_cached() -> bool:
    blob = CACHE / "huggingface" / "hub" / "models--kyutai--pocket-tts" / "blobs" / LEGACY_BLOB_SHA
    snapshot = (
        CACHE
        / "huggingface"
        / "hub"
        / "models--kyutai--pocket-tts"
        / "snapshots"
        / LEGACY_COMMIT
        / "languages"
        / "english"
        / "model.safetensors"
    )
    if not blob.exists() or not blob.is_file():
        return False
    if not snapshot.is_symlink():
        return False
    target = os.readlink(str(snapshot))
    expected = f"../../../blobs/{LEGACY_BLOB_SHA}"
    if target != expected:
        return False
    return bool(blob.stat().st_size)


def download_legacy_weights(token: str) -> None:
    import requests

    base_dir = CACHE / "huggingface" / "hub" / "models--kyutai--pocket-tts"
    blob_dir = base_dir / "blobs"
    snap_dir = base_dir / "snapshots" / LEGACY_COMMIT / "languages" / "english"
    refs_dir = base_dir / "refs"

    blob_dir.mkdir(parents=True, exist_ok=True)
    snap_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    url = (
        f"https://huggingface.co/{LEGACY_REPO}/resolve/{LEGACY_COMMIT}/{LEGACY_FILE}?download=1"
    )
    headers = {"Authorization": f"Bearer {token}"}

    print(f"  Downloading {LEGACY_REPO}/{LEGACY_FILE}...")
    resp = requests.get(url, headers=headers, stream=True, timeout=120)
    resp.raise_for_status()

    blob_path = blob_dir / LEGACY_BLOB_SHA
    with open(blob_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
            f.write(chunk)

    snapshot_symlink = snap_dir / "model.safetensors"
    rel = f"../../../blobs/{LEGACY_BLOB_SHA}"
    if snapshot_symlink.exists():
        snapshot_symlink.unlink()
    snapshot_symlink.symlink_to(rel)

    refs_file = refs_dir / "main"
    current = refs_file.read_text().strip() if refs_file.exists() else ""
    new_ref = "4c8ad48f8a003909bc4f1122cbe88a4252124621"
    if current != new_ref:
        refs_file.write_text(new_ref + "\n")

    print(f"  Downloaded {blob_path.stat().st_size / 1e6:.0f} MB")


def main():
    filename = f"pocket-tts-huggingface-model-cache-{date.today()}.tar.gz"

    out = Path.cwd() / filename

    missing_dirs = []
    for d in HF_DIRS:
        path = CACHE / d
        if not path.exists():
            missing_dirs.append(str(path))
    pocket_cache = CACHE / "pocket_tts"

    if missing_dirs:
        print("ERROR: Missing cache directories:")
        for m in missing_dirs:
            print(f"  {m}")
        print("Run `uv run pocket-tts generate --text test` first to populate cache.")
        sys.exit(1)

    token = get_hf_token()
    if not legacy_is_cached():
        if not token:
            print("ERROR: Legacy voice-cloning weights not cached and no HF_TOKEN found.")
            print("  Set HF_TOKEN in .env or environment to download them.")
            sys.exit(1)
        download_legacy_weights(token)
    else:
        print("  Legacy voice-cloning weights already cached, skipping download.")

    print(f"Creating {filename}...")

    with tarfile.open(str(out), "w:gz") as tar:
        for d in HF_DIRS:
            path = CACHE / d
            tar.add(str(path), arcname=f".cache/huggingface/hub/{d.split('/')[-1]}")

        if pocket_cache.exists():
            tar.add(str(pocket_cache), arcname=".cache/pocket_tts")

        manifest_content = MANIFEST.format(date=date.today(), filename=filename)
        info = tarfile.TarInfo(name="MANIFEST.md")
        data = manifest_content.encode("utf-8")
        info.size = len(data)
        tar.addfile(info, fileobj=__import__("io").BytesIO(data))

    size_mb = out.stat().st_size / 1e6
    print(f"Done — {filename} ({size_mb:.0f} MB)")

    archive_size = len(list(tarfile.open(str(out), "r:gz").getmembers()))
    print(f"  {archive_size} entries in archive")
    print(f"\nRestore on a new machine:\n  tar xzf {filename} -C ~/")


if __name__ == "__main__":
    main()
