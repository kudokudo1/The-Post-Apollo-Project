#!/usr/bin/env python3
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[2]
ROOMS = ("ATLAS","MODEL","BUILD","DEV","OPERATE","EVIDENCE","ARCHIVE")
LINEAGE = "✦︎✦︎✦︎ Meta Apollo Logos //"
errors = []
marker = (ROOT / ".meta-apollo.yml").read_text(encoding="utf-8") if (ROOT / ".meta-apollo.yml").exists() else ""
if not re.search(r"(?m)^design_language:\s*1\s*$", marker): errors.append("missing design_language: 1")
root = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
if not root.startswith(LINEAGE): errors.append("README.md missing lineage")
if "> **STATE //**" not in root: errors.append("README.md missing metadata chassis")
for room in ROOMS:
    p = ROOT / room / "README.md"
    if not p.exists(): errors.append(f"missing {room}/README.md"); continue
    text = p.read_text(encoding="utf-8")
    if not text.startswith(LINEAGE): errors.append(f"{room} missing lineage")
    if f"MAP // {room}" not in text: errors.append(f"{room} missing map identity")
    if "> **STATE //**" not in text: errors.append(f"{room} missing metadata chassis")
    for target in ROOMS:
        if target not in text: errors.append(f"{room} navigation missing {target}")
for rail in ("focus","nav","model","agency","system","scope","warning","neutral"):
    if not (ROOT / "BUILD" / "assets" / "design" / "chassis" / f"{rail}-rail.svg").exists(): errors.append(f"missing {rail} rail")
if errors:
    print("META APOLLO REPOSITORY GRAMMAR // v1 // FAIL")
    [print(" - " + e) for e in errors]
    raise SystemExit(1)
print("META APOLLO REPOSITORY GRAMMAR // v1 // PASS")
