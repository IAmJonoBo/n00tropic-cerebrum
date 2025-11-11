#!/usr/bin/env python3
"""
n00 Docs MCP Server

Provides read-only access to n00 Cerebrum documentation via MCP tools.
"""

import json
import re
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: fastmcp not installed. Install with: pip install mcp")
    raise

mcp = FastMCP("n00-docs")

# Paths
DOCS_ROOT = Path(__file__).parent.parent.parent / "docs"
BUILD_SITE = Path(__file__).parent.parent.parent / "build" / "site"


def extract_tags_from_file(filepath: Path) -> list[str]:
    """Extract page-tags from an AsciiDoc file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        match = re.search(r'^:page-tags:\s*(.+)$', content, re.MULTILINE)
        if match:
            tags_str = match.group(1)
            # Split by comma and clean up
            return [tag.strip() for tag in tags_str.split(',')]
        return []
    except Exception:
        return []


@mcp.tool()
def list_tags() -> list[str]:
    """
    List all unique tags from documentation pages.
    
    Returns:
        Sorted list of unique tags found across all documentation pages.
    """
    tags = set()
    
    # Scan all .adoc files in docs/modules
    if DOCS_ROOT.exists():
        for adoc_file in DOCS_ROOT.glob("modules/**/pages/**/*.adoc"):
            file_tags = extract_tags_from_file(adoc_file)
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
    
    if not DOCS_ROOT.exists():
        return results
    
    # Simple grep-like search through .adoc files
    for adoc_file in DOCS_ROOT.glob("modules/**/pages/**/*.adoc"):
        try:
            content = adoc_file.read_text(encoding="utf-8")
            
            # Check if query matches
            if query_lower not in content.lower():
                continue
            
            # Extract title (first line starting with =)
            title_match = re.search(r'^=\s+(.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else adoc_file.stem
            
            # Extract tags
            tags = extract_tags_from_file(adoc_file)
            
            # Build relative path for URL
            rel_path = adoc_file.relative_to(DOCS_ROOT / "modules" / "ROOT" / "pages")
            page_id = str(rel_path.with_suffix(''))
            
            results.append({
                "id": page_id,
                "title": title,
                "url": f"/{page_id}.html",
                "tags": tags,
                "score": content.lower().count(query_lower)  # Simple scoring
            })
        except Exception:
            continue
    
    # Sort by score (descending)
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
    # Try to get HTML from build
    html_path = BUILD_SITE / f"{id}.html"
    if html_path.exists():
        try:
            html_content = html_path.read_text(encoding="utf-8")
            return {
                "id": id,
                "format": "html",
                "content": html_content
            }
        except Exception as e:
            pass
    
    # Fall back to AsciiDoc source
    adoc_path = DOCS_ROOT / "modules" / "ROOT" / "pages" / f"{id}.adoc"
    if adoc_path.exists():
        try:
            adoc_content = adoc_path.read_text(encoding="utf-8")
            
            # Extract metadata
            title_match = re.search(r'^=\s+(.+)$', adoc_content, re.MULTILINE)
            title = title_match.group(1) if title_match else id
            tags = extract_tags_from_file(adoc_path)
            
            return {
                "id": id,
                "format": "asciidoc",
                "title": title,
                "tags": tags,
                "content": adoc_content
            }
        except Exception as e:
            return {
                "id": id,
                "error": f"Failed to read file: {str(e)}"
            }
    
    return {
        "id": id,
        "error": "Page not found"
    }


if __name__ == "__main__":
    mcp.run()
