#!/usr/bin/env python3
"""Inventory explicit glow exceptions; no automatic rewrite or false completeness."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
patterns = {
    "explicit enable/disable": re.compile(r"^\s*(?:content|primary|label)GlowEnabled\s*:"),
    "explicit strength or radius": re.compile(r"^\s*(?:content|primary|label)Glow\w*(?:Opacity|Radius|Samples)\s*:"),
    "explicit source": re.compile(r"^\s*(?:contentGlowSource|customPrimaryGlowSource|customLabelGlowSource)\s*:"),
}
for group, pattern in patterns.items():
    matches = []
    for directory in ("widgets", "modules", "components"):
        for path in sorted((root / directory).rglob("*.qml")):
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if pattern.search(line):
                    matches.append(f"{path.relative_to(root)}:{n}: {line.strip()}")
    print(f"\n{group}: {len(matches)} bindings")
    print("\n".join(matches))
print("\nInventory only: custom rectangles and aliases need manual source inspection; explicit bindings may be intentional.")
