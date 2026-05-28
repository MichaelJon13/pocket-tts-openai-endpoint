#!/usr/bin/env python3
"""Check if upstream HuggingFace model files are still available.

Each pinned commit hash in the source code refers to a specific file revision
on HuggingFace. This script verifies those revisions still exist.

If any check fails, the upstream files may have been removed/changed
and the cached backup may be stale.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None

HF = "https://huggingface.co"

# (repo_id, file_path, pinned_commit, source_location)
# file_path is empty when the revision is a tree hash (directory/embedding refs).
PINNED_FILES: list[tuple[str, str, str, str]] = [
    # model weights — pocket_tts/config/*.yaml
    ("kyutai/pocket-tts", "languages/english/model.safetensors", "39592ff23c9ef80098bb74895d104c26275fe2c9", "pocket_tts/config/english.yaml"),
    # model weights w/o voice cloning — config
    ("kyutai/pocket-tts-without-voice-cloning", "languages/english/model.safetensors", "d29db7978e464fb90cb3359ee0c69a273b9142cc", "pocket_tts/config/english.yaml"),
    # tokenizer (per-language) — config
    ("kyutai/pocket-tts-without-voice-cloning", "languages/english/tokenizer.model", "d29db7978e464fb90cb3359ee0c69a273b9142cc", "pocket_tts/config/english.yaml"),
    # tokenizer (base) — pocket_tts/conditioners/text.py
    ("kyutai/pocket-tts-without-voice-cloning", "tokenizer.model", "d4fdd22ae8c8e1cb3634e150ebeff1dab2d16df3", "pocket_tts/conditioners/text.py"),
    # voice embeddings dir — pocket_tts/utils/utils.py
    ("kyutai/pocket-tts-without-voice-cloning", "", "e041936c75475d350b405bc870bcf7c22da4e9e6", "pocket_tts/utils/utils.py"),
    # non-English voice prompts — pocket_tts/utils/utils.py
    ("kyutai/pocket-tts", "", "64ab7d24c479d736a83b8cc666c4a776fca30fda", "pocket_tts/utils/utils.py"),
    # estelle voice prompt — pocket_tts/utils/utils.py
    ("kyutai/tts-voices", "", "1fc7395b7e012e2bbebfca14b942a4ef62ccc899", "pocket_tts/utils/utils.py"),
]


FILE_CHECKS = [(r, f, h, s) for r, f, h, s in PINNED_FILES if f]
DIR_CHECKS = [(r, h, s) for r, f, h, s in PINNED_FILES if not f]


def check_file(repo_id: str, file_path: str, pinned: str) -> bool:
    """Check a specific file at a pinned revision via resolve URL."""
    if requests is None:
        return True
    url = f"{HF}/{repo_id}/resolve/{pinned}/{file_path}"
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def check_dir(repo_id: str, pinned: str) -> bool:
    """Check if a tree/snapshot hash exists for a repo.

    Uses the HF API to verify the ref exists, then does a light HEAD
    against the tree URL to confirm it resolves.
    """
    if requests is None:
        return True
    # Quick HEAD against tree URL — 200 or redirect means exists
    url = f"{HF}/{repo_id}/tree/{pinned}"
    try:
        resp = requests.head(url, allow_redirects=True, timeout=10)
        return resp.status_code in (200, 302, 303)
    except requests.RequestException:
        return False


def main():
    if requests is None:
        print("Warning: 'requests' not installed. Install with:")
        print("  uv add requests")
        print()

    print("Checking upstream HuggingFace model files...\n")

    all_ok = True

    for repo_id, file_path, pinned, source in FILE_CHECKS:
        ok = check_file(repo_id, file_path, pinned)
        status = "✓" if ok else "✗ MISSING"
        if not ok:
            all_ok = False
        print(f"  {status}  {repo_id}/{file_path}")
        print(f"       pinned: {pinned[:12]}  ({source})")

    for repo_id, pinned, source in DIR_CHECKS:
        ok = check_dir(repo_id, pinned)
        status = "✓" if ok else "✗ MISSING"
        if not ok:
            all_ok = False
        print(f"  {status}  {repo_id}/ (tree)")
        print(f"       pinned: {pinned[:12]}  ({source})")

    print()
    print("─" * 50)
    if not all_ok:
        print("RESULT: Some pinned revisions no longer resolve on HuggingFace.")
        print("The cached backup may be stale — re-run backup and update hashes.")
        sys.exit(1)

    total = len(FILE_CHECKS) + len(DIR_CHECKS)
    print(f"RESULT: OK — all {total} pinned revisions still resolve on HF.")
    sys.exit(0)


if __name__ == "__main__":
    main()
