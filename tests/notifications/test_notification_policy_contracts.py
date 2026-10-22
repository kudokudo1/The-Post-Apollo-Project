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
require(SERVICE, "function shouldSuppress(sourceId, source, websiteHost)", "service must gate popup delivery")
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
    r"const suppressed = shouldSuppress\(entry\.sourceId, entry\.source, entry\.websiteHost\).*?if \(suppressed\).*?activeNotifications\.remove",
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
# A website gets a child DND/ZZ policy without changing the existing app key.
require(SERVICE, "function websiteKey(sourceId, source, websiteHost)", "child website policy keys")
require(SERVICE, 'return "website:" + encodeURIComponent(sourceKey(sourceId, source))', "child keys must nest beneath a stable parent")
require(SERVICE, 'const parent = policyFor(sourceKey(sourceId, source));', "parent policy inheritance")
require(SERVICE, 'const child = policyFor(childKey);', "exact website policy")
require(SERVICE, 'websiteKey(entry.sourceId, entry.source, entry.websiteHost) === key', "website DND must immediately suppress only matching active site popups")
require(HUB, '"websiteHost": String(entry.websiteHost || "")', "website hostname reaches card controls")
require(HUB, 'onNotificationIdChanged: {', "recycled card must reset per-event state")
require(HUB, 'targetWholeApp = false;', "recycled card resets SITE/APP scope")
require(HUB, 'emailDeckOpen = false;', "recycled card resets email action deck")
require(HUB, 'notificationEntry.targetWholeApp ? "APP"', "visible SITE/APP selector")
require(HUB, 'NotificationsService.toggleDnd(notificationEntry.targetKey,', "DND must follow selected scope")
require(HUB, 'NotificationsService.snoozeApp(notificationEntry.targetKey,', "ZZ must follow selected scope")
require(HUB, 'enabled: !notificationEntry.inheritedRule', "do not falsely allow disabling inherited app policy through site button")
require(HUB, 'root.requestClearAllForApp(notificationEntry.appKey, notificationEntry.source)', "CLEAR ALL must preserve legacy whole-app scope")

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

# Universal desktop intake must preserve standard sender category/urgency
# metadata rather than silently treating all external events as generic/normal.
CONVERTER = "services/notifications/NotificationsConverter.qml"
require(CONVERTER, "import Quickshell.Services.Notifications", "converter must access the supported urgency enum")
require(CONVERTER, 'const hints = notification.hints || {};', "converter must read client hints safely")
require(CONVERTER, 'const category = hints["category"];', "converter must read the standard category hint")
require(CONVERTER, 'NotificationUrgency.Critical', "critical urgency must survive conversion")
require(CONVERTER, 'NotificationUrgency.Low', "low urgency must survive conversion")
require(CONVERTER, '"category": root.categoryFor(notification)', "category must enter durable history")
require(CONVERTER, '"severity": root.severityFor(notification)', "severity must enter durable history")
require(CONVERTER, '"sourceId": String(notification.desktopEntry || "")', "original desktop entry must be kept for existing source policies")
require(CONVERTER, '"source": String(notification.appName || notification.desktopEntry || "UNKNOWN APP")', "app name must have a safe fallback")

# Explicit sender identity or standard type hints can classify external
# notifications. Unknown browser notifications remain Apps without guessing.
require(HUB, "function isCommunicationSource(source, sourceId)", "hub must recognize known communication senders")
for family in ("email", "im", "call", "presence"):
    require(HUB, f'categoryFamily === "{family}"', f"{family} hint family must reach Social")
for family in ("device", "network"):
    require(HUB, f'categoryFamily === "{family}"', f"{family} hint family must reach System")
