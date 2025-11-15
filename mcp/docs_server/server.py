#!/usr/bin/env python3
"""
n00 Docs MCP Server

Provides read-only access to n00 Cerebrum documentation via MCP tools.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Install with: pip install mcp")
    raise

mcp = FastMCP("n00-docs")

# Paths
REPO_ROOT = Path(__file__).parent.parent.parent
IGNORE_PARTS = {".git", "node_modules", "build", "vendor", "dist", "tmp", "artifacts"}
DOCS_ROOT = REPO_ROOT / "docs"
BUILD_SITE = REPO_ROOT / "build" / "site"


def extract_tags_from_file(filepath: Path) -> list[str]:
    """Extract page-tags from an AsciiDoc file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        match = re.search(r"^:page-tags:\s*(.+)$", content, re.MULTILINE)
        if match:
            tags_str = match.group(1)
            # Split by comma and clean up
            return [tag.strip() for tag in tags_str.split(",")]
        return []
    except Exception:
        return []


def find_component_name(antora_file: Path) -> str:
    """Parse the Antora component name from an antora.yml file."""
    try:
        text = antora_file.read_text(encoding="utf-8")
    except OSError:
        return antora_file.parent.parent.name

    match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return antora_file.parent.parent.name


def discover_component_docs() -> Iterable[dict[str, Any]]:
    """Yield metadata for every Antora component in the workspace."""
    for antora_file in REPO_ROOT.glob("**/docs/antora.yml"):
        if any(part in IGNORE_PARTS for part in antora_file.parts):
            continue
        docs_dir = antora_file.parent
        modules_dir = docs_dir / "modules"
        if not modules_dir.is_dir():
            continue
        component_name = find_component_name(antora_file)
        yield {
            "name": component_name,
            "modules_dir": modules_dir,
            "docs_dir": docs_dir,
        }


def build_page_id(component: str, module: str, relative_path: Path) -> str:
    slug = relative_path.as_posix()
    if module and module != "ROOT":
        slug = f"{module}/{slug}" if slug else module
    return f"{component}::{slug}" if slug else f"{component}::index"


@lru_cache(maxsize=1)
def discover_pages() -> list[dict[str, Any]]:
    """Enumerate every AsciiDoc page across all Antora components."""
    pages: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for component in discover_component_docs():
        modules_dir: Path = component["modules_dir"]
        for page_file in modules_dir.glob("**/pages/**/*.adoc"):
            try:
                rel = page_file.relative_to(modules_dir)
            except ValueError:
                continue
            parts = list(rel.parts)
            if len(parts) < 3 or parts[1] != "pages":
                continue
            module_name = parts[0]
            page_rel = Path(*parts[2:]).with_suffix("")
            page_id = build_page_id(component["name"], module_name, page_rel)
            if page_id in seen_ids:
                continue
            pages.append(
                {
                    "id": page_id,
                    "component": component["name"],
                    "module": module_name,
                    "relative": page_rel,
                    "file": page_file,
                }
            )
            seen_ids.add(page_id)
    return pages


def find_page_by_id(page_id: str) -> dict[str, Any] | None:
    pages = discover_pages()
    for page in pages:
        if page["id"] == page_id:
            return page
    # Back-compat: allow ids without component prefix, assume root component
    if "::" not in page_id:
        for page in pages:
            slug = page["id"].split("::", maxsplit=1)[1]
            if slug == page_id:
                return page
    return None


@mcp.tool()
def list_tags() -> list[str]:
    """
    List all unique tags from documentation pages.

    Returns:
        Sorted list of unique tags found across all documentation pages.
    """
    tags = set()
    for page in discover_pages():
        file_tags = extract_tags_from_file(page["file"])
        tags.update(file_tags)
    return sorted(tags)


@mcp.tool()
def search(query: str) -> list[dict[str, Any]]:
    """
    Search documentation pages by query string.

    Args:
        query: Search query string

    Returns:
        List of matching pages with metadata (id, title, url, tags)
    """
    results = []
    query_lower = query.lower()

    for page in discover_pages():
        adoc_file = page["file"]
        try:
            content = adoc_file.read_text(encoding="utf-8")
        except Exception:
            continue

        lowered = content.lower()
        if query_lower not in lowered:
            continue

        title_match = re.search(r"^=\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else adoc_file.stem
        tags = extract_tags_from_file(adoc_file)
        slug = page["id"].split("::", maxsplit=1)[1]
        url_path = slug.replace(" ", "%20")
        results.append(
            {
                "id": page["id"],
                "title": title,
                "url": f"/{url_path}.html",
                "tags": tags,
                "component": page["component"],
                "module": page["module"],
                "score": lowered.count(query_lower),
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


@mcp.tool()
def get_page(id: str) -> dict[str, Any]:
    """
    Retrieve a documentation page by its ID.

    Args:
        id: Page identifier (relative path without extension)

    Returns:
        Dictionary with page metadata and content (HTML if built, AsciiDoc source otherwise)
    """
    page = find_page_by_id(id)
    if not page:
        return {"id": id, "error": "Page not found"}

    slug = page["id"].split("::", maxsplit=1)[1]
    html_path = BUILD_SITE / f"{slug}.html"
    if html_path.exists():
        try:
            html_content = html_path.read_text(encoding="utf-8")
            return {"id": page["id"], "format": "html", "content": html_content}
        except Exception:
            pass

    try:
        adoc_content = page["file"].read_text(encoding="utf-8")
    except Exception as exc:
        return {"id": page["id"], "error": f"Failed to read file: {exc}"}

    title_match = re.search(r"^=\s+(.+)$", adoc_content, re.MULTILINE)
    title = title_match.group(1) if title_match else slug
    tags = extract_tags_from_file(page["file"])

    return {
        "id": page["id"],
        "format": "asciidoc",
        "title": title,
        "tags": tags,
        "component": page["component"],
        "module": page["module"],
        "content": adoc_content,
    }


if __name__ == "__main__":
    mcp.run()
