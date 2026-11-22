#!/usr/bin/env python3
"""Finance-only pilot: shared resize arrows preserve existing chassis ownership."""

from pathlib import Path

root = Path(__file__).resolve().parents[2]
finance = (root / "widgets/FinanceW.qml").read_text(encoding="utf-8")
shared = (root / "components/ResizeButton.qml").read_text(encoding="utf-8")

header = finance.split("id: financeHeader", 1)[1].split("id: headerDivider", 1)[0]
assert header.count("ResizeButton {") == 2
assert "ActionButton {" not in header

down = header.split("id: collapseChassisButton", 1)[1].split("ResizeButton {", 1)[0]
up = header.split("id: expandChassisButton", 1)[1].split("id: financeFeedIndicator", 1)[0]
for block, direction, boundary, delta, callback in (
    (down, "down", "compact", "-1", "root.collapseChassis();"),
    (up, "up", "fullscreen", "1", "root.expandChassis();"),
):
    assert f'direction: "{direction}"' in block
    assert f'available: root.chassisLevel !== "{boundary}"' in block
    assert f"if (delta !== {delta})" in block
    assert callback in block
    assert "root.keyboardOwnershipRequested();" in block
    assert "onResizeRequested: function(delta)" in block
    assert "onLeftClicked:" not in block
    assert "width:" not in block and "height:" not in block

assert "anchors.right: expandChassisButton.left" in down
assert "anchors.rightMargin: 4" in down
assert "anchors.right: financeFeedIndicator.left" in up
assert "anchors.rightMargin: 7" in up
assert "anchors.verticalCenter: parent.verticalCenter" in down
assert "anchors.verticalCenter: parent.verticalCenter" in up

# The shared component only emits an intent; Finance still owns its policy.
assert "signal resizeRequested(int delta)" in shared
assert "height: width" in shared
assert "implicitWidth: 30" in shared
assert "labelPixelSize: 17" in shared
assert "property color decreaseAccentColor: Colors.orange" in shared
assert 'property color increaseAccentColor: "#A46AFF"' in shared
assert 'FinanceChassisPolicy.step(chassisLevel, 1)' in finance
assert 'FinanceChassisPolicy.step(chassisLevel, -1)' in finance
assert "property string chassisLevel: \"compact\"" in finance
print("Finance ResizeButton pilot contracts PASS")
