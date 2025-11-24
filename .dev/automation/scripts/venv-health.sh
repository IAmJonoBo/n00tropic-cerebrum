#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

echo "[venv-health] scanning virtual environments"
mapfile -t VENVS < <(find "$ROOT" -maxdepth 3 -type d -name '.venv*' | sort)
if [[ ${#VENVS[@]} -eq 0 ]]; then
  echo "[venv-health] no virtualenvs found"
  exit 0
fi

echo "[venv-health] found ${#VENVS[@]} envs"
for v in "${VENVS[@]}"; do
  env_name="$(basename "$v")"
  py="$v/bin/python3"
  info="(no python)"
  if [[ -x "$py" ]]; then
    ver=$($py -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || echo "?")
    info="python ${ver}"
  fi
  size=$(du -sh "$v" 2>/dev/null | awk '{print $1}')
  echo " - ${env_name}: ${info}, size ${size}, path ${v}"
  # Staleness: last modified time of bin/python3 if present
  if [[ -x "$py" ]]; then
    ts=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M" "$py" 2>/dev/null || true)
    echo "   last python touch: ${ts:-unknown}"
  fi
  # if requirements / lock nearby
  req=$(find "$(dirname "$v")" -maxdepth 1 -name 'requirements*.txt' | head -1 || true)
  if [[ -n "$req" ]]; then
    echo "   hint: sync with $(basename "$req")"
  fi
  pkg_json="$(dirname "$v")/package.json"
  if [[ -f "$pkg_json" ]]; then
    echo "   hint: pnpm install --filter $(basename "$(dirname "$v")")..."
  fi
  echo
done

# Write summary artefact
mkdir -p "$ROOT/artifacts"
ART="$ROOT/artifacts/venv-health.json"
python3 - "$ROOT" "$ART" <<'PY'
import json, sys, pathlib, subprocess
root = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2])
venvs = []
for path in sorted(root.glob("**/.venv*")):
    py = path / "bin/python3"
    version = None
    if py.exists():
        try:
            version = subprocess.check_output([py, "-c", "import sys;print(sys.version.split()[0])"]).decode().strip()
        except Exception:
            version = None
    venvs.append({"name": path.name, "path": str(path), "python": version})
out.write_text(json.dumps(venvs, indent=2))
print(f"[venv-health] wrote {out}")
PY