require(HUB, 'let group = "apps";', "unrecognized external sources must stay in Apps")
require(HUB, 'root.isCommunicationSource(source, sourceId)', "source classification must use sender identity")
require(HUB, 'const tone = root.isWarning(category, severity) ? "warning"', "critical external notifications must also qualify for Warning")
classification = hub[hub.index("    function classificationFor("):hub.index("    function baseColorForTone(")]
assert 'categoryText === "important"' not in classification, "importance is not Apollo provenance"
assert 'categoryText === "reminder"' not in classification, "reminders are not Apollo provenance"
assert 'severityText === "important"' not in classification, "severity must not identify Apollo origin"

# Favorites are source-level UI state, not suppression policy and not
# notification history. They must survive reload and work without history.
require(SERVICE, "property ListModel favoriteSources: ListModel {}", "independent favorites model")
require(SERVICE, 'path: Quickshell.dataPath("notification-favorites.json")', "favorites must persist")
require(SERVICE, "function isFavorite(appKey)", "favorites must be queryable by source")
require(SERVICE, "function setFavorite(appKey, sourceId, source, enabled)", "Manager needs an explicit unstar operation")
require(SERVICE, "function toggleFavorite(appKey, sourceId, source)", "card stars must toggle backend source state")
require(SERVICE, "function loadFavorites()", "favorites must restore after reload")
require(SERVICE, "function favoriteDocument()", "favorites must save independent of message history")
favorite_document = read(SERVICE).split("    function favoriteDocument()")[1].split("    function scheduleFavoritesSave()")[0]
assert '"appKey"' in favorite_document and '"sourceId"' in favorite_document, "favorites must persist source identity"
favorite_ops = read(SERVICE).split("    function setFavorite(")[1].split("    function policyIndex(")[0]
assert "favoriteSources.append(" in favorite_ops, "starring must create a favorite"
assert "favoriteSources.remove(index)" in favorite_ops, "UNFAV must remove the favorite"
assert "scheduleFavoritesSave()" in favorite_ops, "favorite changes must persist"
favorites_logic = read(SERVICE).split("    function setFavorite(")[1].split("    function policyIndex(")[0]
assert "sourcePolicies" not in favorites_logic, "favoriting must never change DND policy"
assert "notifications.remove" not in favorites_logic, "unfavoriting must never delete history"

# COMBI is still the underlying 'all' filter; favorite is a separate
# overlapping source preference, not another exclusive origin category.
require(HUB, 'label: "COMBI"', "All must display as COMBI")
require(HUB, 'filterId: "all"', "COMBI must retain all-source semantics")
require(HUB, 'filterId: "favorites"', "hub must have a Favorites filter")
require(HUB, 'label: "FAVS"', "compact Favorite filter fits eight buttons")
require(HUB, 'root.activeFilter === "favorites"', "Favorites filter must be actionable")
require(HUB, "NotificationsService.isFavorite(root.appKeyFor(sourceId, source))", "Favorites view must filter by source identity")
require(HUB, "NotificationsService.toggleFavorite(notificationEntry.appKey, notificationEntry.sourceId, notificationEntry.source)", "card star must use persisted state")
require(HUB, "model: NotificationsService.favoriteSources", "Manager must display all favorites, including sources without retained history")
require(HUB, 'text: "FAVORITES  //  " + NotificationsService.favoriteSources.count', "Manager must display Favorites section")
require(HUB, 'label: "UNFAV"', "Manager must allow removing a favorite")
require(HUB, "NotificationsService.setFavorite(favoriteRule.appKey, favoriteRule.sourceId, favoriteRule.source, false)", "UNFAV must remove just favorite status")
require(HUB, 'text: "DO NOT DISTURB  //  " + managerDndPolicies.count', "DND manager must remain available")
require(HUB, 'label: "ALLOW"', "ALLOW policy control must remain intact")

