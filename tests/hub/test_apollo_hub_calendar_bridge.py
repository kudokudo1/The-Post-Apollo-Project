#!/usr/bin/env python3
"""B9 local calendar: one existing clock, no event-provider claims or IO."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
bridge=(ROOT/"services/hub/ApolloHubLiveBridge.qml").read_text()
policy=(ROOT/"services/hub/ApolloHubCalendarPolicy.js").read_text()
tile=(ROOT/"widgets/hub/ApolloHubTile.qml").read_text()
layout=(ROOT/"services/hub/ApolloHubLayout.js").read_text()
shell=(ROOT/"shell.qml").read_text()
workflow=(ROOT/".github/workflows/apollo-hub-calendar.yml").read_text()

for needle in (
    'import "ApolloHubCalendarPolicy.js" as CalendarPolicy',
    "property double observationNowMs: Date.now()",
    "property int calendarMonthOffset: 0",
    "property int calendarWeekStartsOn: 0",
    "readonly property var calendarSnapshot: CalendarPolicy.snapshot(",
    "observationNowMs, calendarMonthOffset, calendarWeekStartsOn",
):
    assert needle in bridge, "Calendar bridge seam missing: "+needle
assert bridge.count("calendarSnapshot: CalendarPolicy.snapshot(")==1
assert bridge.count("property double observationNowMs: Date.now()")==1
assert "SystemClock {" not in bridge
assert 'module: "calendar"' in layout
assert 'tile.moduleId === "calendar"' in tile
assert "property date now: new Date()" in tile
assert shell.count("ApolloHubLiveBridge {")==1

for needle in (
    ".pragma library", "function snapshot(", "function key(",
    "MIN_YEAR = 1900", "MAX_YEAR = 2100", "MAX_MONTH_OFFSET = 120",
    "DAY_MS = 86400000", "new Date(now)", "getFullYear()",
    "getMonth()", "getDate()", "Date.UTC(", "getUTCDay()",
    '"not-connected"', "eventCount:-1",
    "weekdayLabels:", "daysInMonth:", "cells:cells",
    "isToday:", "inMonth:", "row:", "column:",
):
    assert needle in policy, "Missing calendar policy contract: "+needle

for forbidden in (
    "Process {", "FileView {", "SystemClock {", "Timer {",
    "XmlHttpRequest", "fetch(", ".execute(", "Date.prototype",
    "setFullYear(", "setTime(", "EventStore", "GoogleCalendar",
    "Quickshell.execDetached(", "http://", "https://",
):
    assert forbidden not in policy, "Forbidden backend effect: "+forbidden

for needle in (
    '"services/hub/ApolloHubCalendarPolicy.js"',
    '"services/hub/ApolloHubLiveBridge.qml"',
    '"tests/hub/test_apollo_hub_calendar_policy.cjs"',
    '"tests/hub/test_apollo_hub_calendar_bridge.py"',
    "node tests/hub/test_apollo_hub_calendar_policy.cjs",
    "python3 tests/hub/test_apollo_hub_calendar_bridge.py",
):
    assert needle in workflow, "Missing B9 workflow contract: "+needle
print("ApolloHub B9 shared clock, passive calendar and no-events contracts passed")
