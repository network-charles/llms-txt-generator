from __future__ import annotations

import json
import re
from pathlib import Path


def load_spec(directory: Path, filenames: list) -> dict | None:
    """
    Find and load the first matching spec file that exists in the docs folder.

    Supports JSON files with a `.json` extension and YAML files with `.yaml` or `.yml`
    extensions. The generator checks filenames in order and loads the first file it finds.

    If the matched file isn't a valid OpenAPI or AsyncAPI spec, the generator still
    loads it without an error. Description lookups return empty strings because
    the expected `paths` key won't be present.

    Returns None if none of the filenames exist in the folder.
    """
    import yaml

    for name in filenames:
        f = directory / name
        if not f.exists():
            continue
        text = f.read_text()
        if name.endswith(".json"):
            return json.loads(text)
        return yaml.safe_load(text)
    return None


def load_openapi(api_dir: Path) -> dict | None:
    """
    Load an OpenAPI spec from the API reference folder.

    OpenAPI is the standard format for describing REST API endpoints. Mintlify
    uses it to auto-generate API reference pages. The spec file is typically
    named openapi.json and lives at the root of the api-reference folder.
    This function supports both JSON and YAML formats.
    """
    return load_spec(api_dir, ["openapi.json", "openapi.yaml", "openapi.yml"])


def load_asyncapi(api_dir: Path) -> dict | None:
    """
    Load an AsyncAPI spec from the API reference folder.

    AsyncAPI is the equivalent of OpenAPI for event-driven or message-based APIs.
    Use this as a fallback when the generator finds no OpenAPI file.
    This function supports both JSON and YAML formats.
    """
    return load_spec(api_dir, ["asyncapi.json", "asyncapi.yaml", "asyncapi.yml"])


def first_line(text: str) -> str:
    """
    Extract the first meaningful sentence from an OpenAPI endpoint description.

    OpenAPI descriptions often contain rich markdown: bold text, inline code
    in backticks, and multi-paragraph explanations. Only the first line is
    useful for an llms.txt entry, and it needs to be plain text. This function
    skips blank lines, takes the first non-empty one, and strips all markdown
    formatting before returning it.
    """
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Remove double-backtick code spans: ``value`` → value
        line = re.sub(r"``([^`]+?)``", r"\1", line)
        # Remove single-backtick code spans: `value` → value
        line = re.sub(r"`([^`]+?)`", r"\1", line)
        # Remove bold markers: **value** → value
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        # Remove italic markers: *value* → value
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        return line
    return ""


def endpoint_description(spec: dict, method: str, path: str) -> str:
    """
    Look up a single API endpoint in the OpenAPI spec and return its description.

    In an OpenAPI spec, the `paths` key holds every endpoint. Each path
    has one or more HTTP methods such as get, post, or delete, and each method
    has a `description` and a `summary` field. This function reads the description
    first. If it's empty, it falls back to the summary. This then passes the result
    through `first_line` to strip markdown and return only the first sentence.
    """
    op = spec.get("paths", {}).get(path, {}).get(method.lower(), {})
    raw = op.get("description", "") or op.get("summary", "")
    return first_line(raw) if raw else ""
