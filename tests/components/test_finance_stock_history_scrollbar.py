#!/usr/bin/env python3
"""Finance stock-history scrollbar contract (source, not native visual approval)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "widgets/FinanceStockHistoryPane.qml").read_text(encoding="utf-8")
bar = re.findall(r"\bNeonScrollBar\s*\{([^{}]*)\}", SOURCE, re.S)
assert len(bar) == 1, f"Finance history should own one scrollbar, got {len(bar)}"
for needle in (
    "id: stockHistoryScrollBar",
    "flickable: scroll",
    "mountingParent: stocks",
    'geometryMode: "viewport"',
    'handleStyle: "bar"',
    "rightInset: 2",
):
    assert needle in bar[0], f"Finance stock history missing {needle}"
assert "width: Math.max(0, scroll.width - 24)" in SOURCE, (
    "Finance history chart/text must not overlap its scrollbar gutter"
)
assert re.search(r"Flickable\s*\{\s*id:\s*scroll\b", SOURCE)
assert len(re.findall(r"\b(?:Flickable|ListView|GridView)\s*\{", SOURCE)) == 1
print("Finance stock history scrollbar viewport/clearance: PASS")
