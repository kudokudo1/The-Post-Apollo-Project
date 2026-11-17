#!/usr/bin/env python3
"""Finance Budget scrollbar: local host, read-only viewport, mode visibility.

This validates the QML source contract, not a native Quickshell rendering.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
NEON = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")
assert "property Item mountingParent: null" in NEON
assert "flickable.mapToItem(mountingParent, 0, 0)" in NEON
assert 'geometryMode !== "viewport"' in NEON

assert re.search(r"Flickable\s*\{\s*id:\s*budgetScroll\b", SOURCE)
assert re.search(r"Rectangle\s*\{\s*id:\s*emptyPage\b", SOURCE)
assert re.search(r"Column\s*\{\s*id:\s*actualBudgetPage\b", SOURCE)
assert "width: Math.max(0, budgetScroll.width - 22)" in SOURCE
bars = re.findall(r"\bNeonScrollBar\s*\{([^{}]*)\}", SOURCE, re.S)
matches = [block for block in bars if "id: budgetScrollBar" in block]
assert len(matches) == 1, f"Finance Budget rail count {len(matches)}"
bar = matches[0]
for needle in (
    "flickable: budgetScroll",
    "mountingParent: emptyPage",
    'geometryMode: "viewport"',
    'handleStyle: "bar"',
    "rightInset: 2",
    "visible: actualBudgetPage.visible",
    "&& budgetScroll.visible",
    "&& scrollable",
):
    assert needle in bar, f"Budget bar missing {needle}"
assert "mountingParent: actualBudgetPage" not in bar
assert "mountingParent: budgetScroll.parent" not in bar
assert SOURCE.index("id: budgetList") < SOURCE.index("id: budgetScrollBar")
assert SOURCE.index("id: budgetScrollBar") < SOURCE.index("id: financeToolHost")
print("Finance Budget rail viewport/mode containment: PASS")
