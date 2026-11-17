#!/usr/bin/env python3
"""Git CHANGES: seven star rails must mount outside layout positioners.

Source contract, not operator visual acceptance. The shared Qt offscreen smoke
separately exercises NeonScrollBar.mountingParent and viewport geometry.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "widgets/GitChangesView.qml").read_text(encoding="utf-8")
COMPONENT = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")

assert "property Item mountingParent: null" in COMPONENT
assert "flickable.mapToItem(mountingParent, 0, 0)" in COMPONENT
assert 'geometryMode !== "viewport"' in COMPONENT

bars = re.findall(r"\bNeonScrollBar\s*\{([^}]*)\}", SOURCE, re.S)
assert len(bars) == 7, f"CHANGES expected seven rails, found {len(bars)}"
for index in range(1, 8):
    target = f"changesScroll{index}"
    matches = [block for block in bars if re.search(
        rf"\bflickable\s*:\s*{target}\b", block
    )]
    assert len(matches) == 1, f"{target}: expected one rail"
    block = matches[0]
    parent_path = (
        f"{target}.parent" if index == 5 else f"{target}.parent.parent"
    )
    assert 'handleStyle: "star"' in block, f"{target}: preserve stars"
    assert f"mountingParent: {parent_path}" in block, (
        f"{target}: do not reparent into a Column or the global root"
    )
    assert 'geometryMode: "viewport"' in block, (
        f"{target}: align to scroll viewport, not full pane/header"
    )
    assert re.search(
        rf"Flickable\s*\{{\s*id:\s*{target}\b", SOURCE
    ), f"{target}: viewport disappeared"

# The fifth rail lives directly in a Rectangle, unlike its six Column peers.
# Keeping its own local parent preserves correct submode visibility.
assert "mountingParent: changesScroll5.parent\n" in SOURCE
assert "mountingParent: root" not in SOURCE

print("Git CHANGES seven star rail containment: PASS")
