#!/usr/bin/env python3
import datetime
import pathlib

root = pathlib.Path(__file__).resolve().parents[1]
out_dir = root / "handover"
out_dir.mkdir(exist_ok=True)
stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
out = out_dir / f"HANDOVER_PACKET-{stamp}.md"

sections = [
    ("Handover Contract", root / "docs/project/HANDOVER_CONTRACT.md"),
    ("Handover Summary (template)", root / "docs/templates/HandoverSummary.md"),
    ("Scope-Change Protocol", root / "docs/project/SCOPE_CHANGE_PROTOCOL.md"),
]

with out.open("w", encoding="utf-8") as f:
    f.write(f"# Handover Packet — generated {stamp} UTC\n\n")
    for title, path in sections:
        f.write(f"\n---\n\n## {title}\n\n")
        if path.exists():
            f.write(path.read_text(encoding="utf-8"))
        else:
            f.write("_Missing: {}_\n".format(path))

print(f"Generated {out}")
