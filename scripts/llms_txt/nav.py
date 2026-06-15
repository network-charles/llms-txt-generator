from __future__ import annotations


def collect_pages(node, out: list):
    """
    Walk a navigation node and collect every page path string into `out`.

    Mintlify navigation is deeply nested. A tab contains groups, groups contain
    sub-groups, and sub-groups contain page paths. This function recurses through
    whatever structure it finds until it reaches the plain string paths at the leaves.
    """
    if isinstance(node, str):
        # Reached a page path. Add it to the results.
        out.append(node)
    elif isinstance(node, list):
        # A list of items. Walk each one.
        for item in node:
            collect_pages(item, out)
    elif isinstance(node, dict):
        # A group or tab object. Go deeper via its "pages" key.
        collect_pages(node.get("pages", []), out)


def find_shared_root(items: list) -> list:
    """
    Find path segments shared by two or more navigation items.

    Some docs sites nest most pages under a common root folder, for example
    `public/documentation/...` and `public/tutorials/...`, while keeping others
    like `api-reference/...` at the top level. This function looks at the first
    page path across all tabs and returns segments where the same value appears
    in more than one tab, for example `["public"]`. The result tells `main` how
    many leading segments to strip from a tab's folder path to get the navigation
    name used for output files and intro lookups.

    Returns an empty list when no segment appears in more than one tab, meaning
    pages are already at the top level.
    """
    first_pages = []
    for item in items:
        pages: list = []
        collect_pages(item.get("pages", item.get("groups", [])), pages)
        if pages:
            first_pages.append(pages[0].lstrip("/").split("/"))

    if not first_pages:
        return []

    common = []
    for segments in zip(*first_pages):
        mode = max(set(segments), key=segments.count)
        if segments.count(mode) > 1:
            common.append(mode)
        else:
            break
    return common


def openapi_source_path(openapi) -> str | None:
    """
    Return the spec file path from a Mintlify `openapi` navigation value.

    Mintlify accepts either a string path or an object with a `source` field
    when a group declares its own OpenAPI spec.
    """
    if isinstance(openapi, str):
        return openapi
    if isinstance(openapi, dict):
        return openapi.get("source")
    return None


def asyncapi_source_path(asyncapi) -> str | None:
    """
    Return the spec file path from a Mintlify `asyncapi` navigation value.

    Mintlify accepts either a string path or an object with a `source` field
    when a group declares its own AsyncAPI spec.
    """
    if isinstance(asyncapi, str):
        return asyncapi
    if isinstance(asyncapi, dict):
        return asyncapi.get("source")
    return None


def collect_openapi_sources(node, out: list):
    """
    Walk a navigation node and collect every OpenAPI spec source path into `out`.

    Sources can be declared on a tab or on individual groups. Group-level
    declarations use an object with `source` and `directory` keys.
    """
    if isinstance(node, list):
        for item in node:
            collect_openapi_sources(item, out)
    elif isinstance(node, dict):
        source = openapi_source_path(node.get("openapi"))
        if source:
            out.append(source)
        for key in ("groups", "pages"):
            collect_openapi_sources(node.get(key, []), out)


def collect_asyncapi_sources(node, out: list):
    """
    Walk a navigation node and collect every AsyncAPI spec source path into `out`.

    Sources can be declared on a tab or on individual groups.
    """
    if isinstance(node, list):
        for item in node:
            collect_asyncapi_sources(item, out)
    elif isinstance(node, dict):
        source = asyncapi_source_path(node.get("asyncapi"))
        if source:
            out.append(source)
        for key in ("groups", "pages"):
            collect_asyncapi_sources(node.get(key, []), out)


def collect_spec_sources(tab: dict) -> list[str]:
    """Return every OpenAPI and AsyncAPI spec source path declared in a tab."""
    sources: list = []
    collect_openapi_sources(tab, sources)
    collect_asyncapi_sources(tab, sources)
    return sources


