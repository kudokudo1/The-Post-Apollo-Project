#!/usr/bin/env python3
"""Finance research pane bars: mounted, host-contained, and content-clear.

Source contract only; native Quickshell geometry/interaction is operator-gated.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
CASES = (
    ("FinanceSecDocumentInspector.qml", "scroller", "inspector", "secDocumentScrollBar"),
    ("FinanceSecFilingsPane.qml", "filingScroll", "filingList", "filingIndexScrollBar"),
    ("FinanceMarketPane.qml", "marketScroller", "marketList", "marketIndexScrollBar"),
    ("FinanceResearchCrawlPane.qml", "pagesScroll", "pageList", "crawlPagesScrollBar"),
    ("FinanceResearchCrawlPane.qml", "detailsScroll", "detail", "crawlDetailsScrollBar"),
)
files = {}
for filename, target, host, bar_id in CASES:
    source = files.setdefault(
        filename, (ROOT / "widgets" / filename).read_text(encoding="utf-8")
    )
    assert re.search(rf"\bFlickable\s*\{{\s*id:\s*{target}\b", source), (
        f"{filename}: missing scroll target {target}"
    )
    bars = re.findall(r"\bNeonScrollBar\s*\{([^{}]*)\}", source, flags=re.S)
    matches = [block for block in bars if re.search(
        rf"\bid:\s*{bar_id}\b", block
    )]
    assert len(matches) == 1, f"{filename}: expected 1 {bar_id}, got {len(matches)}"
    block = matches[0]
    for needle in (
        f"flickable: {target}",
        f"mountingParent: {host}",
        'geometryMode: "viewport"',
        'handleStyle: "bar"',
        "rightInset: 2",
    ):
        assert needle in block, f"{filename}/{bar_id}: missing {needle}"
    assert f"width: Math.max(0, {target}.width - 22)" in source, (
        f"{filename}/{target}: reserve a content gutter for the rail"
    )
    assert "scroll" in target.lower() or target == "scroller"

for filename, source in files.items():
    target_count = len(re.findall(r"\b(?:Flickable|ListView|GridView)\s*\{", source))
    bar_count = len(re.findall(r"\bNeonScrollBar\s*\{", source))
    assert target_count == bar_count, (
        f"{filename}: scroll targets {target_count}, bars {bar_count}"
    )
    assert 'handleStyle: "star"' not in source, (
        f"{filename}: Finance is not a Git/Hospital star family"
    )

component = (ROOT / "components/NeonScrollBar.qml").read_text(encoding="utf-8")
assert "property Item mountingParent: null" in component
assert "flickable.mapToItem(mountingParent, 0, 0)" in component
assert 'geometryMode !== "viewport"' in component

print("Finance SEC, Market, Crawl scrollbar coverage: PASS (5 panes / 4 files)")
