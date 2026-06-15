from __future__ import annotations

import hashlib
import json
from pathlib import Path


def compute_hashes(outputs: dict) -> dict:
    """
    Compute a SHA-256 hash for each generated file content.

    Takes a dict of relative path strings to content strings and returns
    a new dict with the same keys mapped to their SHA-256 hex digests. Compare
    the result against load_hash_cache() output to detect whether any llms.txt
    file has changed since the last run.
    """
    return {
        path: hashlib.sha256(content.encode()).hexdigest()
        for path, content in outputs.items()
    }


def load_hash_cache(cache_path: Path) -> dict:
    """
    Load previously stored file hashes from the cache file.

    Returns an empty dict if the cache file doesn't exist yet. On the first
    run, the generator treats all files as new and writes them.
    """
    if not cache_path.exists():
        return {}
    return json.loads(cache_path.read_text())


def save_hash_cache(cache_path: Path, hashes: dict):
    """
    Write the current file hashes to the cache file for future comparisons.

    The cache file is a plain JSON object mapping relative file paths to their
    SHA-256 hex digests. Keep it alongside the generated llms.txt files so the
    next run can find it.
    """
    cache_path.write_text(json.dumps(hashes, indent=2) + "\n")
