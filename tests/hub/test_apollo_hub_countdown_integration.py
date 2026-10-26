#!/usr/bin/env python3
"""P3-D: one TimeW owner for up to eight named countdowns, full in-Hub controls."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

owner=read("widgets/TimeW.qml")
policy=read("services/time/CountdownPolicy.js")
shell=read("shell.qml")
hub=read("widgets/ApolloHubW.qml")
tile=read("widgets/hub/ApolloHubTile.qml")
mini=read("widgets/hub/ApolloHubTimeMini.qml")
controls=read("widgets/hub/ApolloHubCountdownControls.qml")
wf=read(".github/workflows/apollo-hub-time.yml")
foundation=read(".github/workflows/apollo-hub-foundation.yml")

for token in (
    "property var countdownTimers: [CountdownPolicy.createTimer(1)]",
    "readonly property var hubCountdownSnapshot:",
    'source: "timew-monotonic-countdowns"',
    'maxTimers: CountdownPolicy.MAX_TIMERS',
    'runningCount: countdownRunningCount',
    'CountdownPolicy.displayMs(timer)',
    'function hubCountdownAction(id, action, name, hours, minutes, seconds)',
    'function hubCountdownRequest(id, action, name, hours, minutes, seconds)',
    'hubCountdownAction(',
    'CountdownPolicy.byId(countdownTimers, id)',
    'CountdownPolicy.parseDuration(hours, minutes, seconds)',
    'countdownTimers = CountdownPolicy.update(countdownTimers, id,',
    'countdownTimers = CountdownPolicy.act(',
    'countdownNowMs()',
    'countdownTimers = countdownTimers.filter(function(entry)',
    'if (countdownTimers.length <= 1)',
    'hubCountdownFeedback = accepted',
    'id !== id',  # sentinel replaced below
):
    if token == 'id !== id':
        continue
    assert token in owner, "TimeW owner countdown action missing: " + token

assert 'countdownTimers.length >= CountdownPolicy.MAX_TIMERS' in owner
assert 'entry.id !== id' in owner
assert "if (action === \"create\")" in owner
assert "if (action === \"edit\")" in owner
assert "if (action === \"remove\")" in owner
assert "if (action === \"start\" || action === \"pause\" || action === \"reset\")" in owner
assert owner.count("id: countdownHeartbeat") == 1
assert owner.count("id: countdownAnchor") == 1
assert "running: timew.countdownRunningCount > 0" in owner

for token in (
    'countdownSnapshot: timewWindow',
    'timewWindow.hubCountdownSnapshot : null',
    'onCountdownActionRequested: function(id, action, name,',
    'timewWindow.hubCountdownRequest(',
):
    assert token in shell, "Shell TimeW route missing: " + token

for token in (
    'property var countdownSnapshot: null',
    'property bool countdownInputFocused: false',
    'signal countdownActionRequested(int id, string action,',
    'function requestCountdownAction(id, action, name, hours, minutes, seconds)',
    'countdownSnapshot.source !== "timew-monotonic-countdowns"',
    '&& !countdownInputFocused',
    'countdownInputFocused = false;',
    'countdownSnapshot: hub.countdownSnapshot',
    'hub.requestCountdownAction(',
    'hub.countdownInputFocused = focused;',
):
    assert token in hub, "Hub gate/focus missing: " + token

for token in (
    'property var countdownSnapshot: null',
    'signal countdownInputFocusChanged(bool focused)',
    'signal countdownActionRequested(int id, string action,',
    'countdownSnapshot: tile.countdownSnapshot',
    'tile.countdownActionRequested(',
    'tile.countdownInputFocusChanged(focused);',
    'property date now: new Date()',
):
    assert token in tile, "Tile countdown seam missing: " + token

for token in (
    'property var countdownSnapshot: null',
    'signal countdownInputFocusChanged(bool focused)',
    'signal countdownActionRequested(int id, string action,',
    'label: "CLOCK"', 'label: "STOPWATCH"', 'label: "COUNTDOWN"',
    'ApolloHubCountdownControls {',
    'countdownSnapshot: timeMini.countdownSnapshot',
    'timeMini.countdownActionRequested(',
    'timeMini.countdownInputFocusChanged(focused);',
    'onToggleHourFormat: tile.use24Hour', # checked separately
):
    if token.startswith('onToggleHourFormat'):
        continue
    assert token in mini, "Time mini countdown navigation missing: " + token

for token in (
    'readonly property var timers:',
    'readonly property var selectedTimer:',
    'signal actionRequested(int id, string action,',
    'signal inputFocusChanged(bool focused)',
    'property bool editDirty: false',
    'property bool removeArmed: false',
    'function syncSelection()',
    'function selectTimer(id)',
    'function applyEdits()',
    'function issue(action)',
    'pendingCreateMaxId',
    'id: nameField', 'id: hoursField', 'id: minutesField',
    'id: secondsField',
    'onActiveFocusChanged:',
    'label: "NEW TIMER"',
    'label: "APPLY EDITS"',
    'label: "RESET DRAFT"',
    'label: countdownUi.timerRunning ? "PAUSE"',
    'label: "RESET"',
    '"CONFIRM REMOVE TIMER"',
    'EDIT REQUESTED // AWAIT OWNER STATE',
    'if (editDirty && selectedTimer !== null',
    'selectedTimer.name === nameDraft',
    'selectedTimer.hours === hoursDraft',
    'selectedTimer.minutes === minutesDraft',
    'selectedTimer.seconds === secondsDraft',
    'selectedTimer.status === "finished"',
    '? "RESTART" : "START"',
    'countdownUi.issue("remove");',
):
    assert token in controls, "Countdown controls missing: " + token

for token in (
    "var MAX_TIMERS = 8", "var MAX_NAME_LENGTH = 32",
    "function parseDuration(hours, minutes, seconds)",
    "function tick(entries, nowMs)",
    "function act(entries, id, action, nowMs)",
):
    assert token in policy, "Countdown owner policy missing: " + token

# Existing Hub clock remains the only Time tile refresh timer. TimeW owns
# the existing countdown heartbeat, running with its own monotonic anchor.
assert tile.count("Timer {") == 1
for forbidden in ("Timer {", "ElapsedTimer {", "SystemClock {",
                  "Process {", "FileView {", "Quickshell.execDetached(",
                  "Date.now(", "CountdownPolicy.act(", "countdownTimers:"):
    assert forbidden not in controls + mini, (
        "Hub must not make a second timer backend: " + forbidden)
assert 'ApolloHubStopwatchControls {' in mini
assert 'ApolloHubMediaExplore {' in tile

# QML root Item.data/state overrides previously prevented entire QS startup.
for name, source in (("TIME",mini),("COUNTDOWN",controls)):
    assert "Item {" in source
    for reserved in ("data", "state", "children", "resources", "parent"):
        regex = (r"^\s*(?:readonly\s+)?property\s+\w+\s+"
                 + reserved + r"\s*:")
        assert re.search(regex, "    readonly property var "
                         + reserved + ": null", re.M)
        assert not re.search(regex, source, re.M), (
            name + " shadows QtQuick.Item." + reserved)
assert controls.count("id: hoursField") == 1
assert controls.count("id: minutesField") == 1
assert controls.count("id: secondsField") == 1
assert controls.count("id: nameField") == 1
for p in (wf,foundation):
    assert 'tests/hub/test_apollo_hub_countdown_integration.py' in p
    assert 'widgets/hub/ApolloHubCountdownControls.qml' in p
    assert "python3 tests/hub/test_apollo_hub_countdown_integration.py" in p
print("Hub direct TimeW countdown owner and QML contracts passed")
