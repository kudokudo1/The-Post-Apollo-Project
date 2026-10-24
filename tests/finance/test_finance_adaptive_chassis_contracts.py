#!/usr/bin/env python3
"""M0 guarded window resizing and in-workspace tools source contracts."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
menu = (root / "widgets/FinanceW.qml").read_text(encoding="utf-8")
policy = (root / "widgets/FinanceChassisPolicy.js").read_text(encoding="utf-8")
host = (root / "widgets/FinanceToolHost.qml").read_text(encoding="utf-8")
git = (root / "widgets/GitW.qml").read_text(encoding="utf-8")

assert 'import "FinanceChassisPolicy.js" as FinanceChassisPolicy' in menu
assert 'property string chassisLevel: "compact"' in menu
assert 'readonly property var chassisFrame: FinanceChassisPolicy.frame(' in menu
assert 'readonly property int frameWidth: chassisFrame.width' in menu
assert 'readonly property int frameHeight: chassisFrame.height' in menu
# Compact Finance and Git share a 9px top line; Finance's 3px lift is
# against its own 12px glow gutter, not the current Git chassis inset.
assert 'property int panelHeight: 790' in git
assert 'property int topGlowGutter: 9' in git
assert 'mode === "expanded" ? 900 : 790' in policy
assert 'readonly property int compactTopLift: 3' in menu
assert 'chassisLevel === "compact" ? glowGutter - compactTopLift : glowGutter' in menu
assert 'implicitHeight: frameHeight + frameTopInset + glowGutter' in menu
assert 'y: root.frameTopInset' in menu
assert 'anchors.topMargin: root.frameTopInset' in menu
assert 'FinanceChassisPolicy.topMargin(' in menu
assert 'FinanceChassisPolicy.leftMargin(' in menu
assert 'chassisLevel = FinanceChassisPolicy.step(chassisLevel, 1);' in menu
assert 'chassisLevel = FinanceChassisPolicy.step(chassisLevel, -1);' in menu
assert 'id: expandChassisButton' in menu
assert 'id: collapseChassisButton' in menu
assert 'available: root.chassisLevel !== "fullscreen"' in menu
assert 'available: root.chassisLevel !== "compact"' in menu
assert 'onLeftClicked: {' in menu
assert 'root.expandChassis();' in menu
assert 'root.collapseChassis();' in menu

# Window object remains mapped; region and focus gate resize with the frame.
assert menu.count('PanelWindow {') == 1
assert 'visible: true' in menu
assert 'mask: Region {' in menu
assert 'width: root.menuOpen ? root.frameWidth : 0' in menu
assert 'height: root.menuOpen ? root.frameHeight : 0' in menu
assert 'WlrLayershell.layer: WlrLayer.Overlay' in menu
assert 'WlrKeyboardFocus.None' in menu
assert 'WlrKeyboardFocus.OnDemand' in menu
assert 'WlrKeyboardFocus.Exclusive' in menu
assert 'onMenuOpenChanged:' in menu
size_functions = menu[menu.index('function expandChassis()'):
                      menu.index('function toggle()')]
for dangerous in ('menuOpen =', 'clear()', 'refresh()', 'financeWrite.submit(',
                  'financeAllocationWrite.submit(', 'financeFundingWrite.submit('):
    assert dangerous not in size_functions, dangerous

# Reserved domains use a local tool slot. Its Loader is never controlled by
# window size or visibility: a resize cannot destroy the hosted instance.
assert menu.count('FinanceToolHost {') == 1
assert 'id: financeToolHost' in menu
assert 'visible: !actualBudgetPage.visible' in menu
assert 'property Component embeddedComponent: null' in host
assert 'active: host.toolConnected' in host
assert 'sourceComponent: host.embeddedComponent' in host
assert 'visible: host.toolConnected' in host
assert 'IN-WORKSPACE TOOL // NOT CONNECTED' in host
assert 'function frame(level, viewportWidth, viewportHeight, gutter)' in policy
assert 'function step(level, direction)' in policy
for forbidden in ('Qt.openUrlExternally', 'Process {', 'openUrl(',
                  'exec(', 'financeWrite.submit(', 'financeFundingWrite.submit('):
    assert forbidden not in host, forbidden

print("FinanceW M0 adaptive chassis and internal host contracts: PASS")
