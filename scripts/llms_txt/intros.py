from __future__ import annotations

import json
import sys
from pathlib import Path


def get_intro(intros: dict, navigation_folder: str):
    """
    Look up the intro text for a navigation by its folder path.

    Supports wildcard keys for versioned docs where each version lives in its
    own subfolder, such as `docs/v1.0` and `docs/v1.1`, while all versions share
    the same intro. Use a key in the form `docs/*` to match all versions at
    once instead of listing each version explicitly.

    The lookup order is:

    1. Exact match on the full folder path, for example "documentation".
    2. Wildcard match. For example, `docs/*` matches `docs/v1.0`,
    `docs/v1.1`, and similar paths.

    Returns None if no match exists.
    """
    if navigation_folder in intros:
        return intros[navigation_folder]
    for key, value in intros.items():
        if key.endswith("/*"):
            prefix = key[:-2]
            if navigation_folder == prefix or navigation_folder.startswith(prefix + "/"):
                return value
    return None


def format_intro(text) -> str:
    """
    Format intro text as a blockquote for an llms.txt file.

    The llms.txt standard uses a leading ">" to mark the site or navigation
    description, for example:

        > NexusOne is a unified data control plane for modern data teams.

    This function accepts either a plain string or a list of strings.
    In both cases, all lines join into one paragraph under a single `>`.
    """
    if isinstance(text, list):
        paragraph = " ".join(str(line).strip() for line in text if str(line).strip())
    else:
        paragraph = " ".join(text.strip().splitlines())
    return f"> {paragraph}"


def load_intros(intros_file: Path) -> dict:
    """
    Load the intro text for each navigation from llms-txt-intros.json in the docs root.

    Each entry uses a folder name as the key, matching the top-level folder of
    each docs navigation. The value is either a plain string or a list of strings
    for multi-sentence intros. A special `root` key sets the intro for the root
    `llms.txt` file. For example:

        {
          "root": "NexusOne is a unified data control plane."
        }
    """
    if not intros_file.exists():
        sys.exit(f"Error: llms-txt-intros.json not found at {intros_file}")
    return json.loads(intros_file.read_text())