# The user's existing keyboard-owner protocol must remain authoritative.
require(HUB, 'sequence: "Escape"', "Esc close shortcut")
require(HUB, 'context: Qt.WindowShortcut', "Esc must not be global")
require(HUB, 'enabled: root.menuOpen && root.keyboardActive', "Esc must not steal focus from other windows")
escape_logic = hub.split("    function handleEscape()")[1].split('    Shortcut {')[0]
assert 'pendingClearAllKey' in escape_logic, "Esc must check destructive confirmation"
assert 'cancelClearAll()' in escape_logic, "Esc must cancel confirmation"
assert 'close()' in escape_logic, "Esc must close the hub"
assert "WlrKeyboardFocus.OnDemand" in hub, "keep existing local window focus behavior"

# Chromium native notifications require the advertised actions capability.
# This must have real, live-only invocation, never just a capability flag.
require(SERVICE, "actionsSupported: true", "native action compatibility must be advertised")
require(SERVICE, "bodySupported: true", "standard body capability must remain advertised")
require(SERVICE, "function trackExternalNotification(eventId, nativeNotification, converted)", "native action lifetimes must be tracked")
require(SERVICE, "nativeNotification.closed.connect(function(reason)", "sender closure must dispose native action references")
require(SERVICE, "function releaseExternalNotification(eventId)", "native callback registry must be released")
require(SERVICE, "function externalActionsFor(eventId)", "popup must be able to query live action labels")
require(SERVICE, "function invokeExternalAction(eventId, actionIdentifier)", "actions must route by live event ID")
require(SERVICE, "action.invoke();", "originating app must receive action click")
require(SERVICE, "function expireExternalNotifications()", "orphaned native actions must expire")
require(SERVICE, "live.notification.expire();", "expired native notifications must be signalled to sender")
require(SERVICE, 'property var liveExternalNotifications: ({})', "native Qt objects must not enter persistent models")

native_history = read(SERVICE).split("    function historySnapshot(")[1].split("    function historyDocument()")[0]
assert "liveExternalNotifications" not in native_history, "live native objects must never enter persisted history"
assert '"notification": nativeNotification' not in native_history, "persist only serializable history metadata"

require("modules/Notifications.qml", "required property string notificationId", "popup must carry native event identity")
require("modules/Notifications.qml", "id: externalActionRow", "popup must render live-action buttons")
require("modules/Notifications.qml", "NotificationsService.externalActionsFor(notificationCard.notificationId)", "popup must resolve only live actions")
require("modules/Notifications.qml", "NotificationsService.invokeExternalAction(", "popup action click must reach service")
require("modules/Notifications.qml", "nativeActionButton.modelData.identifier", "actions must be matched by identifier, not index")
require(SERVICE, '"notificationId": String(eventId)', "popup delegate must receive a safe event ID role")

# Hospital's first producer uses existing Room outcome signals only.
# Status polls and read-only refreshes must not generate alert storms.
HOSPITAL = "widgets/HospitalW.qml"
ROOM = "services/hospital/HospitalRoomService.qml"
require(HOSPITAL, "import qs.services.notifications", "Hospital must reuse the shared notification service")
require(HOSPITAL, "function publishRoomOutcome(title, description, severity, eventType)", "single bounded Hospital producer")
require(HOSPITAL, '"source": "HOSPITAL"', "Hospital events must retain Apollo origin")
require(HOSPITAL, '"sourceId": "hospital"', "Hospital events must retain existing source policy identity")
require(HOSPITAL, '"category": "internal"', "Hospital events must appear in Apollo")
require(HOSPITAL, "NotificationsService.pushRich({", "Hospital events must enter shared policy and history pipeline")
require_regex(
    HOSPITAL,
    r"function publishRoomOutcome\(.*?if \(!room \|\| !patient\)\s*return;.*?NotificationsService\.pushRich",
    "Hospital must not create notifications without Room/Patient identity",
)
require_regex(
    HOSPITAL,
    r"function onIntegrationFailed\(reason, uncertain\).*?publishRoomOutcome\(.*?\"warning\"",
    "refused integration is a Warning event",
)
require_regex(
    HOSPITAL,
    r"function onIntegrated\(\).*?publishRoomOutcome\(.*?\"normal\"",
    "only the successful integrated signal sends a normal event",
)
require_regex(
    HOSPITAL,
    r"function onPostOpFinished\(\).*?patientService\.refresh\(\).*?VERIFY_FAILED.*?VERIFY_TIMEOUT.*?publishRoomOutcome\(.*?\"warning\"",
    "post-op failures notify without changing existing patient refresh",
)
require(ROOM, 'if (status !== "POST_OP_CLEAN")', "integration success must be post-op verified")
require_regex(
    ROOM,
    r"if \(status !== \"POST_OP_CLEAN\"\).*?integrated\(\);.*?postOpFinished\(\);",
    "verified integration must precede successful post-op finished",
)
hospital_policy = read(HOSPITAL).split("function publishRoomOutcome(")[1].split("    // Permanent-mapped", 1)[0]
assert "Quickshell.execDetached" not in hospital_policy, "notifications must never execute additional commands"
assert "raw" not in hospital_policy.lower(), "notification payload must not include raw command stderr"
assert "reason" not in hospital_policy.lower(), "notification payload must not leak operation errors"

