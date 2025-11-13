#!/usr/bin/env python3
"""
Script Index Generator for n00tropic Polyrepo

This script scans the entire workspace for executable scripts and organizes them
into a categorized index. It generates a Markdown file with sections for easy
navigation by agents and developers.

Usage:
    python generate_script_index.py

The generated index will be saved as 'script_index.md' in the current directory.
"""

import os
import pathlib
import re
from collections import defaultdict
from typing import Dict, List, Tuple

# Script extensions to look for
SCRIPT_EXTENSIONS = {
    ".sh",
    ".bash",
    ".zsh",
    ".fish",  # Shell scripts
    ".py",
    ".pyc",  # Python
    ".js",
    ".mjs",
    ".cjs",  # JavaScript
    ".ts",
    ".tsx",  # TypeScript
    ".rb",  # Ruby
    ".pl",
    ".pm",  # Perl
    ".php",  # PHP
    ".go",  # Go
    ".rs",  # Rust
    ".java",  # Java
    ".scala",  # Scala
    ".kt",  # Kotlin
    ".cs",  # C#
    ".cpp",
    ".cc",
    ".cxx",
    ".c++",  # C++
    ".c",  # C
    ".swift",  # Swift
    ".dart",  # Dart
    ".lua",  # Lua
    ".r",
    ".R",  # R
    ".sql",  # SQL (sometimes executable)
    ".ps1",  # PowerShell
    ".bat",
    ".cmd",  # Windows batch
}

# Directories to ignore
IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "venv",
    "env",
    ".env",
    "build",
    "dist",
    "target",
    "bin",
    "obj",
    ".next",
    ".nuxt",
    ".vuepress",
    "public",
    "static",
    "assets",
    "images",
    "docs",
    ".vscode",
    ".idea",
    ".DS_Store",
    "Thumbs.db",
}


def is_script_file(file_path: pathlib.Path) -> bool:
    """Check if a file is a script based on shebang or executable permission."""
    if os.access(file_path, os.X_OK):
        return True
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#!"):
                return True
    except OSError:
        pass
    return False


def get_script_description(file_path: pathlib.Path) -> str:
    """Extract description from script comments."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[:20]  # Read first 20 lines
            description = []
            for line in lines:
                line = line.strip()
                if line.startswith("#") and not line.startswith("#!"):
                    # Remove leading # and spaces
                    desc_line = re.sub(r"^#\s*", "", line)
                    if desc_line:
                        description.append(desc_line)
                elif line.startswith('"""') or line.startswith("'''"):
                    # Python docstring
                    docstring_lines = []
                    for next_line in lines[lines.index(line) + 1 :]:
                        if next_line.strip().endswith(
                            '"""'
                        ) or next_line.strip().endswith("'''"):
                            break
                        docstring_lines.append(next_line.strip())
                    description.extend(
                        docstring_lines[:3]
                    )  # First 3 lines of docstring
                    break
                elif line and not line.startswith("#"):
                    break  # Stop at first non-comment line
            return (
                " ".join(description).strip()
                if description
                else "No description available"
            )
    except OSError:
        return "Unable to read description"


def categorize_scripts(
    workspace_root: pathlib.Path,
) -> Dict[str, List[Tuple[pathlib.Path, str]]]:
    """Scan workspace and categorize scripts by their containing directory."""
    scripts_by_category = defaultdict(list)

    for root, dirs, files in os.walk(workspace_root):
        # Remove ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        root_path = pathlib.Path(root)
        # Determine category based on relative path from workspace root
        try:
            relative_path = root_path.relative_to(workspace_root)
            if relative_path == pathlib.Path("."):
                category = "Root Scripts"
            else:
                # Use the first part of the path as category
                category_parts = []
                for part in relative_path.parts:
                    if part not in IGNORE_DIRS and not part.startswith("."):
                        category_parts.append(part)
                        break
                category = (
                    "/".join(category_parts) if category_parts else "Miscellaneous"
                )
        except ValueError:
            category = "Miscellaneous"

        for file in files:
            file_path = root_path / file
            if is_script_file(file_path):
                description = get_script_description(file_path)
                scripts_by_category[category].append((file_path, description))

    # Sort scripts within each category by filename
    for category in scripts_by_category:
        scripts_by_category[category].sort(key=lambda x: x[0].name.lower())

    return dict(scripts_by_category)


def generate_markdown_index(
    scripts_by_category: Dict[str, List[Tuple[pathlib.Path, str]]],
    workspace_root: pathlib.Path,
) -> str:
    """Generate Markdown content for the script index."""
    lines = []
    lines.append("# n00tropic Polyrepo Script Index")
    lines.append("")
    lines.append(
        "This index automatically catalogs all scripts across the n00tropic polyrepo."
    )
    lines.append("Generated by `generate_script_index.py`.")
    lines.append("")
    lines.append(f"**Workspace Root:** `{workspace_root}`")
    lines.append(f"**Total Categories:** {len(scripts_by_category)}")
    total_scripts = sum(len(scripts) for scripts in scripts_by_category.values())
    lines.append(f"**Total Scripts:** {total_scripts}")
    lines.append("")
    lines.append("## Categories")
    lines.append("")

    # Table of contents
    for category in sorted(scripts_by_category.keys()):
        count = len(scripts_by_category[category])
        anchor = category.lower().replace("/", "-").replace(" ", "-")
        lines.append(f"- [{category}](#{anchor}) ({count} scripts)")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed sections
    for category in sorted(scripts_by_category.keys()):
        lines.append(f"## {category}")
        lines.append("")
        scripts = scripts_by_category[category]
        lines.append(f"**{len(scripts)} scripts**")
        lines.append("")

        for script_path, description in scripts:
            relative_path = script_path.relative_to(workspace_root)
            lines.append(f"### `{relative_path}`")
            lines.append("")
            lines.append(f"{description}")
            lines.append("")

            # Add file info
            try:
                stat = script_path.stat()
                size_kb = stat.st_size / 1024
                lines.append(f"- **Size:** {size_kb:.1f} KB")
                lines.append(f"- **Modified:** {stat.st_mtime}")
            except OSError:
                pass
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*This index is automatically generated. To update, run `python generate_script_index.py`.*"
    )

    return "\n".join(lines)


def main():
    """Entry point for generating the script index from the workspace."""
    workspace_root = pathlib.Path("/Volumes/APFS Space/n00tropic")
    output_file = pathlib.Path(__file__).parent / "script_index.md"

    print(f"Scanning workspace: {workspace_root}")
    scripts_by_category = categorize_scripts(workspace_root)
    total_found = sum(len(s) for s in scripts_by_category.values())
    category_count = len(scripts_by_category)
    print(
        f"Found {total_found} scripts in {category_count} categories",
    )

    print(f"Generating index at: {output_file}")
    markdown_content = generate_markdown_index(scripts_by_category, workspace_root)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print("Script index generated successfully!")


if __name__ == "__main__":
    main()
