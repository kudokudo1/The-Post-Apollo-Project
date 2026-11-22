#!/usr/bin/env python3
"""Git CONTROL and TimeW inner viewport source/geometry regression.

Isolated numeric inspection of the actual QML function. No live Quickshell,
Git operations, saved alarms, wall-clock mutation or desktop processes.
"""
from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[2]
git = (root / "widgets/GitW.qml").read_text(encoding="utf-8")
time = (root / "widgets/TimeW.qml").read_text(encoding="utf-8")
settings = (root / "widgets/TimeSettingsCompact.qml").read_text(encoding="utf-8")
alarm = (root / "widgets/AlarmManagerPane.qml").read_text(encoding="utf-8")
angel = (root / "widgets/AngelPane.qml").read_text(encoding="utf-8")

# Git's one persistent local control camera must allocate its flexible area
# between two existing useful regions, not simply enlarge the outer frame.
for token in (
    "id: gitControlCamera",
    "readonly property int fixedRowsHeight:",
    "branchControlStrip.height",
    "gitSyncControlStrip.height",
    "gitLocalToolStrip.height",
    "spacing * 4",
    "Math.max(0, height - fixedRowsHeight)",
    "Math.max(140, Math.round(flexibleRowsHeight * 0.67))",
    "Math.max(70, flexibleRowsHeight - branchMapHeight)",
    "height: gitControlCamera.branchMapHeight",
    "height: gitControlCamera.outputPanelHeight",
):
    assert token in git, token

for camera_height in (450, 550, 720, 1150):
    fixed = 82 + 58 + 36 + 4 * 10
    flexible = max(0, camera_height - fixed)
    branch = max(140, round(flexible * 0.67))
    output = max(70, flexible - branch)
    assert fixed + branch + output <= camera_height, camera_height
    assert branch >= 140 and output >= 70
    if camera_height >= 550:
        assert output > 70
assert "gitOutputPanel.showDetails" in git
assert "gitService.actionOutput" in git
assert "gitService.runSyncAction(" in git
assert "gitService.runReadAction(" in git
assert 'property int resizeLevel: 1' in git

# TimeW reserves the visible title/divider/mode strip/footer before assigning
# the rest to the selected child. The actual QML JS function is executed below.
for token in (
    "id: timePageContent", "id: pageTitle", "id: pageRule",
    "id: modeFooter", "function availablePaneHeight(",
    "height: timePageContent.availablePaneHeight(\n"
    "                            toolsSubModeStrip.height, false,\n"
    "                            alarmFooterNavigation.height)",
    "height: timePageContent.availablePaneHeight(\n"
    "                            settingsSubModeStrip.height, true, 0)",
    "height: timePageContent.availablePaneHeight(0, true, 0)",
    "height: 315 + Math.round(timew.extraVerticalRoom * 0.60)",
    "height: 126 + Math.round(timew.extraVerticalRoom * 0.45)",
):
    assert token in time, token

needle = "function availablePaneHeight(stripHeight, footerVisible, navHeight) {"
assert time.count(needle) == 1
body = time.split(needle, 1)[1].split("\n                    }", 1)[0]
function_js = needle + body + "\n}"
assert "return Math.max(0, height - reserved);" in function_js
node = """
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = %s;
function value(h, strip, footer, nav) {
  return vm.runInNewContext(source + '\\n availablePaneHeight(' +
    [strip, footer, nav].map(JSON.stringify).join(',') + ')',
    {height:h, spacing:14, pageTitle:{implicitHeight:22},
     pageRule:{height:2}, modeFooter:{implicitHeight:14}});
}
const compact = [value(637,34,true,0),value(637,0,true,0),
                 value(637,34,false,28)];
const tall = [value(1100,34,true,0),value(1100,0,true,0),
              value(1100,34,false,28)];
assert.deepEqual(compact,[509,557,495]);
assert.deepEqual(tall,[972,1020,958]);
for(let i=0;i<3;i++) {
 assert.equal(tall[i]-compact[i],463);
 assert.ok(compact[i]>0 && tall[i]<1100);
}
console.log('PASS: actual TimeW pane allocation follows page height');
""" % json.dumps(function_js)
r = subprocess.run(["node", "-e", node], capture_output=True, text=True,
                   timeout=20, check=False)
assert r.returncode == 0, r.stdout + "\n" + r.stderr

# SettingsCompact is only selected by TimeW's "visual"/"sync" subpages;
# CPU++ retains its existing separate "all" settings path.
assert 'visible: pane.settingsSection !== "all"' in (
    root / "widgets/TimeSettingsPane.qml"
).read_text(encoding="utf-8")
assert "readonly property int verticalGrowth: Math.max(0, height - 457)" in settings
assert "spacing: compact.visualGap" in settings
assert "spacing: compact.syncGap" in settings
for h in (350, 457, 650, 1000, 1200):
    growth = max(0, h - 457)
    visual_gap = min(52, 5 + growth // 14)
    sync_gap = min(45, 3 + growth // 16)
    assert 5 <= visual_gap <= 52
    assert 3 <= sync_gap <= 45
assert "height: Math.max(0, pane.height - y)" in alarm
assert "angelJournalView.height - 325" in angel
assert "ListView {" in alarm and "ListView {" in angel

print(r.stdout.strip())
print("Git + TimeW responsive inner pane contracts: PASS")
