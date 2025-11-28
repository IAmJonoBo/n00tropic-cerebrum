# uv-first Python bootstrap (workspace-wide)

Use this whenever you need Python deps for any subrepo (n00-frontiers, n00-horizons, n00-school, n00clear-fusion, etc.).

```bash
# from workspace root
scripts/uv-bootstrap.sh n00-frontiers
scripts/uv-bootstrap.sh n00-horizons
scripts/uv-bootstrap.sh n00-school
scripts/uv-bootstrap.sh n00clear-fusion
```

The script:

- sets `UV_CACHE_DIR` to `<repo>/.uv-cache` (override if you prefer);
- creates `<repo>/.venv` if missing with `uv venv`;
- installs `requirements.txt` and `requirements-dev.txt` when present.

To activate after bootstrapping:

```bash
source <repo>/.venv/bin/activate
```

If `uv` is missing, install it from https://github.com/astral-sh/uv (single binary).