# GitHub PR/merge queue fanout: only completed operations may notify.
# Polls, passive refreshes, previews, and ordinary metadata edits are silent.
GIT_VIEW = "widgets/GitW.qml"
require(GIT_VIEW, "import qs.services.notifications", "Git UI must reuse existing notification service")
require(GIT_VIEW, "function publishGitHubOutcome(repository, number, title, message, severity, eventType)", "bounded GitHub producer")
require(GIT_VIEW, '"source": "GITHUB"', "GitHub event source must be stable")
require(GIT_VIEW, '"sourceId": "github"', "GitHub source policies must remain stable")
require(GIT_VIEW, '"category": "internal"', "GitHub events must classify as Apollo")
require(GIT_VIEW, "NotificationsService.pushRich({", "GitHub notifications must use shared policy and history path")
require(GIT_VIEW, "function reportPullRequestMutation(succeeded, verified, operation, evidence)", "PR mutation handler")
require(GIT_VIEW, "function reportMergeQueueMutation(succeeded, verified, operation, evidence)", "merge queue handler")
require(GIT_VIEW, '["create", "close", "reopen"].indexOf(action) < 0', "ordinary PR edits must not notify")
require(GIT_VIEW, 'const isMerge = action.indexOf("merge-") === 0;', "all PR merge methods must be covered")
require(GIT_VIEW, "state === expectedState", "PR notification must verify actual requested state")
require(GIT_VIEW, "succeeded && verified", "success must require mutation plus verification")
require(GIT_VIEW, "Boolean(result.queued) === (action === \"enqueue\")", "queue result must match requested action")
require(GIT_VIEW, '"warning", "pr-" + action + "-attention"', "unverified PR mutations must warn, not claim success")
require(GIT_VIEW, '"warning", "queue-" + action + "-attention"', "unverified queue mutations must warn")
require_regex(
    GIT_VIEW,
    r"target: githubPullRequestLifecycleService\s+function onMutationFinished\(.*?root\.reportPullRequestMutation\(",
    "PR notifications must observe mutation completion, not polling",
)
require_regex(
    GIT_VIEW,
    r"target: githubMergeQueueLifecycleService\s+function onMutationFinished\(.*?root\.reportMergeQueueMutation\(",
    "queue notifications must observe mutation completion, not previews",
)
publisher = read(GIT_VIEW).split("function publishGitHubOutcome(")[1].split("    // Permanent-mapped overlay:")[0]
assert "Quickshell.execDetached" not in publisher, "notifications must not execute Git/GitHub mutations"
assert "lastError" not in publisher and "mutationStderrText" not in publisher and "mutationStdoutText" not in publisher, "notifications must not copy raw gh error details"

print("Notification policy contracts: PASS")
