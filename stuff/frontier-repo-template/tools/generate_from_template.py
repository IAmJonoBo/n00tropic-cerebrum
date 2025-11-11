#!/usr/bin/env python3
"""
A tiny generator that can create the directory tree described in templates/template.json or template.yaml.
Usage:
    python tools/generate_from_template.py --source templates/template.json --dest ../my-new-project
"""
import argparse
import json
import pathlib

try:
    import yaml  # optional
except Exception:
    yaml = None


def load_spec(path):
    text = open(path, "r", encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        if not yaml:
            raise SystemExit("PyYAML not installed")
        return yaml.safe_load(text)
    return json.loads(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="templates/template.json")
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    spec = load_spec(args.source)
    dest = pathlib.Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    for item in spec["structure"]:
        p = dest / item["path"]
        if item["type"] == "dir":
            p.mkdir(parents=True, exist_ok=True)
        elif item["type"] == "file":
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text("", encoding="utf-8")
    print(f"Generated skeleton at {dest}")


if __name__ == "__main__":
    main()
