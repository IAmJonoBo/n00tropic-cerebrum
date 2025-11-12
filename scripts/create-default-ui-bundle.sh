#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR="$ROOT_DIR/vendor/antora"
TMP_DIR="$ROOT_DIR/.tmp-ui-bundle"

mkdir -p "$OUT_DIR"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/layouts/partials"
mkdir -p "$TMP_DIR/styles"
mkdir -p "$TMP_DIR/assets"

# Write a minimal bundle.json Antora expects
cat >"$TMP_DIR/bundle.json" <<EOF
{
  "name": "n00-fallback-ui",
  "version": "0.0.0",
  "title": "Fallback UI",
  "asciidoc": {
    "attributes": {}
  }
}
EOF

# Minimal layout; Antora uses Handlebars so provide a simple layout
cat >"$TMP_DIR/layouts/layout.hbs" <<'EOF'
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>{{title}}</title>
    <link rel="stylesheet" href="/styles/site.css" />
  </head>
  <body>
    <div id="content">
    {{{body}}}
    </div>
  </body>
</html>
EOF

# Minimal style
cat >"$TMP_DIR/styles/site.css" <<'EOF'
body {
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
  line-height: 1.4;
  margin: 0;
}
#content { padding: 1rem; }
EOF

# Create a small placeholder image
convert -size 128x128 xc:lightgray "$TMP_DIR/assets/placeholder.png" 2>/dev/null || true

# Zip the bundle
rm -f "$OUT_DIR/ui-bundle.zip"
(cd "$TMP_DIR" && zip -r "$OUT_DIR/ui-bundle.zip" .)

# Cleanup temp dir
rm -rf "$TMP_DIR"

echo "Created default UI bundle at $OUT_DIR/ui-bundle.zip" || true
