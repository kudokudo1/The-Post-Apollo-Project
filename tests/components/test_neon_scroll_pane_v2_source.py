#!/usr/bin/env python3
"""Source contracts: Finance Market layout owns scroll extent, rail owns viewport.

Generic component runtime assertions belong to test_neon_scroll_pane_v2_qt.py.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
market = (ROOT / "widgets/FinanceMarketPane.qml").read_text(encoding="utf-8")
shared = (ROOT / "components/NeonScrollPaneV2.qml").read_text(encoding="utf-8")
qmldir = (ROOT / "components/qmldir").read_text(encoding="utf-8")

assert 'property string viewportPolicy: "fill"' in shared
assert 'property real availableExtent: 0' in shared
assert 'property real splitFraction: 0.46' in shared
assert 'property real fixedExtent: 210' in shared
assert 'default property alias contentData: scrollContents.data' in shared
assert 'Flickable {' in shared
assert 'NeonScrollBar {' in shared
assert 'mountingParent: root' in shared
assert 'geometryHost: root' in shared
assert 'geometryMode: "box"' in shared
assert 'visible: root.visible && scrollable' in shared
assert 'NeonScrollPaneV2 1.0 NeonScrollPaneV2.qml' in qmldir
assert 'property string marketScrollPolicy: "fill"' in market
assert 'property int fixedMarketListHeight: 210' in market
assert 'marketList.height' not in market  # no accidental imperative height write
assert 'height: pane.wide ? parent.height : marketScrollPane.preferredExtent' in market
assert 'viewportPolicy: pane.wide ? "fill" : pane.marketScrollPolicy' in market
assert 'availableExtent: body.height' in market
assert 'contentExtent: marketRows.height' in market
assert 'width: Math.max(0, marketScrollPane.flickable.width - marketScrollPane.contentGutter)' in market
assert 'id: marketLayoutControls' in market
for name in ('FULL', 'SPLIT', 'FIXED'):
    assert f'label:"{name}"' in market or f'label: "{name}"' in market
assert 'pane.narrowDetailOpen = true;' in market
assert 'pane.narrowDetailOpen = false' in market
assert 'id: backToMarketList' in market
assert 'visible: pane.wide || pane.marketScrollPolicy !== "fill"' in market
assert '|| pane.narrowDetailOpen' in market
assert '|| !pane.narrowDetailOpen' in market
assert 'marketScroller' not in market
assert 'marketIndexScrollBar' not in market
assert 'NeonScrollBar {' not in market, "no second direct scrollbar"
print("Market ScrollPane V2 layout policy, native track ownership and details access: PASS")
