# llms.txt generator

The `llms.txt` generator for Mintlify documentation sites reads the `docs.json` file and generates the following:

- A root `llms.txt` that links to each navigation's `llms.txt`
- A per-navigation `llms.txt` with 300 characters page descriptions under the `## Docs` section
- An `## OpenAPI Specs` or `## AsyncAPI Specs` section for API reference endpoint pages or multiple API files
- If your docs support versioning, it generates individual `llms.txt` files for each version
- `llms.txt` file hashes are available in [llms-txt-cache.json](../llms-txt-cache.json) and tracks changes

When you open a PR, you can use the [GitHub actions](.github/workflows/llms-txt-gen-check.yml) to verify if llms.txt files are out of date.

> Currently, this tool can't handle documentations grouped by [Products](https://www.mintlify.com/docs/organize/navigation#products).
It'll be added sometime in the future.

## Setup

1. Install dependencies and activate the virtual environment:

    ```bash
    uv sync
    source .venv/bin/activate
    ```

2. In [llms-txt-intros.json](llms-txt-intros.json), specify your `llms.txt` blockquote introduction for each Mintlify navigation in your documentation.

## Supported flags

Generate `llms_txt` outputs from a documentation site using a base URL, with optional flags for preview mode and custom docs location.

| Flag          | Purpose                                                   |
| ------------- | --------------------------------------------------------- |
| `--base-url`  | Sets the root URL used for generating documentation links |
| `--dry-run`   | Runs generation without writing files                     |
| `--docs-root` | Points to a custom directory containing `docs.json`       |

A few examples:

```bash
python scripts/llms_txt --base-url https://docs.example.com
```

```bash
python scripts/llms_txt \
  --base-url https://docs.example.com \
  --dry-run
```

```bash
python scripts/llms_txt \
  --base-url https://docs.example.com \
  --docs-root ./docs
```
