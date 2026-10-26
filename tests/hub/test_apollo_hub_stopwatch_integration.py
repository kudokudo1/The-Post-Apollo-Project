#!/usr/bin/env python3
"""P3 direct stopwatch: one TimeW monotonic owner, one existing Hub tile tick."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

owner = read("widgets/TimeW.qml")
shell = read("shell.qml")
hub = read("widgets/ApolloHubW.qml")
tile = read("widgets/hub/ApolloHubTile.qml")
mini = read("widgets/hub/ApolloHubTimeMini.qml")
controls = read("widgets/hub/ApolloHubStopwatchControls.qml")

for token in (
    'readonly property var hubStopwatchSnapshot:',
    'source: "timew-monotonic-stopwatch"',
    'StopwatchPolicy.format(stopwatchDisplayMs)',
    'function hubRefreshStopwatch()',
    'function hubStopwatchAction(action)',
    'startStopwatch();', 'pauseStopwatch();',
    'lapStopwatch();', 'resetStopwatch();',
    'stopwatchAnchor.elapsed() * 1000',
):
    assert token in owner, f"TimeW owner seam absent: {token}"

for token in (
    'stopwatchSnapshot: timewWindow',
    'timewWindow.hubStopwatchSnapshot : null',
    'onStopwatchActionRequested: function(action)',
    'timewWindow.hubStopwatchAction(action);',
    'onStopwatchSampleRequested:',
    'timewWindow.hubRefreshStopwatch();',
):
    assert token in shell, f"Shell TimeW route absent: {token}"

for token in (
    'property var stopwatchSnapshot: null',
    'signal stopwatchActionRequested(string action)',
    'signal stopwatchSampleRequested()',
    'function requestStopwatchAction(action)',
    'stopwatchSnapshot.source !== "timew-monotonic-stopwatch"',
    'stopwatchSnapshot: hub.stopwatchSnapshot',
    'hub.requestStopwatchAction(action);',
    'hub.stopwatchSampleRequested();',
):
    assert token in hub, f"Hub TimeW action contract absent: {token}"

for token in (
    'property date now: new Date()',
    'onTriggered: tile.now = new Date()',
    'onNowChanged:',
    'stopwatchSampleRequested();',
    'property var stopwatchSnapshot: null',
    'signal stopwatchActionRequested(string action)',
    'signal stopwatchSampleRequested()',
    'stopwatchSnapshot: tile.stopwatchSnapshot',
    'tile.stopwatchActionRequested(action);',
):
    assert token in tile, f"Hub Time tile forwarding absent: {token}"

for token in (
    'signal stopwatchActionRequested(string action)',
    'property string selectedTool: "clock"',
    'label: "CLOCK"',
    'label: "STOPWATCH"',
    'ApolloHubStopwatchControls {',
    'stopwatchSnapshot: timeMini.stopwatchSnapshot',
    'timeMini.stopwatchActionRequested(action);',
    'timeSnapshot.displayTime',
):
    assert token in mini, f"Hub Time view contract absent: {token}"

for token in (
    'property var stopwatchSnapshot: null',
    'signal actionRequested(string action)',
    'readonly property bool running:',
    'label: stopwatchUi.running ? "PAUSE" : "START"',
    'label: "LAP"',
    'label: "RESET STOPWATCH"',
    'stopwatchUi.actionRequested("lap")',
    'stopwatchUi.actionRequested("reset")',
    'LAP " + String(modelData.index)',
):
    assert token in controls, f"Direct stopwatch controls absent: {token}"

# Controls must not create a second StopwatchPolicy state, clock or timer.
assert tile.count("Timer {") == 1
assert owner.count("ElapsedTimer {") >= 1
for forbidden in ("Timer {", "ElapsedTimer {", "SystemClock {",
                  "Quickshell.execDetached(", "Process {", "FileView {",
                  "Date.now(", "stopwatchAccumulatedMs:"):
    assert forbidden not in controls + mini, (
        "Stopwatch control accidentally owns a new backend: " + forbidden)

# Regression for the QtQuick.Item reserved data/state property failures.
for component in (mini, controls):
    for prop in ("data", "state", "children", "resources", "parent"):
        pattern = (r"^\s*(?:readonly\s+)?property\s+"
                   r"\w+\s+" + prop + r"\s*:")
        # Ensure this check would reject an intentionally injected mistake.
        assert re.search(pattern, "    readonly property var " + prop + ": null", re.M)
        assert not re.search(pattern, component, re.M), (
            "Reserved Item property override: " + prop)

print("ApolloHub TimeW direct stopwatch owner contracts passed")
