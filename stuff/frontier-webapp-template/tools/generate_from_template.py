#!/usr/bin/env python3
import argparse
import json
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="templates/template.json")
    ap.add_argument("--dest", required=True)
    args = ap.parse_args()
    spec = json.loads(pathlib.Path(args.source).read_text(encoding="utf-8"))
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
