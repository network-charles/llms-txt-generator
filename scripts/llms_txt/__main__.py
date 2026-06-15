#!/usr/bin/env python3
"""
llms.txt generator for Mintlify documentation sites.

Reads docs.json and generates:
  - A root llms.txt that links to each navigation's llms.txt
  - A per-navigation llms.txt with page descriptions under ## Docs
  - An ## OpenAPI Specs or ## AsyncAPI Specs navigation for API reference tabs

Setup:
  # Install dependencies and activate the virtual environment
  uv sync
  source .venv/bin/activate

Usage:
  # Generate for all navigation found in docs.json
  python3 scripts/llms_txt --base-url https://docs.example.com

  # Preview without writing files
  python3 scripts/llms_txt \
    --base-url https://docs.example.com \
    --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add the scripts/ folder to Python's search path so all sibling modules
# are importable when running this file directly.
sys.path.insert(0, str(Path(__file__).parent.parent))

from llms_txt.cache import compute_hashes, load_hash_cache, save_hash_cache
from llms_txt.frontmatter import read_mdx
from llms_txt.intros import get_intro, load_intros
from llms_txt.nav import detect_nav_type, find_shared_root, infer_folder, tab_display_name
from llms_txt.render import generate_root, generate_navigation


def main():
    parser = argparse.ArgumentParser(
        description="Generate llms.txt files for a Mintlify docs site.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate for all navigation found in docs.json
  python scripts/llms_txt --base-url https://docs.example.com

  # Preview without writing files
  python scripts/llms_txt \
      --base-url https://docs.example.com \
      --dry-run

  # Custom docs root, for when docs.json isn't in the current directory
  python scripts/llms_txt \
      --base-url https://docs.example.com \
      --docs-root ./docs
        """,
    )
    parser.add_argument(
        "--base-url",
        required=True,
        help="Public URL of your docs site, for example https://docs.example.com",
    )
    parser.add_argument(
        "--docs-root",
        default=".",
        help="Path to the docs root that contains docs.json. Defaults to the current directory.",
    )
    parser.add_argument(
        "--nav-type",
        choices=["tabs", "anchors", "groups", "pages"],
        help="Navigation type to use. Auto-detected from docs.json if omitted.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated content without writing any files",
    )

    args = parser.parse_args()

    # ── Load docs.json ────────────────────────────────────────────────────────
    # docs.json is the Mintlify config file that defines the site name and the
    # full navigation structure. Everything else is derived from it.
    docs_root = Path(args.docs_root).resolve()
    docs_json_path = docs_root / "docs.json"

    if not docs_json_path.exists():
        sys.exit(f"Error: docs.json not found at {docs_json_path}")

    config = json.loads(docs_json_path.read_text())
    site_name = config.get("name", "Documentation")
    nav = config.get("navigation", {})

    # Mintlify supports several navigation styles. Detect which one this site uses
    # so we know how to iterate the navigation entries below.
    nav_type = args.nav_type or detect_nav_type(nav)
    print(f"Site: {site_name}")
    print(f"Navigation type: {nav_type}")

    # If the navigation uses versioning then tabs are inside each
    # version, so we loop through all versions and collect all
    # tabs into one flat list.
    if "versions" in nav:
        items = []
        for version in nav["versions"]:
            items.extend(version.get("tabs", []))
    else:
        # If there is no versioning, use the detected navigation type directly
        items = nav.get(nav_type, [])

    # If nothing was found, stop the program because the config is invalid or empty
    if not items:
        sys.exit(f"Error: no '{nav_type}' entries found in navigation")

    # Expand versioned tabs, Mintlify `versions` structure, into one synthetic
    # tab per version so the rest of the pipeline treats each version separately.
    expanded = []
    for item in items:
        if "versions" in item:
            base_name = tab_display_name(item)
            for version in item["versions"]:
                expanded.append({
                    "tab": f"{base_name} {version['version']}",
                    "groups": version.get("groups", []),
                })
        else:
            expanded.append(item)
    items = expanded

    # ── Load intro text ───────────────────────────────────────────────────────
    # llms-txt-intros.json holds the short description that appears at the top
    # of each navigation's llms.txt. The "root" key is used for the root llms.txt.
    intros = load_intros(docs_root / "llms-txt-intros.json")
    root_intro = intros.get("root") or read_mdx(docs_root / "home.mdx").get("description", "")

    # ── Generate per-navigation llms.txt files ───────────────────────────────────
    # Some sites nest navigation under a shared folder such as public/. Detect
    # that prefix once so each navigation's name and output path resolve correctly.
    print()
    shared_root = find_shared_root(items)
    root_len = len(shared_root)
    navigation = []
    outputs = {}  # maps each relative output path to its generated content

    for item in items:
        # Determine which folder this tab's pages live under, for example documentation/.
        # Tabs with no subfolder, like the Home tab, are skipped.
        full_folder = infer_folder(item)
        if full_folder is None:
            continue

        # Strip the shared root prefix to get the navigation name used for intro
        # lookups and API detection. For example, public/documentation → documentation.
        navigation_parts = full_folder.split("/")
        navigation_name = navigation_parts[root_len] if root_len < len(navigation_parts) else navigation_parts[-1]

        # The output folder is capped at shared root + navigation name so the file
        # lands at documentation/llms.txt, not documentation/getting-started/llms.txt.
        navigation_folder = "/".join(navigation_parts[: root_len + 1])

        display_name = tab_display_name(item)
        navigation_intro = get_intro(intros, navigation_folder)
        _, content = generate_navigation(
            item, docs_root, args.base_url,
            navigation_name=navigation_name, navigation_folder=navigation_folder, intro=navigation_intro,
        )
        if not content:
            continue

        navigation.append((display_name, navigation_folder))
        outputs[f"{navigation_folder}/llms.txt"] = content

    # ── Generate root llms.txt ────────────────────────────────────────────────
    # The root file is the top-level index that links to every navigation's llms.txt.
    # AI crawlers start here to discover all available documentation.
    root_content = generate_root(site_name, root_intro, navigation, args.base_url)
    outputs["llms.txt"] = root_content

    # ── Dry run: print instead of writing ─────────────────────────────────────
    if args.dry_run:
        for rel_path, content in outputs.items():
            out_path = docs_root / rel_path
            separator = "=" * 60
            print(f"{separator}\n{out_path}\n{separator}\n{content}")
        return

    # ── Hash check: skip writing if nothing changed ───────────────────────────
    # Compare a SHA-256 hash of the new output against the last saved hashes.
    # If they match, the content hasn't changed and there is nothing to write.
    cache_path = docs_root / "llms-txt-cache.json"
    new_hashes = compute_hashes(outputs)
    old_hashes = load_hash_cache(cache_path)

    if new_hashes == old_hashes:
        print("No changes detected. Skipping.")
        sys.exit(0)

    # ── Write llms.txt files to their navigation folders ────────────────────────
    for rel_path, content in outputs.items():
        out_path = docs_root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        print(f"  Wrote {out_path.relative_to(docs_root)}")

    save_hash_cache(cache_path, new_hashes)
    print(f"\nDone. Generated {len(navigation)} navigation + root llms.txt")


if __name__ == "__main__":
    main()
