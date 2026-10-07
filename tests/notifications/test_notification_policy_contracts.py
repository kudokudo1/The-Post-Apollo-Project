#!/usr/bin/env python3
"""Static contracts for notification snooze / DND policy and manager UI."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(path: str, needle: str, message: str) -> None:
    text = read(path)
    assert needle in text, f"{message}: missing {needle!r} in {path}"


def require_regex(path: str, pattern: str, message: str) -> None:
    text = read(path)
    assert re.search(pattern, text, re.S), f"{message}: {path}"


SERVICE = "services/notifications/NotificationsService.qml"
HUB = "widgets/notifications/NotificationsHubW.qml"

require(SERVICE, "property ListModel sourcePolicies: ListModel {}", "policy model must be persistent service state")
require(SERVICE, "property int defaultSnoozeDurationMs: 24 * 60 * 60 * 1000", "default snooze must be one day")
require(SERVICE, 'path: Quickshell.dataPath("notification-policies.json")', "notification policies must persist across reloads")
require(SERVICE, "function shouldSuppress(sourceId, source)", "service must gate popup delivery")
require(SERVICE, "function snoozeApp(appKey, sourceId, source)", "service must implement timed snooze")
require(SERVICE, "function setDnd(appKey, sourceId, source, enabled)", "service must implement DND")
require_regex(
    SERVICE,
    r"function setDnd\(.*?setProperty\(index, \"snoozeUntil\", 0\).*?suppressActiveForKey",
    "enabling DND must clear timed snooze and suppress current popups",
)
require_regex(
    SERVICE,
    r"function snoozeApp\(.*?setProperty\(index, \"dnd\", false\).*?setProperty\(index, \"snoozeUntil\", until\).*?suppressActiveForKey",
    "snooze must replace DND with a timed deadline and suppress current popups",
)
require_regex(
    SERVICE,
    r"const suppressed = shouldSuppress\(entry\.sourceId, entry\.source\).*?if \(suppressed\).*?activeNotifications\.remove",
    "suppressed notifications must stay out of the popup model",
)

require(HUB, 'filterId: "manager"', "hub must expose a MANAGER mode")
require(HUB, 'label: "MANAGER"', "manager control must be visibly labeled")
require(HUB, 'text: "DO NOT DISTURB  //  " + managerDndPolicies.count', "manager must show DND sources")
require(HUB, 'label: "ALLOW"', "manager must let the operator clear DND")
for preset in ("1H", "6H", "12H", "1D", "3D", "7D"):
    require(HUB, f'label: "{preset}"', f"manager must expose {preset} snooze preset")
require(HUB, "NotificationsService.snoozeApp(", "ZZ button must call backend snooze policy")
require(HUB, "NotificationsService.toggleDnd(", "DND button must call backend DND policy")

hub = read(HUB)
assert 'toggleAppFlag(notificationEntry.appKey, "snoozed")' not in hub, "ZZ must not be frontend-only state"
assert 'toggleAppFlag(notificationEntry.appKey, "dnd")' not in hub, "DND must not be frontend-only state"

print("Notification policy contracts: PASS")
