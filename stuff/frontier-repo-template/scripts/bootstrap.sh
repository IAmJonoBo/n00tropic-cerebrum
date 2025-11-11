#!/usr/bin/env bash
set -euo pipefail
echo "Bootstrapping repo: installing hooks"
pre-commit install || true
