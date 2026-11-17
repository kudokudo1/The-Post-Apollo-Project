#!/usr/bin/env python3
"""Finance Budget scrollbar integration contract.

Checks the real FinanceW wiring and reactive geometry component source.
The separate offscreen Qt test verifies that actual positions move.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
FINANCE = (ROOT / "widgets/FinanceW.qml").read_text(encoding="utf-8")
OVERLAY = (ROOT / "widgets/FinanceBudgetScrollRail.qml").read_text(encoding="utf-8")
NEON = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")

assert re.search(r"Flickable\s*\{\s*id:\s*budgetScroll\b", FINANCE)
assert re.search(r"Rectangle\s*\{\s*id:\s*emptyPage\b", FINANCE)
assert re.search(r"Column\s*\{\s*id:\s*actualBudgetPage\b", FINANCE)
assert "width: Math.max(0, budgetScroll.width - 22)" in FINANCE
assert len(re.findall(r"\bFinanceBudgetScrollRail\s*\{", FINANCE)) == 1
assert re.search(
    r"FinanceBudgetScrollRail\s*\{\s*id: budgetScrollBar\s+"
    r"scrollTarget: budgetScroll\s+layoutHost: actualBudgetPage", FINANCE
)
assert FINANCE.index("id: budgetList") < FINANCE.index("id: budgetScrollBar")
assert FINANCE.index("id: budgetScrollBar") < FINANCE.index("id: financeToolHost")
assert "mountingParent: emptyPage" not in FINANCE, (
    "Old coordinate-mapped rail must not remain on the Finance host"
)
for needle in (
    "layoutHost.parent === root.parent",
    "scrollTarget.parent === layoutHost",
    "x: validHierarchy ? layoutHost.x + scrollTarget.x : 0",
    "y: validHierarchy ? layoutHost.y + scrollTarget.y : 0",
    "width: validHierarchy ? Math.max(0, scrollTarget.width) : 0",
    "height: validHierarchy ? Math.max(0, scrollTarget.height) : 0",
    "visible: validHierarchy && layoutHost.visible && scrollTarget.visible",
    "mountingParent: root",
    "geometryHost: root",
    'geometryMode: "box"',
    'handleStyle: "bar"',
    "rightInset: 2",
    "visible: root.visible && scrollable",
):
    assert needle in OVERLAY, f"Finance Budget reactive overlay missing {needle}"

assert "mapToItem(" not in OVERLAY.split("Item {", 1)[1].split("Shared.NeonScrollBar", 1)[0], (
    "Reactive overlay positioning must not use opaque coordinate mapping"
)
assert "property Item mountingParent: null" in NEON
print("Finance Budget reactive viewport rail source contract: PASS")
