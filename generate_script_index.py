#!/usr/bin/env python3
"""Generate Markdown + Antora script indices for the n00tropic polyrepo."""

from __future__ import annotations

import argparse
import datetime
import os
import pathlib
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

SCRIPT_EXTENSIONS = {
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
    ".py",
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".rb",
    ".pl",
    ".pm",
    ".php",
    ".go",
    ".rs",
    ".java",
    ".scala",
    ".kt",
    ".cs",
    ".cpp",
    ".cc",
    ".cxx",
    ".c++",
    ".c",
    ".swift",
    ".dart",
    ".lua",
    ".r",
    ".sql",
    ".ps1",
    ".bat",
    ".cmd",
}

NORMALIZED_SCRIPT_EXTENSIONS = {ext.lower() for ext in SCRIPT_EXTENSIONS}

IGNORE_DIRS = {
    ".bench-cli",
    ".cypress",
    ".git",
    ".idea",
    ".mypy_cache",
    ".next",
    ".nuxt",
    ".pytest_cache",
    ".tox",
    ".vscode",
    "Thumbs.db",
    "__pycache__",
    "artifacts",
    "assets",
    "bin",
    "build",
    "dist",
    "docs",
    "env",
    "images",
    "lib",
    "node_modules",
    "obj",
    "public",
    "static",
    "target",
    "vendor",
}

BINARY_EXTENSIONS = {".pyc"}

REPO_ROOT = pathlib.Path(__file__).parent.resolve()
DEFAULT_WORKSPACE_ROOT = pathlib.Path("/Volumes/APFS Space/n00tropic")
DEFAULT_MARKDOWN_OUTPUT = REPO_ROOT / "script_index.md"
DEFAULT_ADOC_OUTPUT = REPO_ROOT / "docs/modules/ROOT/pages/script-index.adoc"


@dataclass
class ScriptRecord:
    """Metadata describing a discovered script."""

    repo: str
    category: str
    relative_path: pathlib.Path
    absolute_path: pathlib.Path
    description: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan the workspace for scripts and emit Markdown/AsciiDoc indices.",
    )
    parser.add_argument(
        "--workspace-root",
        default=str(DEFAULT_WORKSPACE_ROOT),
        help="Absolute path to the /Volumes/APFS Space/n00tropic workspace root.",
    )
    parser.add_argument(
        "--markdown-output",
        default=str(DEFAULT_MARKDOWN_OUTPUT),
        help="Path for the generated Markdown index (defaults to script_index.md).",
    )
    parser.add_argument(
        "--adoc-output",
        default=str(DEFAULT_ADOC_OUTPUT),
        help="Path for the generated Antora page (defaults to docs/modules/ROOT/pages/script-index.adoc).",
    )
    return parser.parse_args()


