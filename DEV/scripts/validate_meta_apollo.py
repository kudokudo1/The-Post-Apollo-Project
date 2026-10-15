#!/usr/bin/env python3
from pathlib import Path
import re

def navigation_link_errors(root: Path) -> list[str]:
    """Validate local README/room-map Markdown links, not document semantics."""
    from urllib.parse import unquote

    root = root.resolve()
    pages = ("README.md",) + tuple(f"{room}/README.md" for room in ROOMS)
    pattern = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
    issues: list[str] = []
    for page in pages:
        document = root / page
        if not document.is_file():
            continue  # Room/README presence is checked by repository grammar.
        fenced = False
        for number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith((chr(96) * 3, "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for match in pattern.finditer(line):
                href = match.group(1).strip()
                if (not href or href.startswith(("#", "//"))
                        or re.match(r"(?i)^[a-z][a-z0-9+.-]*:", href)):
                    continue  # External addresses and in-page anchors.
                raw_target = unquote(href.split("#", 1)[0].split("?", 1)[0])
                if not raw_target:
                    continue
                target = ((root / raw_target.lstrip("/")) if raw_target.startswith("/")
                          else (document.parent / raw_target)).resolve()
                try:
                    target.relative_to(root)
                except ValueError:
                    issues.append(f"{page}:{number} link escapes repository: {href}")
                    continue
                if not target.exists():
                    issues.append(f"{page}:{number} broken local link: {href}")
    return issues


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
errors.extend(navigation_link_errors(ROOT))
if errors:
    print("META APOLLO REPOSITORY GRAMMAR // v1 // FAIL")
    [print(" - " + e) for e in errors]
    raise SystemExit(1)
print("META APOLLO REPOSITORY GRAMMAR // v1 // PASS")
