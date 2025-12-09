#!/usr/bin/env python3
# pylint: disable=missing-function-docstring,invalid-name,line-too-long
"""
md-reflow: Recursively reflow long lines in Markdown files intelligently.

Goals
- Rewrap prose to a target width while preserving Markdown semantics.
- Respect code fences/indented code, tables, HTML/MDX blocks, YAML/TOML/JSON front matter,
  link reference definitions, headings, and hard line breaks.
- Handle lists (including checkboxes) with correct hanging indents.
- Handle blockquotes (supports nested > prefixes).
- Avoid breaking inside inline code spans and link/image constructs.
- Work recursively over directories. Sensible defaults; configurable via CLI.

No third-party dependencies. Python 3.9+.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import os
import re
import sys
from pathlib import Path
from typing import Iterator, List, Optional, Sequence, Tuple

# ---------- Utilities ----------

FRONT_MATTER_DELIMS = (
    "---",  # YAML / many tools
    "+++",  # TOML (Hugo)
    "{",  # JSON; we detect only if first non-ws char is '{' and ends with '}' alone on a line
)

DEFAULT_EXTS = (".md", ".markdown", ".adoc")
MDX_EXTS = (".mdx",)

# A conservative set of HTML block starters; we skip reflow until a blank line or closing tag.
HTML_BLOCK_START_RE = re.compile(
    r"""^\s*<(?:
        (?:script|style|pre|table|thead|tbody|tfoot|tr|td|th|div|section|article|aside|
           details|summary|figure|figcaption|iframe|video|ul|ol|li|blockquote|dl|dt|dd|
           header|footer|nav|main|canvas|svg|math|form)\b
        |!--
    )""",
    re.IGNORECASE | re.VERBOSE,
)
HTML_BLOCK_END_RE = re.compile(r".*?(-->)\s*$", re.IGNORECASE)

ATX_HEADING_RE = re.compile(r"^\s{0,3}(?:#{1,6}|={1,6})(?:\s|$)")
SETEXT_UNDERLINE_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")

FENCE_OPEN_RE = re.compile(r"^(\s*)(`{3,}|~{3,}|-{4,}|\.{4,}|\+{4,})(.*)$")


# closing fence must match fence char and length, ignoring trailing spaces.
def fence_close_re(ch: str, n: int) -> re.Pattern:
    return re.compile(rf"^\s*{re.escape(ch*n)}\s*$")


# List item marker (supports nested, checkboxes).
LIST_MARKER_RE = re.compile(
    r"""
    ^(?P<indent>\s*)
    (?P<marker>[*+-]|\d{1,9}[.)])
    (?P<space>\s+)
    (?P<checkbox>\[(?:\s|x|X)\]\s+)?  # optional task list box
    """,
    re.VERBOSE,
)

# Link and image constructs to keep unbroken during wrapping
LINK_INLINE_RE = re.compile(r"!?\[[^\]]*\]\([^\s)]+(?:\s+\"[^\"]*\")?\)")
LINK_REF_RE = re.compile(r"!?\[[^\]]*\]\[[^\]]*\]")
AUTOLINK_RE = re.compile(r"<[a-zA-Z][a-zA-Z0-9+.\-]*:[^ >]*>")  # <scheme:...>
# Bare URLs don't contain spaces: no extra handling needed.

# Link definition lines: `[id]: url "title"`
LINK_DEF_RE = re.compile(r"^\s*\[[^\]]+\]:\s+\S+")

# Table header separator row (GFM style)
TABLE_SEP_RE = re.compile(
    r"""^\s*\|?      # optional leading pipe
        (?:\s*:?-{3,}:?\s*\|)+
        \s*:?-{3,}:?\s*\|?\s*$""",
    re.VERBOSE,
)


# Hard line breaks: two trailing spaces or a trailing backslash (CommonMark)
def is_hard_break(line: str) -> bool:
    return (
        len(line.rstrip("\n")) >= 2 and line.rstrip("\n").endswith("  ")
    ) or line.rstrip("\n").endswith("\\")


def detect_newline_style(text: str) -> str:
    # Return '\r\n' if Windows-style appears, else '\n'
    return (
        "\r\n"
        if "\r\n" in text
        and text.count("\r\n") >= text.count("\n") - text.count("\r\n")
        else "\n"
    )


def expand_tabs(line: str) -> str:
    return line.expandtabs(4)


# ---------- Wrapping engine ----------

NBSP = "\u00a0"


def protect_spans(s: str) -> Tuple[str, List[Tuple[int, int]]]:
    """
    Replace spaces _inside_ protected spans (inline code, links/images, autolinks)
    with NBSP so text wrapping does not split them. Returns the modified string and
    a list of (start, end) indices of protected segments (for debugging/future use).
    """
    spans: List[Tuple[int, int]] = []

    def mark_span(start: int, end: int):
        spans.append((start, end))

    # 1) Inline code handling with variable backtick counts
    parts: List[Tuple[int, int]] = []
    i = 0
    while i < len(s):
        if s[i] == "`":
            j = i
            while j < len(s) and s[j] == "`":
                j += 1
            n = j - i  # number of backticks
            # find matching closing run of same length
            k = s.find("`" * n, j)
            if k == -1:
                i += 1
                continue
            parts.append((i, k + n))
            i = k + n
        else:
            i += 1
    for a, b in parts:
        mark_span(a, b)

    # 2) Links/images (inline + reference)
    for m in LINK_INLINE_RE.finditer(s):
        mark_span(m.start(), m.end())
    for m in LINK_REF_RE.finditer(s):
        mark_span(m.start(), m.end())
    # 3) Autolinks
    for m in AUTOLINK_RE.finditer(s):
        mark_span(m.start(), m.end())

    # 4) AsciiDoc link/image/include/xref forms: link:url[text], image::path[], xref:target[]
    ADOC_LINK_RE = re.compile(r"(?:link:|image:|xref:|include:)\S*\[[^\]]*\]")
    for m in ADOC_LINK_RE.finditer(s):
        mark_span(m.start(), m.end())
    # 5) AsciiDoc double angle xref <<target,label>>: protect entire thing
    XREF_ANGLE_RE = re.compile(r"<<[^>]+>>")
    for m in XREF_ANGLE_RE.finditer(s):
        mark_span(m.start(), m.end())
    # 6) AsciiDoc attribute references like {var} should not be broken
    ATTR_REF_RE = re.compile(r"\{[^}]+\}")
    for m in ATTR_REF_RE.finditer(s):
        mark_span(m.start(), m.end())

    if not spans:
        return s, []

    # merge overlapping spans
    spans.sort()
    merged = [spans[0]]
    for a, b in spans[1:]:
        la, lb = merged[-1]
        if a <= lb:
            merged[-1] = (la, max(lb, b))
        else:
            merged.append((a, b))
    spans = merged

    # replace internal spaces in spans with NBSP
    out = []
    last = 0
    for a, b in spans:
        out.append(s[last:a])
        protected = s[a:b].replace(" ", NBSP)
        out.append(protected)
        last = b
    out.append(s[last:])
    return "".join(out), spans


def wrap_text_prose(
    text: str,
    width: int,
    initial_indent: str = "",
    subsequent_indent: str = "",
) -> str:
    """
    Wrap a single paragraph of text (no blank lines inside).
    Respects hard breaks by splitting the paragraph on them first.
    """
    lines = text.splitlines()
    segments: List[str] = []
    current: List[str] = []

    def flush_segment():
        if not current:
            return
        para = " ".join([x.strip() for x in current if x.strip() != ""])
        if not para:
            current.clear()
            return
        protected, _ = protect_spans(para)
        wrapped = _fill(protected, width, initial_indent, subsequent_indent)
        wrapped = wrapped.replace(NBSP, " ")
        segments.append(wrapped)
        current.clear()

    for line in lines:
        if is_hard_break(line):
            # treat as end of segment; preserve explicit line break
            current.append(line.rstrip("\n"))
            flush_segment()
        elif line.strip() == "":
            flush_segment()
            segments.append(
                ""
            )  # blank line inside paragraph block becomes a blank line
        else:
            current.append(line.rstrip("\n"))
    flush_segment()

    return ("\n".join(segments)).rstrip()


def _fill(text: str, width: int, initial_indent: str, subsequent_indent: str) -> str:
    # Minimal custom fill to avoid stdlib textwrap quirkiness
    words = re.findall(r"\S+|\s+", text)
    out_lines: List[str] = []
    line = initial_indent
    line_len = len(line.expandtabs(4))
    idx = 0

    def append_word(w: str, is_space: bool):
        nonlocal line, line_len
        if is_space:
            # collapse multiple spaces to one normal space unless NBSP used
            if NBSP in w:
                # keep NBSPs as-is (won't split), normal spaces collapse to one
                w2 = re.sub(r" +", " ", w.replace(NBSP, NBSP))
            else:
                w2 = " "
        else:
            w2 = w
        line += w2
        line_len = len(line.expandtabs(4))

    while idx < len(words):
        token = words[idx]
        is_space = token.isspace()
        if is_space and not out_lines and line.strip() == "":
            idx += 1  # skip leading space
            continue

        if not is_space:
            # If adding token would exceed width, wrap (unless line is empty)
            projected = (
                len((line + ("" if line.endswith(" ") else " ") + token).expandtabs(4))
                if line.strip()
                else len((line + token).expandtabs(4))
            )
            if line.strip() and projected > width:
                out_lines.append(line.rstrip())
                line = subsequent_indent + token
                line_len = len(line.expandtabs(4))
                idx += 1
                continue

        # normal append
        if not line.strip():
            line = (initial_indent if not out_lines else subsequent_indent) + (
                "" if is_space else token
            )
            line_len = len(line.expandtabs(4))
        else:
            if not is_space and not (line.endswith(" ") or line.endswith(NBSP)):
                line += " "
            append_word(token, is_space=False if not is_space else True)
        idx += 1

    if line:
        out_lines.append(line.rstrip())

    return "\n".join(out_lines)


# ---------- Block parsing and formatting ----------


@dataclasses.dataclass
class FormatOptions:
    """Tweakable settings controlling markdown reflow behavior."""

    width: int = 100
    prose_wrap: str = "always"  # "always" | "preserve"
    include_mdx: bool = False


def format_markdown(text: str, opts: FormatOptions) -> str:
    nl = detect_newline_style(text)
    lines = text.splitlines()
    i = 0
    out: List[str] = []

    # Front matter at file start
    i = _consume_front_matter(lines, out)

    while i < len(lines):
        line = lines[i]

        # Blank lines pass through
        if line.strip() == "":
            out.append("")
            i += 1
            continue

        # AsciiDoc attribute assignment (':name: value'), include directives, conditionals: pass through
        ls = line.lstrip()
        if (
            ls.startswith(":")
            or ls.startswith("include::")
            or ls.startswith("ifdef::")
            or ls.startswith("ifndef::")
        ):
            out.append(line.rstrip())
            i += 1
            continue

        # Headings (ATX)
        if ATX_HEADING_RE.match(line):
            out.append(line.rstrip())
            i += 1
            # setext heading underlines handled below
            continue

        # Setext headings: line followed by === or ---
        if i + 1 < len(lines) and SETEXT_UNDERLINE_RE.match(lines[i + 1]):
            out.append(line.rstrip())
            out.append(lines[i + 1].rstrip())
            i += 2
            continue

        # Link definition line
        if LINK_DEF_RE.match(line):
            out.append(line.rstrip())
            i += 1
            continue

        # Fenced code block
        m = FENCE_OPEN_RE.match(line)
        if m:
            _, fence, _rest = m.groups()
            end_re = fence_close_re(fence[0], len(fence))
            out.append(line.rstrip())
            i += 1
            while i < len(lines):
                out.append(lines[i].rstrip())
                if end_re.match(lines[i]):
                    i += 1
                    break
                i += 1
            continue

        # HTML/MDX-ish block
        if HTML_BLOCK_START_RE.match(line):
            i = _consume_html_block(lines, i, out)
            continue

        # Table block
        if _looks_like_table_header(lines, i):
            i = _consume_table_block(lines, i, out)
            continue

        # Blockquote
        if line.lstrip().startswith(">"):
            i = _consume_blockquote(lines, i, out, opts)
            continue

        # List block
        lm = LIST_MARKER_RE.match(line)
        if lm:
            i = _consume_list_block(lines, i, out, opts)
            continue

        # Paragraph / plain text block
        i = _consume_paragraph(lines, i, out, opts)

    return nl.join(out).rstrip() + nl


def _consume_front_matter(lines: List[str], out: List[str]) -> int:
    i = 0
    if not lines:
        return 0
    first = lines[0].lstrip()
    if first.startswith("---"):
        # YAML: read until next --- or ...
        out.append(lines[0].rstrip())
        i = 1
        while i < len(lines):
            out.append(lines[i].rstrip())
            if lines[i].strip() in ("---", "..."):
                i += 1
                break
            i += 1
        return i
    if first.startswith("+++"):
        out.append(lines[0].rstrip())
        i = 1
        while i < len(lines):
            out.append(lines[i].rstrip())
            if lines[i].strip().startswith("+++"):
                i += 1
                break
            i += 1
        return i
    if first.startswith("{"):
        # JSON front matter: consume until a line with only '}' (best effort)
        out.append(lines[0].rstrip())
        i = 1
        while i < len(lines):
            out.append(lines[i].rstrip())
            if lines[i].strip() == "}":
                i += 1
                break
            i += 1
        return i
    return 0


def _consume_html_block(lines: List[str], i: int, out: List[str]) -> int:
    # consume until a blank line or HTML comment close if started with <!--
    start = lines[i]
    out.append(start.rstrip())
    i += 1
    in_comment = start.strip().startswith("<!--")
    while i < len(lines):
        out.append(lines[i].rstrip())
        if lines[i].strip() == "":
            i += 1
            break
        if in_comment and HTML_BLOCK_END_RE.match(lines[i]):
            i += 1
            break
        if not in_comment and lines[i].strip().startswith("</"):
            i += 1
            break
        i += 1
    return i


def _looks_like_table_header(lines: List[str], i: int) -> bool:
    if i + 1 >= len(lines):
        return False
    # header line must contain a pipe; next line must be a separator row
    return ("|" in lines[i]) and TABLE_SEP_RE.match(lines[i + 1] or "") is not None


def _consume_table_block(lines: List[str], i: int, out: List[str]) -> int:
    # Pass table through unchanged (alignment is renderer-dependent).
    out.append(lines[i].rstrip())
    i += 1
    out.append(lines[i].rstrip())  # separator line
    i += 1
    while i < len(lines):
        if lines[i].strip() == "":
            break
        if "|" not in lines[i]:
            break
        out.append(lines[i].rstrip())
        i += 1
    return i


def _consume_blockquote(
    lines: List[str], i: int, out: List[str], opts: FormatOptions
) -> int:
    buf: List[str] = []
    prefixes: List[str] = []

    j = i
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            buf.append("")
            prefixes.append("")
            j += 1
            continue
        if not line.lstrip().startswith(">"):
            break
        # Extract minimal '>' prefix (supports nested)
        m = re.match(r"^(\s*>+\s?)", line)
        if m:
            pfx = m.group(1)
            content = line[len(pfx) :]
            prefixes.append(pfx)
            buf.append(content.rstrip())
            j += 1
        else:
            break

    # Reflow the content lines as a sub-document (recursively)
    inner = format_markdown("\n".join(buf) + "\n", opts).rstrip("\n").splitlines()
    # Reapply '>' prefix: if a stored prefix is empty (blank line), keep it blank
    for k, line in enumerate(inner):
        if buf[k].strip() == "" or line.strip() == "":
            out.append("")  # blank line inside the quote
        else:
            # normalise to single '>' level using the minimal prefix seen at that line
            # Keep original depth based on original prefixes[k] (best effort).
            p = prefixes[k] or "> "
            # ensure a single space after the last '>'
            if not p.rstrip().endswith(">"):
                p = "> "
            else:
                p = re.sub(r">\s*$", "> ", p)
            out.append(f"{p}{line.rstrip()}")
    return j


def _consume_list_block(
    lines: List[str], i: int, out: List[str], opts: FormatOptions
) -> int:
    # Consume contiguous list (same or deeper indent)
    start_indent_match = re.match(r"^(\s*)", lines[i])
    start_indent = len(start_indent_match.group(1)) if start_indent_match else 0
    j = i
    block: List[str] = []
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            block.append("")
            j += 1
            continue
        indent_match = re.match(r"^(\s*)", line)
        ind = len(indent_match.group(1)) if indent_match else 0
        marker_match = LIST_MARKER_RE.match(line)
        if ind < start_indent:
            break
        if ind == start_indent and not marker_match:
            break
        block.append(line.rstrip())
        # If a fenced code begins, include it verbatim until it ends
        fm = FENCE_OPEN_RE.match(line)
        if fm:
            _, f, _ = fm.groups()
            end_re = fence_close_re(f[0], len(f))
            j += 1
            while j < len(lines):
                block.append(lines[j].rstrip())
                if end_re.match(lines[j]):
                    j += 1
                    break
                j += 1
            continue
        j += 1

    # Process block per list item
    k = 0
    while k < len(block):
        line = block[k]
        if line.strip() == "":
            out.append("")
            k += 1
            continue
        m = LIST_MARKER_RE.match(line)
        if not m:
            # Not a marker at this line (continuation of previous item or stray text).
            out.append(line)
            k += 1
            continue
        indent = m.group("indent")
        marker = m.group("marker")
        space = m.group("space")
        checkbox = m.group("checkbox") or ""
        head_prefix = f"{indent}{marker}{space}{checkbox}"
        content_indent = " " * len(head_prefix)

        # Gather this item's lines until next sibling item (same indent) or block end
        item_lines: List[str] = [line[len(head_prefix) :]]
        k += 1
        while k < len(block):
            next_line = block[k]
            if next_line.strip() == "":
                item_lines.append("")
                k += 1
                continue
            nm = LIST_MARKER_RE.match(next_line)
            if nm and len(nm.group("indent")) == len(indent):
                break  # next sibling
            # Continuation line (hanging indent or nested content)
            if nm and len(nm.group("indent")) > len(indent):
                # nested list begins; include line and let recursive formatter handle inside
                item_lines.append(next_line)
            else:
                # normal continuation (strip only the item's content indent if present)
                if next_line.startswith(content_indent):
                    item_lines.append(next_line[len(content_indent) :])
                else:
                    item_lines.append(next_line)
            k += 1

        # Format the item's content as a sub-document, then re-indent
        subdoc = "\n".join(item_lines) + "\n"
        formatted = format_markdown(subdoc, opts).rstrip("\n").splitlines()

        # Re-apply hanging indent: first line gets head_prefix, others get content_indent
        if not formatted:
            out.append(head_prefix.rstrip())
        else:
            first_done = False
            for fl in formatted:
                if fl.strip() == "":
                    out.append("")
                    continue
                if not first_done:
                    out.append(f"{head_prefix}{fl.rstrip()}")
                    first_done = True
                else:
                    out.append(f"{content_indent}{fl.rstrip()}")

    return j


def _consume_paragraph(
    lines: List[str], i: int, out: List[str], opts: FormatOptions
) -> int:
    buf: List[str] = []
    j = i
    while j < len(lines):
        line = lines[j]
        if line.strip() == "":
            break
        if (
            ATX_HEADING_RE.match(line)
            or LINK_DEF_RE.match(line)
            or FENCE_OPEN_RE.match(line)
            or HTML_BLOCK_START_RE.match(line)
            or _looks_like_table_header(lines, j)
            or line.lstrip().startswith(">")
            or LIST_MARKER_RE.match(line)
            or (j + 1 < len(lines) and SETEXT_UNDERLINE_RE.match(lines[j + 1]))
        ):
            break
        buf.append(line.rstrip())
        j += 1

    para = "\n".join(buf)
    if opts.prose_wrap == "preserve":
        out.extend(buf)
    else:
        wrapped = wrap_text_prose(para, opts.width)
        out.extend(wrapped.splitlines())
    return j


# ---------- CLI / filesystem ----------


def iter_markdown_files(
    paths: Sequence[Path],
    include_mdx: bool,
    exts: Sequence[str],
    include_hidden: bool,
    exclude_dirs: Sequence[str],
) -> Iterator[Path]:
    allowed_exts = set(e.lower() for e in exts)
    if include_mdx:
        allowed_exts |= set(MDX_EXTS)
    for p in paths:
        if p.is_file():
            if p.suffix.lower() in allowed_exts:
                yield p
        elif p.is_dir():
            for root, dirs, files in os.walk(p):
                # prune excluded dirs
                dirs[:] = [
                    d
                    for d in dirs
                    if (include_hidden or not d.startswith("."))
                    and d not in exclude_dirs
                ]
                for name in files:
                    if not include_hidden and name.startswith("."):
                        continue
                    fp = Path(root) / name
                    if fp.suffix.lower() in allowed_exts:
                        yield fp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="md-reflow",
        description="Recursively reflow long lines in Markdown and AsciiDoc files while preserving semantics.",
    )
    ap.add_argument("paths", nargs="+", help="Files or directories to process.")
    ap.add_argument(
        "-w",
        "--width",
        type=int,
        default=100,
        help="Target wrap width for prose (default: 100).",
    )
    ap.add_argument(
        "--prose-wrap",
        choices=["always", "preserve"],
        default="always",
        help="When 'preserve', do not reflow paragraphs; only fix structural joining (default: always).",
    )
    ap.add_argument(
        "--exts",
        default=",".join(DEFAULT_EXTS),
        help="Comma-separated list of file extensions to include (default: .md,.markdown,.adoc).",
    )
    ap.add_argument(
        "--include-mdx", action="store_true", help="Also process .mdx files (opt-in)."
    )
    ap.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and folders.",
    )
    ap.add_argument(
        "--exclude-dirs",
        default=".git,node_modules,.venv,.tox,.idea,.vscode",
        help="Comma-separated directory names to skip.",
    )
    ap.add_argument(
        "-i", "--in-place", action="store_true", help="Write changes back to files."
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit with non-zero status if any files would change.",
    )
    ap.add_argument(
        "--diff", action="store_true", help="Show unified diffs for changed files."
    )
    ap.add_argument(
        "--stdout",
        action="store_true",
        help="Write the reformatted content to STDOUT (single file only).",
    )

    args = ap.parse_args(argv)

    paths = [Path(p) for p in args.paths]
    exts = tuple(
        e if e.startswith(".") else f".{e}" for e in args.exts.split(",") if e.strip()
    )
    exclude_dirs = tuple(d.strip() for d in args.exclude_dirs.split(",") if d.strip())

    files = list(
        iter_markdown_files(
            paths, args.include_mdx, exts, args.include_hidden, exclude_dirs
        )
    )
    if not files:
        print("No matching files.", file=sys.stderr)
        return 2

    if args.stdout and (len(files) != 1 or not files[0].is_file()):
        print("--stdout requires exactly one input file.", file=sys.stderr)
        return 2

    opts = FormatOptions(
        width=args.width, prose_wrap=args.prose_wrap, include_mdx=args.include_mdx
    )
    changed_any = False

    for fp in files:
        raw = fp.read_text(encoding="utf-8", errors="surrogatepass")
        result = format_markdown(raw, opts)
        if result != raw:
            changed_any = True
            if args.stdout:
                sys.stdout.write(result)
                continue
            if args.diff or args.check:
                diff = difflib.unified_diff(
                    raw.splitlines(keepends=True),
                    result.splitlines(keepends=True),
                    fromfile=str(fp),
                    tofile=str(fp),
                )
                sys.stdout.writelines(diff)
            if args.in_place and not args.check:
                fp.write_text(result, encoding="utf-8")
        else:
            # No change; optionally print nothing to keep quiet.
            pass

    if args.check and changed_any:
        return 1
    return 0


# ---------- Helpers not yet used but reserved for future robustness ----------


def _consume_table_like_until_blank(lines: List[str], i: int, out: List[str]) -> int:
    # Fallback (unused): keep lines with pipes until blank; conservative.
    while i < len(lines) and ("|" in lines[i]) and lines[i].strip() != "":
        out.append(lines[i].rstrip())
        i += 1
    return i


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        # Allow piping to tools like `head` without ugly tracebacks.
        try:
            sys.stderr.close()
        finally:
            pass