def spec_folder_from_paths(paths: list[str]) -> str | None:
    """
    Return the folder path shared by one or more spec file paths.

    For a single path such as `/api-reference/openapi.json`, returns
    `api-reference`. For multiple paths, returns their longest common prefix.
    """
    if not paths:
        return None

    all_parts = [path.lstrip("/").split("/") for path in paths]
    if len(all_parts) == 1:
        parts = all_parts[0]
        return "/".join(parts[:-1]) if len(parts) > 1 else None

    common = []
    for segments in zip(*all_parts):
        if len(set(segments)) == 1:
            common.append(segments[0])
        else:
            break

    if common:
        return "/".join(common)

    parts = all_parts[0]
    return "/".join(parts[:-1]) if len(parts) > 1 else None


def tab_spec_path(tab: dict) -> str | None:
    """
    Return the first spec file path declared on an API tab in docs.json, if any.

    AsyncAPI tabs often have no endpoint pages. Mintlify points at the spec file
    directly via an `asyncapi` or `openapi` key instead of listing pages.
    """
    sources = collect_spec_sources(tab)
    return sources[0] if sources else None


def infer_folder(tab: dict) -> str | None:
    """
    Return the folder path where this navigation's `llms.txt` file gets saved.

    For a flat layout, `documentation/getting-started/foo` returns `documentation`,
    so the file saves to `documentation/llms.txt`. For a nested layout where tabs
    share a root folder, `public/documentation/foo` returns `public/documentation`,
    so the file saves to `public/documentation/llms.txt`.

    For multiple pages the prefix is the longest path segment sequence shared by
    all pages in the tab. For a single page, it is all segments except the
    filename.

    Tabs like the Home tab have pages at the root with no subfolder, for
    example just `home`. This function skips those tabs by returning None,
    since there is no meaningful folder to generate an `llms.txt` for.

    AsyncAPI-only tabs with no pages fall back to the folder in their spec path,
    for example `/api-reference/asyncapi.yaml` → `api-reference`.
    """
    pages: list = []
    collect_pages(tab.get("pages", tab.get("groups", [])), pages)
    if not pages:
        folder = spec_folder_from_paths(collect_spec_sources(tab))
        if folder:
            return folder
        return None

    parts = pages[0].lstrip("/").split("/")

    if len(parts) <= 1:
        # Root-level page with no subfolder. Skip it.
        return None

    if len(pages) == 1:
        # Only one page in this tab, so there is nothing to compare for a common prefix.
        # Use all path segments except the last one, which is the filename.
        # For example, documentation/overview/introduction → documentation/overview.
        return "/".join(parts[:-1])

    # Multiple pages: find the longest prefix shared by all page paths.
    # For example, documentation/ai/overview and documentation/ai/tasks
    # share documentation/ai, so the folder is documentation/ai.
    all_parts = [p.lstrip("/").split("/") for p in pages]
    common = []
    for segments in zip(*all_parts):
        if len(set(segments)) == 1:
            common.append(segments[0])
        else:
            break

    # If a shared prefix was found, return it as a path. If no segments matched,
    # fall back to the first segment of the first page, for example documentation.
    return "/".join(common) if common else parts[0]


def detect_nav_type(nav: dict) -> str:
    """
    Detect which navigation style the docs.json file uses.

    Mintlify supports several top-level navigation patterns. The most common
    is tabs, which creates a row of tabs across the top of the site. Others
    include anchors for pinned sidebar links, groups for a flat grouped sidebar,
    and pages for a simple flat list. This function checks which key is present
    in the navigation object and returns it so the rest of the script knows
    how to iterate the structure.

    If the entire docs is versioned, it goes one level deeper to get the
    navigation style.
    """

    # If the navigation is versioned, inspect each version separately.
    if "versions" in nav:
        for version in nav["versions"]:
            for key in ("tabs", "anchors", "groups", "pages"):
                if key in version:
                    return key

    # If there is no versioning, check the top-level navigation object
    # for known navigation types.
    for key in ("tabs", "anchors", "groups", "pages"):
        if key in nav:
            return key
    
    # Default fallback when no known navigation structure is detected.
    return "pages"


def tab_display_name(tab: dict) -> str:
    """
    Return the human-readable name of a navigation item.

    Depending on the navigation type, Mintlify stores the name under a different key.
    A tab uses `tab`, an anchor uses `anchor`, and a group uses `group`.
    This function tries each in order and returns the first one it finds.
    """
    return tab.get("tab") or tab.get("anchor") or tab.get("group", "")
