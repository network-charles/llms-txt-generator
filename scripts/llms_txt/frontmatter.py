from __future__ import annotations

import re
from pathlib import Path


def parse_frontmatter(text: str) -> dict:
    """
    Parse the YAML frontmatter block at the top of a Mintlify MDX page file.

    Mintlify MDX files begin with a frontmatter block delimited by triple dashes.
    This block holds metadata like the page title and description, for example:

        ---
        title: "Overview"
        description: "A short summary of this page."
        ---

    Some descriptions span multiple lines inside the same quoted string:

        ---
        description: "First line of a long
        description that continues here."
        ---

    This function reads that block and returns a plain dict of key-value pairs.
    The generator joins multi-line quoted values into a single string.
    """
    # MDX frontmatter is wrapped between two --- lines at the top of the file.
    # Capture everything between them as a single block of text.
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    result = {}
    lines = match.group(1).splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]

        if ":" in line:
            # Split on the first colon to separate the key from its value.
            # For example, title: "Overview" → key = title, value = "Overview".
            key, _, value = line.partition(":")
            value = value.strip()

            # Check whether the value opens with a quote character, either " or '.
            opening_quote = value[0] if value and value[0] in ('"', "'") else None

            # A value that starts with a quote but does not end with one spans
            # multiple lines. Keep reading until the closing quote is found,
            # then join all parts into one string.
            if opening_quote and not (len(value) > 1 and value.endswith(opening_quote)):
                parts = [value[1:]]  # drop the opening quote from the first line
                index += 1
                while index < len(lines):
                    continuation = lines[index].strip()
                    if continuation.endswith(opening_quote):
                        parts.append(continuation[:-1])  # drop the closing quote
                        break
                    parts.append(continuation)
                    index += 1
                value = " ".join(parts)
            else:
                # Single-line value: strip surrounding quotes if present.
                value = value.strip(opening_quote or "\"'")

            result[key.strip()] = value

        index += 1

    return result


def read_mdx(path: Path) -> dict:
    """
    Read a Mintlify MDX page file and return its frontmatter fields as a dict.

    Returns an empty dict if the file doesn't exist, so any function using
    this can safely call .get() on the result without extra checks.
    """
    if not path.exists():
        return {}
    return parse_frontmatter(path.read_text(encoding="utf-8"))
