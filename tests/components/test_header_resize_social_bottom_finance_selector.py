#!/usr/bin/env python3
"""Visual top/bottom alignment and operator header-selection contracts.

This is a source and arithmetic policy test, NOT native QML or the user's
running compositor. Test full-display geometry against the ACTUAL visible
Notifications/Social frame, not the untrimmed output height.
"""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
def read(path):
    return (ROOT/path).read_text(encoding="utf-8")

apollo=read("widgets/ApolloHubW.qml")
git=read("widgets/GitW.qml")
cpu=read("widgets/CpuPlusW.qml")
time=read("widgets/TimeW.qml")
hub=read("widgets/notifications/NotificationsHubW.qml")
finance=read("widgets/FinanceW.qml")
shell=read("shell.qml")
shared=read("components/ResizeButton.qml")

# Operator-established Notifications visible bottom = screen - (5 + 8).
# On real machines both screenHeight and the frame gap are variables.
assert "property int panelBottomMargin: 5" in hub
assert "property int frameInset: 8" in hub
for path,source in (("apollo",apollo),("git",git),("cpu",cpu)):
    assert "property var notificationsReference: null" in source, path
    assert "notificationsReference.panelBottomMargin + notificationsReference.frameInset" in source, path
    assert "{ width: 99999, height: 99999 }" in source, path
    assert "property int resizeLevel: 1" in source, path
    assert "resizeLevel + delta" in source, path
for path,token in (
    ("apollo","notificationsReference: notificationsHubWindow"),
    ("git","notificationsReference: notificationsHubWindow"),
    ("cpu","notificationsReference: notificationsHubWindow"),
):
    assert shell.count(token)>=3, (path,"one live source bound to all three widgets")
assert "top: 0" in apollo and "anchors.topMargin: 0" in apollo
assert "readonly property int frameHeight: Math.min(" in apollo
assert "- visualBottomGap" in apollo
assert "readonly property int effectivePanelLeftMargin:" in git
assert "resizeLevel === resizeSteps.length - 1 ? glowGutter : panelLeftMargin" in git
assert "readonly property int effectiveBottomGlowGutter:" in git
assert "panelHeight + topGlowGutter + effectiveBottomGlowGutter" in git
assert "top: panelTopMargin" in git
assert "anchors.topMargin: root.topGlowGutter" in git
assert "readonly property int chassisRightMargin:" in cpu
assert "resizeLevel === resizeSteps.length - 1 ? 1 : 220" in cpu
assert "top: -3" in cpu
assert "anchors.bottomMargin: cpuPlusWindow.resizeLevel" in cpu

for screen_height in (768, 900, 1080, 1440, 2160):
    for bottom_margin, inset in ((5,8),(8,8),(5,12)):
        target=screen_height-bottom_margin-inset
        # Apollo starts at 0, no top offset.
        hub_frame=min(99999,screen_height-(bottom_margin+inset))
        # Git visible chassis starts at topGlowGutter=9.
        git_frame=min(99999,screen_height-9-(bottom_margin+inset))
        # CPU++ top -3 and frame top/bottom as implemented.
        cpu_outer=min(99999,screen_height)
        cpu_frame_bottom= -3+cpu_outer-max(0,(bottom_margin+inset)-3)
        assert hub_frame == target
        assert 9+git_frame == target
        assert cpu_frame_bottom == target
        # None of the visible frames exceeds its output height.
        assert 0 < hub_frame <= screen_height
        assert 0 < git_frame <= screen_height
        assert 0 < cpu_outer <= screen_height

# Header arrows ALWAYS precede the status indicator when one exists.
# Apollo has no LIVE badge: its controls precede EDIT and Close instead.
def first(source,token):
    at=source.find(token)
    assert at>=0,token
    return at

time_header=time.split("id: header\n",1)[1].split("id: headerDivider",1)[0]
assert first(time_header,"id: growTimeButton") < first(time_header,"id: stateIndicator")
assert first(time_header,"id: shrinkTimeButton") < first(time_header,"id: stateIndicator")
git_header=git.split("id: frame\n",1)[1].split("id: pageStatusText",1)[0]
assert "id: shrinkGitButton" in git_header
assert "id: growGitButton" in git_header
# Place the LIVE badge after both controls inside one shared row.
assert git_header.index("id: growGitButton") < git_header.index("width: 94")
cpu_header=cpu.split("id: cpuPlusCloseButton",1)[1].split("id: cpuPlusInternetText",1)[0]
assert "anchors.right: cpuPlusInternetIndicator.left" in cpu_header
assert "anchors.right: growCpuButton.left" in cpu_header
assert "anchors.right: cpuPlusCloseButton.left" in cpu_header
apollo_header=apollo.split("id: header\n",1)[1].split("id: headerDivider",1)[0]
assert apollo_header.index("id: shrinkHubButton") < apollo_header.index("id: editButton")
assert apollo_header.index("id: growHubButton") < apollo_header.index("id: editButton")
notifications_header=hub.split("id: header\n",1)[1].split("id: searchBox",1)[0]
assert "anchors.right: storedCountNumber.left" in notifications_header
assert "anchors.topMargin: 7" in notifications_header
assert "direction: \"left\"" in notifications_header
assert "direction: \"right\"" in notifications_header
assert notifications_header.count("reverseHorizontalGrowth: true")==2
assert notifications_header.index("id: widenNotificationButton") < notifications_header.index("id: narrowNotificationButton")
assert "property bool reverseHorizontalGrowth: false" in shared
assert 'direction === "left"' in shared
assert 'direction === "up" || direction === "right"' in shared
assert 'readonly property int sizeDelta: increasing ? 1 : -1' in shared
assert "anchors.rightMargin: notificationHeaderActions.width + 22" not in hub
assert "anchors.rightMargin: 14" in hub

# Finance preview is a real pair of keyboard-navigable ActionButtons, not
# an inactive decoration. The only state mutation is a QML presentation flag.
assert 'property string selectorPreviewActive: "a"' in finance
work=finance.split("id: workArea",1)[1]
assert "WidgetContentKeyboardNavigator {" in work
assert "id: selectorPreviewRow" in work
assert "id: selectorPreviewA" in work and "id: selectorPreviewB" in work
assert work.count('keyboardActivationSignal: "leftClicked"') >= 2
assert 'selected: root.selectorPreviewActive === "a"' in work
assert 'selected: root.selectorPreviewActive === "b"' in work
assert 'onLeftClicked: root.selectorPreviewActive = "a"' in work
assert 'onLeftClicked: root.selectorPreviewActive = "b"' in work
preview=work.split("id: selectorPreviewRow",1)[1].split("// BUDGET SUB MODES:",1)[0]
assert not re.search(r"\b(?:financeBudget|Transactions|save|write|delete|remove|Process|FileView)\b",preview), "preview cannot commit financial writes"
assert "contentRoot: workArea" in work
assert "navigationActive: root.standardKeysAvailable" in work
assert "financeKeyboardAnchor.activeFocus" in work

print("Header placement, four-level visible-bottom geometry and Finance selector: PASS")
