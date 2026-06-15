from __future__ import annotations

from pathlib import Path

from .frontmatter import read_mdx
from .intros import format_intro
from .nav import collect_asyncapi_sources, collect_openapi_sources, collect_pages, tab_display_name
from .spec import endpoint_description, load_openapi


def entry_line(title: str, url: str, description: str, max_desc: int = 300) -> str:
    """
    Format a single page or endpoint entry for an llms.txt file.

    Each entry is a markdown link followed by a short description, for example:

        - [What is NexusOne?](https://docs.example.com/documentation/what-is-example.md): Overview of the platform.

    The generator caps descriptions at 300 characters. If a description is empty,
    the generator writes the entry without the colon and description part.
    """
    if description:
        desc = description[:max_desc] + ("…" if len(description) > max_desc else "")
        return f"- [{title}]({url}): {desc}"
    return f"- [{title}]({url})"


def spec_entry_lines(sources: list[str], base_url: str) -> list[str]:
    """Build llms.txt entries that link directly to spec files."""
    lines = []
    for source in sources:
        clean = source.lstrip("/")
        spec_url = f"{base_url.rstrip('/')}/{clean}"
        spec_title = Path(clean).stem
        lines.append(entry_line(spec_title, spec_url, ""))
    return lines


def generate_navigation(
    tab: dict,
    docs_root: Path,
    base_url: str,
    navigation_name: str,
    navigation_folder: str,
    intro=None,
) -> tuple:
    """
    Build the llms.txt content for one docs navigation. For example, a tab navigation might have
    a Documentation or API reference tab.

    Page paths come from the docs.json navigation entry passed in as `tab`. For each
    path, the generator reads the matching `.mdx` file locally to get the page title
    and description from its frontmatter. API endpoint pages have an
    `openapi: METHOD /path` frontmatter field instead of a description, so the
    generator looks up their descriptions in the local OpenAPI spec file.

    Each navigation gets its own llms.txt file with this structure:

        # Documentation

        > Optional intro text from llms-txt-intros.json.

        ## Docs
        - [Page title](URL): description from the page's frontmatter

        ## OpenAPI Specs
        - [Endpoint title](URL): first-line description from the OpenAPI spec
        - [openapi](URL)

        ## AsyncAPI Specs
        - [asyncapi](URL)

    OpenAPI tabs list endpoint pages in navigation. The generator puts those
    pages under `## OpenAPI Specs` and looks up each endpoint's description in the
    local spec file.

    When a tab or group declares OpenAPI or AsyncAPI specs in docs.json without
    endpoint pages, the generator links directly to each spec file. OpenAPI and
    AsyncAPI specs always render in separate sections, even when both are present
    in the same tab.

    All other tabs only get a `## Docs` section sourced from their MDX page
    frontmatter.

    Returns the navigation name and the file content as a string.
    """
    name = tab_display_name(tab)

    # Load a local OpenAPI spec for endpoint page descriptions.
    openapi_spec = load_openapi(docs_root / navigation_folder)

    pages: list = []
    collect_pages(tab.get("pages", tab.get("groups", [])), pages)

    doc_lines = []
    openapi_lines = []
    asyncapi_lines = []

    for page in pages:
        clean = page.lstrip("/")
        url = f"{base_url.rstrip('/')}/{clean}.md"
        fm = read_mdx(docs_root / f"{clean}.mdx")
        title = fm.get("title") or clean.split("/")[-1].replace("-", " ").title()

        openapi_ref = fm.get("openapi", "")
        if openapi_ref and openapi_spec:
            # Use OpenAPI spec as the canonical description source
            parts = openapi_ref.split(None, 1)
            description = endpoint_description(openapi_spec, parts[0], parts[1]) if len(parts) == 2 else ""
            openapi_lines.append(entry_line(title, url, description))
        else:
            doc_lines.append(entry_line(title, url, fm.get("description", "")))

    # Link directly to spec files declared in navigation when there are no
    # generated endpoint pages for that spec type.
    openapi_sources: list = []
    collect_openapi_sources(tab, openapi_sources)
    if openapi_sources and not openapi_lines:
        openapi_lines.extend(spec_entry_lines(openapi_sources, base_url))

    asyncapi_sources: list = []
    collect_asyncapi_sources(tab, asyncapi_sources)
    if asyncapi_sources and not asyncapi_lines:
        asyncapi_lines.extend(spec_entry_lines(asyncapi_sources, base_url))

    lines = [f"# {name}", ""]
    if intro:
        lines += [format_intro(intro), ""]
    if doc_lines:
        lines += ["## Docs", ""] + doc_lines + [""]
    if openapi_lines:
        lines += ["## OpenAPI Specs", ""] + openapi_lines + [""]
    if asyncapi_lines:
        lines += ["## AsyncAPI Specs", ""] + asyncapi_lines + [""]

    return navigation_name, "\n".join(lines).strip() + "\n"


def generate_root(
    site_name: str,
    intro: str,
    navigation: list,
    base_url: str,
) -> str:
    """
    Build the root llms.txt file that serves as the top-level index for the site.

    The root file links to each navigation's own llms.txt so that AI tools can
    discover all available documentation from a single entry point. Its structure
    follows the llms.txt standard:

        # NexusOne

        > Short description of the documentation site.

        - [Documentation](https://docs.example.com/documentation/llms.txt)
        - [Tutorials](https://docs.example.com/tutorials/llms.txt)
        - [API reference](https://docs.example.com/api-reference/llms.txt)

    The site name comes from the "name" field in docs.json. The intro comes
    from the "root" key in llms-txt-intros.json, or falls back to home.mdx.
    """
    lines = [f"# {site_name}", ""]
    if intro:
        lines += [format_intro(intro), ""]
    for display_name, folder in navigation:
        url = f"{base_url.rstrip('/')}/{folder}/llms.txt"
        lines.append(f"- [{display_name}]({url})")
    lines.append("")
    return "\n".join(lines).strip() + "\n"
