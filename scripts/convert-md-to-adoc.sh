#!/usr/bin/env bash
set -euo pipefail

DOCS_ROOT="${1:-docs}"
MODULE="${2:-ROOT}"
PAGES_DIR="${DOCS_ROOT}/modules/${MODULE}/pages"

if ! command -v kramdoc >/dev/null 2>&1; then
  echo "kramdoc is required. Install via 'gem install kramdown-asciidoc'." >&2
  exit 1
fi

mkdir -p "${PAGES_DIR}"

while IFS= read -r -d '' src; do
  rel="${src#${DOCS_ROOT}/}"
  rel_dir="$(dirname "${rel}")"
  rel_dir="${rel_dir#.}"
  rel_dir="${rel_dir#/}"
  rel_base="$(basename "${rel}" .md)"
  target_dir="${PAGES_DIR}"
  if [ -n "${rel_dir}" ]; then
    target_dir="${target_dir}/${rel_dir}"
  fi
  mkdir -p "${target_dir}"
  target_file="${target_dir}/${rel_base}.adoc"
  echo "Converting ${src} -> ${target_file}"
  kramdoc -o "${target_file}" "${src}"
  rm "${src}"
  if [ -f "${src}.bak" ]; then
    rm "${src}.bak"
  fi
  git add "${target_file}"
done < <(find "${DOCS_ROOT}" -type f -name '*.md' ! -path "${DOCS_ROOT}/modules/*" -print0)