def extract_first_sentence(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return "No description available"
    match = re.search(r"(.+?[.!?])(\s|$)", normalized)
    if match:
        return match.group(1).strip()
    return normalized


def get_script_description(file_path: pathlib.Path) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            lines: List[str] = []
            for _ in range(40):
                line = handle.readline()
                if not line:
                    break
                lines.append(line)
    except OSError:
        return "Unable to read description"

    docstring_buffer: List[str] = []
    in_docstring = False
    delimiter = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if not in_docstring and line.startswith("#!"):
            continue
        if line.startswith(("'''", '"""')):
            token = line[:3]
            content = line[3:]
            if not in_docstring:
                in_docstring = True
                delimiter = token
                if content.endswith(token):
                    inner = content[:-3].strip()
                    if inner:
                        docstring_buffer.append(inner)
                    break
                if content.strip():
                    docstring_buffer.append(content.strip())
                continue
            if content.endswith(token):
                inner = content[:-3].strip()
                if inner:
                    docstring_buffer.append(inner)
                break
            continue
        if in_docstring:
            if delimiter and line.endswith(delimiter):
                inner = line[:-3].strip()
                if inner:
                    docstring_buffer.append(inner)
                break
            docstring_buffer.append(line)
            continue
        if line.startswith("#"):
            candidate = line.lstrip("#").strip()
            if candidate:
                return extract_first_sentence(candidate)
        if line.startswith("//"):
            candidate = line.lstrip("/").strip()
            if candidate:
                return extract_first_sentence(candidate)
        break

    if docstring_buffer:
        return extract_first_sentence(" ".join(docstring_buffer))
    return "No description available"


def is_script_file(file_path: pathlib.Path) -> bool:
    if file_path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    if file_path.suffix.lower() in NORMALIZED_SCRIPT_EXTENSIONS:
        return True
    if os.access(file_path, os.X_OK):
        return True
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
            first_line = handle.readline().strip()
            return first_line.startswith("#!")
    except OSError:
        return False


def discover_scripts(workspace_root: pathlib.Path) -> List[ScriptRecord]:
    records: List[ScriptRecord] = []
    ignore_dirs = {entry.lower() for entry in IGNORE_DIRS}

    for root, dirs, files in os.walk(workspace_root):
        dirs[:] = [
            d for d in dirs if d.lower() not in ignore_dirs and not d.endswith(".app")
        ]
        root_path = pathlib.Path(root)
        for file_name in files:
            file_path = root_path / file_name
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() in BINARY_EXTENSIONS:
                continue
            if not is_script_file(file_path):
                continue
            try:
                relative_path = file_path.relative_to(workspace_root)
            except ValueError:
                continue
            parts = relative_path.parts
            repo = parts[0] if parts else workspace_root.name
            within_repo = (
                pathlib.Path(*parts[1:]) if len(parts) > 1 else pathlib.Path(file_name)
            )
            category_path = within_repo.parent.as_posix()
            category = (
                category_path
                if category_path and category_path != "."
                else "(repo root)"
            )
            description = get_script_description(file_path)
            records.append(
                ScriptRecord(
                    repo=repo,
                    category=category,
                    relative_path=relative_path,
                    absolute_path=file_path,
                    description=description,
                )
            )
    return records


def build_repo_map(
    records: Iterable[ScriptRecord],
) -> Dict[str, Dict[str, List[ScriptRecord]]]:
    repo_map: Dict[str, Dict[str, List[ScriptRecord]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for record in records:
        repo_map[record.repo][record.category].append(record)
    for repo in repo_map:
        for category in repo_map[repo]:
            repo_map[repo][category].sort(
                key=lambda rec: rec.relative_path.as_posix().lower()
            )
    return repo_map


def count_totals(repo_map: Dict[str, Dict[str, List[ScriptRecord]]]) -> Dict[str, int]:
    repos = len(repo_map)
    categories = sum(len(categories) for categories in repo_map.values())
    scripts = sum(
        len(items) for categories in repo_map.values() for items in categories.values()
    )
    return {"repos": repos, "categories": categories, "scripts": scripts}


def generate_markdown_index(
    repo_map: Dict[str, Dict[str, List[ScriptRecord]]], workspace_root: pathlib.Path
) -> str:
    totals = count_totals(repo_map)
    lines: List[str] = []
    lines.append("<!-- markdownlint-disable -->")
    lines.append("<!-- vale off -->")
    lines.append("")
    lines.append("# n00tropic Polyrepo Script Index")
    lines.append("")
    lines.append(
        "This index automatically catalogues scripts across the workspace for agents and maintainers."
    )
    lines.append(f"**Workspace Root:** `{workspace_root}`")
    lines.append(f"**Repositories Scanned:** {totals['repos']}")
    lines.append(f"**Categories:** {totals['categories']}")
    lines.append(f"**Total Scripts:** {totals['scripts']}")
    lines.append("")

    for repo in sorted(repo_map):
        repo_categories = repo_map[repo]
        repo_total = sum(len(items) for items in repo_categories.values())
        lines.append(f"## {repo}")
        lines.append("")
        lines.append(
            f"**{repo_total} scripts across {len(repo_categories)} categories.**"
        )
        lines.append("")
        for category in sorted(repo_categories):
            category_records = repo_categories[category]
            lines.append(f"### {repo} / {category} ({len(category_records)} scripts)")
            lines.append("")
            for record in category_records:
                lines.append(f"#### `{record.relative_path}`")
                lines.append("")
                lines.append(record.description)
                try:
                    stat = record.absolute_path.stat()
                    size_kb = stat.st_size / 1024
                    modified = datetime.datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat()
                    lines.append(f"- **Size:** {size_kb:.1f} KB")
                    lines.append(f"- **Modified:** {modified}")
                except OSError:
                    lines.append("- **Size:** unavailable")
                lines.append("- **Repository:** `{}`".format(record.repo))
                lines.append(f"- **Category:** `{record.category}`")
                lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(
        '*This index is automatically generated. To update, run `python generate_script_index.py --workspace-root "/Volumes/APFS Space/n00tropic"`.*'
    )
    lines.append("")
    lines.append("<!-- vale on -->")
    lines.append("<!-- markdownlint-enable -->")
    lines.append("")
    return "\n".join(lines)


def generate_adoc_summary(repo_map: Dict[str, Dict[str, List[ScriptRecord]]]) -> str:
    totals = count_totals(repo_map)
    reviewed = datetime.date.today().isoformat()
    lines: List[str] = []
    lines.append("= Script index")
    lines.append(
        ":page-tags: diataxis:reference, domain:platform, audience:operator, stability:beta"
    )
    lines.append(f":reviewed: {reviewed}")
    lines.append("// vale Vale.Terms = NO")
    lines.append("")
    lines.append(
        f"This page summarises {totals['scripts']} scripts across {totals['repos']} repositories and {totals['categories']} categories."
    )
    lines.append(
        "For the exhaustive Markdown export, open `script_index.md` at the workspace root."
    )
    lines.append("")
    lines.append("== Repository summary")
    lines.append("")

    for repo in sorted(repo_map):
        repo_categories = repo_map[repo]
        repo_total = sum(len(items) for items in repo_categories.values())
        lines.append(f"*Repository:* `{repo}` ({repo_total} scripts)")
        lines.append("")
        for category in sorted(repo_categories):
            count = len(repo_categories[category])
            lines.append(f"* `{category}`: {count} scripts")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    workspace_root = pathlib.Path(args.workspace_root).expanduser().resolve()
    markdown_output = pathlib.Path(args.markdown_output).resolve()
    adoc_output = pathlib.Path(args.adoc_output).resolve()

    print(f"Scanning workspace: {workspace_root}")
    records = discover_scripts(workspace_root)
    repo_map = build_repo_map(records)
    totals = count_totals(repo_map)
    print(
        f"Found {totals['scripts']} scripts across {totals['categories']} categories in {totals['repos']} repositories",
    )

    print(f"Writing Markdown index to: {markdown_output}")
    markdown_output.write_text(
        generate_markdown_index(repo_map, workspace_root), encoding="utf-8"
    )

    print(f"Writing Antora summary to: {adoc_output}")
    adoc_output.write_text(generate_adoc_summary(repo_map), encoding="utf-8")

    print("Script indices generated successfully!")


if __name__ == "__main__":
    main()
