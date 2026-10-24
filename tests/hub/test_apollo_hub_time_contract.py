#!/usr/bin/env python3
"""B10 Time policy consumes the existing Hub tile clock, no extra watcher."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
policy=(ROOT/"services/hub/ApolloHubTimePolicy.js").read_text()
tile=(ROOT/"widgets/hub/ApolloHubTile.qml").read_text()
mini=(ROOT/"widgets/hub/ApolloHubTimeMini.qml").read_text()
timew=(ROOT/"widgets/TimeW.qml").read_text()
clock=(ROOT/"modules/Clock.qml").read_text()
shell=(ROOT/"shell.qml").read_text()
bridge=(ROOT/"services/hub/ApolloHubLiveBridge.qml").read_text()
workflow=(ROOT/".github/workflows/apollo-hub-time.yml").read_text()

for needle in (
    ".pragma library", "function snapshot(epochMs, use24Hour)",
    "function unavailable(reason)", "getFullYear()", "getMonth()",
    "getDate()", "getDay()", "getHours()", "getMinutes()",
    "getSeconds()", "getTimezoneOffset()", '"UTC" + sign',
    'state: "ready"', 'state: "unavailable"', "localDate:",
    "dateLabel:", "time24:", "time12:", "displayTime:",
    "utcOffsetMinutes:", "utcOffsetLabel:",
):
    assert needle in policy, "Missing B10 time contract: "+needle

assert "property date now: new Date()" in tile
assert 'interval: 1000' in tile
assert 'tile.moduleId === "time"' in tile
assert 'onTriggered: tile.now = new Date()' in tile
assert 'import "../../services/hub/ApolloHubTimePolicy.js" as TimePolicy' in tile
assert 'TimePolicy.snapshot(tile.now.getTime(), tile.use24Hour)' in tile
assert tile.count("Timer {")==1
assert 'ApolloHubTimeMini {' in tile
assert 'onToggleHourFormat: tile.use24Hour = !tile.use24Hour' in tile
assert 'timeSnapshot.displayTime' in mini
assert 'timeSnapshot.dateLabel' in mini
assert 'timeSnapshot.utcOffsetLabel' in mini
assert 'onLeftClicked: timeMini.toggleHourFormat()' in mini
assert "Timer {" not in mini and "SystemClock {" not in mini
assert "Qt.formatTime(" not in tile
assert "SystemClock {" in clock
assert "SystemClock {" in timew
assert shell.count("ApolloHubLiveBridge {")==1
assert "ApolloHubTimePolicy.js" not in bridge
# TimeW later adopted the shared pure formatter, but still owns its own
# SystemClock. Sharing formatting does not transfer timer/clock ownership.
assert 'import "../services/hub/ApolloHubTimePolicy.js" as LocalTimePolicy' in timew
assert 'LocalTimePolicy.snapshot(localClock.date.getTime(), use24Hour)' in timew
assert timew.count("SystemClock {") == 1
assert 'property bool use24Hour: true' in timew

for forbidden in (
    "Process {", "FileView {", "Timer {", "SystemClock {",
    "fetch(", "XmlHttpRequest", "Date.now(", "setHours(",
    "setTime(", "Quickshell.execDetached(", "HttpClient",
    "Intl.", "Qt.", "exec(",
):
    assert forbidden not in policy, "B10 cannot own clock/side effects: "+forbidden

for needle in (
    '"services/hub/ApolloHubTimePolicy.js"',
    '"tests/hub/test_apollo_hub_time_policy.cjs"',
    '"tests/hub/test_apollo_hub_time_contract.py"',
    "python3 tests/hub/test_apollo_hub_time_contract.py",
    "TZ=America/New_York node tests/hub/test_apollo_hub_time_policy.cjs",
    "TZ=UTC node tests/hub/test_apollo_hub_time_policy.cjs",
    "TZ=Asia/Kathmandu node tests/hub/test_apollo_hub_time_policy.cjs",
    "TZ=Pacific/Chatham node tests/hub/test_apollo_hub_time_policy.cjs",
):
    assert needle in workflow, "B10 CI registration missing: "+needle
print("ApolloHub B10 pure time projection / reuse-existing-tick contracts passed")
