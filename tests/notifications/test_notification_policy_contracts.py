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
require(SERVICE, "function clearNotificationsForSource(appKey)", "service must support source-wide history clearing")
require_regex(
    SERVICE,
    r"function clearNotificationsForSource\(appKey\).*?notifications\.remove\(i\).*?activeNotifications\.remove\(i\).*?scheduleHistorySave",
    "clear-all must remove source entries from history and active popups, then persist",
)
require(HUB, 'label: "CLEAR ALL"', "notification cards must expose a clear-all control")
require(HUB, 'width: 60', "clear-all control should use the approved compact width")
require_regex(
    HUB,
    r'label: "CLEAR ALL".*?danger: true.*?requestClearAllForApp',
    "clear-all control must be red and request confirmation rather than deleting immediately",
)
require(HUB, 'text: "CLEAR ALL NOTIFICATIONS?"', "clear-all must show a confirmation window")
require(HUB, 'label: "NO"', "confirmation must expose NO")
require(HUB, 'label: "YES"', "confirmation must expose YES")
require_regex(
    HUB,
    r"function confirmClearAll\(\).*?NotificationsService\.clearNotificationsForSource\(root\.pendingClearAllKey\)",
    "YES must execute source-wide clearing",
)

hub = read(HUB)
assert 'toggleAppFlag(notificationEntry.appKey, "snoozed")' not in hub, "ZZ must not be frontend-only state"
assert 'toggleAppFlag(notificationEntry.appKey, "dnd")' not in hub, "DND must not be frontend-only state"

# Source group and severity must remain independent: Apollo warnings appear
# under both Apollo (source) and Warning (severity), without rewriting history.
require(HUB, "function isWarning(category, severity)", "warning facet must be independent")
require(HUB, 'root.activeFilter === "warning"', "warning must be an overlapping filter")
require(HUB, "root.isWarning(category, severity)", "warning matching must use severity")
require(HUB, 'group = "apollo"', "internal sources must keep the Apollo group")
require_regex(
    HUB,
    r'function classificationFor\(.*?const tone = root\.isWarning\(category, severity\).*?return \{ group: group, tone: tone \}',
    "warning must change presentation tone, not the source group",
)

# Durable history remains append/update-by-ID, but repeated startup events
# must not masquerade as updates to the same historical occurrence.
require(SERVICE, "const historyIndex = indexOfNotification(notifications, entry.id);", "stable IDs still update")
require(HUB, "rows.sort(function(a, b)", "history presentation must sort newest first")
require(HUB, "return (bTime - aTime) || (b.ordinal - a.ordinal);", "recent update must appear first")
require(HUB, "filteredNotifications.append(rows[j].data);", "sorted view must not reorder stored history")
popup = read("modules/Notifications.qml")
assert '"id": "apollo-structure-test"' not in popup, "each startup test requires a distinct occurrence ID"

print("Notification policy contracts: PASS")
