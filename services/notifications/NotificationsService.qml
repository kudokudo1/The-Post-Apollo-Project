pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import "." as NotificationsBackend
import "BrowserSiteIdentity.js" as BrowserSiteIdentity
import "ApolloNotificationRoute.js" as ApolloNotificationRoute
import "EmailNotificationActions.js" as EmailNotificationActions
import "mail/ProtonNativeDeliveryAudit.js" as ProtonNativeDeliveryAudit

Singleton {
    id: root

    property ListModel notifications: ListModel {}
    property ListModel activeNotifications: ListModel {}
    // Delivered by shell.qml to the single, already-mounted widget instance.
    // This signal carries allowlisted view coordinates, never code/commands.
    signal apolloNavigationRequested(var destination)
    // Native notification/action objects must NEVER enter a ListModel or the
    // persistent JSON history. They exist only while the sender is live.
    property var liveExternalNotifications: ({})
    property int externalActionsRevision: 0
    // Optional, metadata-presence-only feasibility check. Off by default;
    // never serialized, never an authenticated mailbox binding.
    readonly property bool protonNativeAuditEnabled:
        String(Quickshell.env("POST_APOLLO_PROTON_DELIVERY_AUDIT") || "") === "1"
    property int protonNativeAuditSamples: 0
    // One-shot startup history copy measurement; off by default and never
    // reports stored message content, IDs, source names, or raw file text.
    readonly property bool arrayCopyProbeEnabled:
        String(Quickshell.env("POST_APOLLO_ARRAY_COPY_PROBE") || "").trim() === "1"
    property double protonNativeAuditLastMs: 0
    property ListModel sourcePolicies: ListModel {}
    // Independent from DND/snooze: starring a source never suppresses it.
    property ListModel favoriteSources: ListModel {}

    property int normalTimeoutMs: 5000
    property int extendedTimeoutMs: 10000

    property int notificationSerial: 0

    property int historyVersion: 1
    property bool historyReady: false
    property bool historyEnabled: true
    property string historyStatus: "loading"

    // Bound persistent history so rendering/search/filter cost cannot
    // grow forever over the lifetime of the desktop session.
    property int maxHistoryEntries: 300
    property int notificationsRevision: 0

    // Persistent source-wide notification policy.
    property int policyVersion: 1
    property bool policyReady: false
    property string policyStatus: "loading"
    property int policyRevision: 0
    property int defaultSnoozeDurationMs: 24 * 60 * 60 * 1000

    // Control Bay viewport preference, independent of notification history,
    // Favorites and DND/ZZ policy files. Locked means no slider edits;
    // it never disables scrolling itself.
    property real scrollSpeedMultiplier: 1.0
    property bool scrollSpeedLocked: false
    property bool scrollSettingsReady: false

    property int favoriteVersion: 1
    property bool favoritesReady: false
    property string favoritesStatus: "loading"
    property int favoritesRevision: 0

    function markNotificationsChanged() {
        notificationsRevision += 1;
    }

    function sourceKey(sourceId, source) {
        const sourceIdText = String(sourceId || "").trim().toLowerCase();
        const sourceText = String(source || "").trim().toLowerCase();

        if (sourceIdText !== "")
            return sourceIdText;

        if (sourceText !== "")
            return sourceText;

        return "unknown";
    }

    // Optional child of the existing app/source policy key. Stable hostname
    // identity comes from the browser origin metadata, never message mentions.
    // Encode the parent so arbitrary app IDs cannot collide with child keys.
    function websiteKey(sourceId, source, websiteHost) {
        const host = BrowserSiteIdentity.hostnameFor(websiteHost);
        if (host === "")
            return "";
        const site = host === "youtu.be" || host === "youtube.com"
            || host.endsWith(".youtube.com") ? "youtube.com"
            : host.startsWith("www.") ? host.substring(4) : host;
        return "website:" + encodeURIComponent(sourceKey(sourceId, source)) + "::" + site;
    }

    // Favorites are source-wide, just like the card star, but are persisted
    // separately from suppression policies and notification history.
    function favoriteIndex(appKey) {
        const key = String(appKey || "").trim().toLowerCase();
        if (key === "")
            return -1;
        for (let i = 0; i < favoriteSources.count; i++) {
            if (String(favoriteSources.get(i).appKey || "") === key)
                return i;
        }
        return -1;
    }

    function isFavorite(appKey) {
        return favoriteIndex(appKey) !== -1;
    }

    function setFavorite(appKey, sourceId, source, enabled) {
        const key = String(appKey || sourceKey(sourceId, source)).trim().toLowerCase();
        if (key === "")
            return;
        const index = favoriteIndex(key);
        if (enabled === true) {
            if (index === -1) {
                favoriteSources.append({
                    "appKey": key,
                    "source": String(source || ""),
                    "sourceId": String(sourceId || "")
                });
            } else {
                // Preserve useful names for the Manager even when a newer
                // notification updates an app's displayed identity.
                const existing = favoriteSources.get(index);
                const name = String(source || "");
                const desktop = String(sourceId || "");
                if (name === "" && desktop === "")
                    return;
                if (name !== "" && name !== String(existing.source || ""))
                    favoriteSources.setProperty(index, "source", name);
                if (desktop !== "" && desktop !== String(existing.sourceId || ""))
                    favoriteSources.setProperty(index, "sourceId", desktop);
                // No model change needed if identity is unchanged.
            }
        } else {
            if (index === -1)
                return;
            favoriteSources.remove(index);
        }
        favoritesRevision += 1;
        scheduleFavoritesSave();
    }

    function toggleFavorite(appKey, sourceId, source) {
        setFavorite(appKey, sourceId, source, !isFavorite(appKey));
    }

    function policyIndex(appKey) {
        const key = String(appKey || "").trim().toLowerCase();

        for (let i = 0; i < sourcePolicies.count; i++) {
            if (String(sourcePolicies.get(i).appKey || "") === key)
                return i;
        }

        return -1;
    }

    function policyFor(appKey) {
        const index = policyIndex(appKey);

        if (index === -1) {
            return {
                "appKey": String(appKey || ""),
                "source": "",
                "sourceId": "",
                "dnd": false,
                "snoozeUntil": 0
            };
        }

        const policy = sourcePolicies.get(index);

        return {
            "appKey": String(policy.appKey || ""),
            "source": String(policy.source || ""),
            "sourceId": String(policy.sourceId || ""),
            "dnd": policy.dnd === true,
            "snoozeUntil": Number(policy.snoozeUntil || 0)
        };
    }

    function isDnd(appKey) {
        return policyFor(appKey).dnd === true;
    }

    function isSnoozed(appKey) {
        return Number(policyFor(appKey).snoozeUntil || 0) > Date.now();
    }

    function shouldSuppress(sourceId, source, websiteHost) {
        const parent = policyFor(sourceKey(sourceId, source));
        if (parent.dnd === true || Number(parent.snoozeUntil || 0) > Date.now())
            return true; // Existing app-wide policies always affect child sites.
        const childKey = websiteKey(sourceId, source, websiteHost);
        if (childKey === "")
            return false;
        const child = policyFor(childKey);
        return child.dnd === true || Number(child.snoozeUntil || 0) > Date.now();
    }

    function ensurePolicy(appKey, sourceId, source) {
        const key = String(appKey || sourceKey(sourceId, source)).trim().toLowerCase();
        let index = policyIndex(key);

        if (index === -1) {
            sourcePolicies.append({
                "appKey": key,
                "source": String(source || ""),
                "sourceId": String(sourceId || ""),
                "dnd": false,
                "snoozeUntil": 0
            });

            return sourcePolicies.count - 1;
        }

        if (String(source || "") !== "")
            sourcePolicies.setProperty(index, "source", String(source));

        if (String(sourceId || "") !== "")
            sourcePolicies.setProperty(index, "sourceId", String(sourceId));

        return index;
    }

    function markPoliciesChanged() {
        policyRevision += 1;
        schedulePolicySave();
    }

    function suppressActiveForKey(appKey) {
        const key = String(appKey || "").trim().toLowerCase();

        for (let i = activeNotifications.count - 1; i >= 0; i--) {
            const entry = activeNotifications.get(i);

            if (sourceKey(entry.sourceId, entry.source) === key
                    || websiteKey(entry.sourceId, entry.source, entry.websiteHost) === key)
                activeNotifications.remove(i);
        }
    }

    function compactPolicy(index) {
        if (index < 0 || index >= sourcePolicies.count)
            return;

        const policy = sourcePolicies.get(index);

        if (policy.dnd !== true && Number(policy.snoozeUntil || 0) <= Date.now())
            sourcePolicies.remove(index);
    }

    function setDnd(appKey, sourceId, source, enabled) {
        const index = ensurePolicy(appKey, sourceId, source);

        sourcePolicies.setProperty(index, "dnd", enabled === true);

        if (enabled === true) {
            // DND is indefinite and supersedes a timed snooze.
            sourcePolicies.setProperty(index, "snoozeUntil", 0);
            suppressActiveForKey(String(sourcePolicies.get(index).appKey || ""));
        } else {
            compactPolicy(index);
        }

        markPoliciesChanged();
    }

    function toggleDnd(appKey, sourceId, source) {
        setDnd(appKey, sourceId, source, !isDnd(appKey));
    }

    function snoozeApp(appKey, sourceId, source) {
        const index = ensurePolicy(appKey, sourceId, source);
        const until = Date.now() + Math.max(60000, Number(defaultSnoozeDurationMs || 0));

        // Snooze is timed and replaces indefinite DND for this source.
        sourcePolicies.setProperty(index, "dnd", false);
        sourcePolicies.setProperty(index, "snoozeUntil", until);

        suppressActiveForKey(String(sourcePolicies.get(index).appKey || ""));
        markPoliciesChanged();
    }

    function clearSnooze(appKey) {
        const index = policyIndex(appKey);

        if (index === -1)
            return;

        sourcePolicies.setProperty(index, "snoozeUntil", 0);
        compactPolicy(index);
        markPoliciesChanged();
    }

    function setDefaultSnoozeDurationMs(durationMs) {
        const minimum = 60 * 1000;
        const maximum = 30 * 24 * 60 * 60 * 1000;
        const next = Math.max(minimum, Math.min(maximum, Number(durationMs || 0)));

        if (next === defaultSnoozeDurationMs)
            return;

        defaultSnoozeDurationMs = next;
        markPoliciesChanged();
    }

    function expireSnoozes() {
        const now = Date.now();
        let changed = false;

        for (let i = sourcePolicies.count - 1; i >= 0; i--) {
            const policy = sourcePolicies.get(i);
            const until = Number(policy.snoozeUntil || 0);

            if (until > 0 && until <= now) {
                sourcePolicies.setProperty(i, "snoozeUntil", 0);

                if (policy.dnd !== true)
                    sourcePolicies.remove(i);

                changed = true;
            }
        }

        if (changed)
            markPoliciesChanged();
    }

    // Opt-in browser notification provenance audit, NOT an action gateway.
    // The helper yields a fixed-format line of booleans and capped counts.
    // No titles, bodies, IDs, hints, URLs or account data ever reach logs.
    function auditProtonNativeDelivery(notification) {
        if (!protonNativeAuditEnabled || protonNativeAuditSamples >= 12)
            return;
        const nowMs = Date.now();
        if (nowMs - protonNativeAuditLastMs < 1000)
            return;
        const observed = ProtonNativeDeliveryAudit.collect(notification);
        const line = ProtonNativeDeliveryAudit.safeLine(observed);
        if (line === "")
            return;
        protonNativeAuditSamples += 1;
        protonNativeAuditLastMs = nowMs;
        console.info(line);
    }

    // ===== EXTERNAL NOTIFICATIONS ===============================

    NotificationServer {
        id: notificationServer

        keepOnReload: false
        // Chromium requires the standard body + actions capabilities to
        // select the desktop-native notifications backend.
        bodySupported: true
        actionsSupported: true
        // Post-Apollo stores notification history even after popups expire,
        // and its popup supports images supplied by native applications.
        persistenceSupported: true
        imageSupported: true
        // We do NOT advertise markup support; client text must remain text.
        bodyMarkupSupported: false

        onNotification: function (notification) {
            root.auditProtonNativeDelivery(notification);
            notification.tracked = true;

            // Each native delivery gets an independent history ID. The live
            // QObject remains exclusively in this service's transient map.
            const eventId = root.makeNotificationId();
            const converted = NotificationsBackend.NotificationsConverter.convert(notification);
            converted.id = eventId;
            root.pushConverted(converted);
            root.trackExternalNotification(eventId, notification, converted);
        }
    }

    // ===== NATIVE ACTIONS =======================================
    // Quickshell's NotificationAction.invoke() signals the originating
    // application. Never serialize a QML/QObject callback into history.
    // A saved or expired event MUST NOT be able to trigger an action.

    function trackExternalNotification(eventId, nativeNotification, converted) {
        const id = String(eventId || "");
        if (id === "")
            return;

        const next = Object.assign({}, liveExternalNotifications);
        next[id] = {
            "notification": nativeNotification,
            "expiresAt": Date.now() + timeoutFor(normalize(converted))
        };
        liveExternalNotifications = next;
        externalActionsRevision += 1;

        // Release native objects before Qt destroys them. No destroyed
        // QObject reference is ever retained for saved history.
        nativeNotification.closed.connect(function(reason) {
            root.releaseExternalNotification(id);
        });
    }

    function releaseExternalNotification(eventId) {
        const id = String(eventId || "");
        if (!Object.prototype.hasOwnProperty.call(liveExternalNotifications, id))
            return;
        const next = Object.assign({}, liveExternalNotifications);
        delete next[id];
        liveExternalNotifications = next;
        externalActionsRevision += 1;

        // A sender-closed event should no longer have an active popup.
        const activeIndex = indexOfNotification(activeNotifications, id);
        if (activeIndex !== -1)
            activeNotifications.remove(activeIndex);
        // Do not remove the retained history item.
    }

    function externalActionsFor(eventId) {
        const live = liveExternalNotifications[String(eventId || "")];
        if (!live || live.expiresAt <= Date.now())
            return [];
        const nativeActions = live.notification.actions || [];
        const result = [];
        // Bound the popup control surface; no action ever fires by index.
        for (let i = 0; i < nativeActions.length && result.length < 3; i++) {
            const action = nativeActions[i];
            if (!action)
                continue;
            const identifier = String(action.identifier || "");
            if (identifier === "")
                continue;
            result.push({
                "identifier": identifier,
                "label": String(action.text || (identifier === "default" ? "OPEN" : "ACTION"))
            });
        }
        return result;
    }

    function invokeExternalAction(eventId, actionIdentifier) {
        const id = String(eventId || "");
        const identifier = String(actionIdentifier || "");
        const live = liveExternalNotifications[id];
        if (!live || live.expiresAt <= Date.now() || identifier === "")
            return false;

        const nativeActions = live.notification.actions || [];
        for (let i = 0; i < nativeActions.length; i++) {
            const action = nativeActions[i];
            if (action && String(action.identifier || "") === identifier) {
                action.invoke();
                // Quickshell closes nonresident native notifications itself.
                return true;
            }
        }
        return false;
    }

    // Sender-advertised EMAIL actions only. The desktop notification does not
    // carry an authenticated mailbox message ID, so a saved notification or
    // an expired native callback MUST NOT mutate mail. A successful return
    // means only "dispatched to the original sender", not mailbox confirmed.
    function emailActionsFor(eventId) {
        const id = String(eventId || "");
        const index = indexOfNotification(notifications, id);
        if (index < 0)
            return [];
        const live = liveExternalNotifications[id];
        if (!live || Number(live.expiresAt || 0) <= Date.now())
            return [];
        return EmailNotificationActions.availableActions(
            notifications.get(index), live.notification.actions || []);
    }

    function hasEmailAction(eventId, operation) {
        const requested = String(operation || "");
        const actions = emailActionsFor(eventId);
        for (let i = 0; i < actions.length; i++) {
            if (actions[i].kind === requested)
                return true;
        }
        return false;
    }

    function dispatchEmailAction(eventId, operation) {
        const requested = String(operation || "");
        const actions = emailActionsFor(eventId);
        for (let i = 0; i < actions.length; i++) {
            if (actions[i].kind === requested)
                return invokeExternalAction(eventId, actions[i].identifier);
        }
        return false;
    }

    // Native desktop clients use the "default" action for opening a
    // notification's destination (e.g. Chromium's original web push click).
    // This is only available while the native QObject is tracked and live.
    // It must NEVER be reconstructed from saved history or inferred from text.
    function hasExternalDefaultAction(eventId) {
        const live = liveExternalNotifications[String(eventId || "")];
        if (!live || live.expiresAt <= Date.now())
            return false;
        const actions = live.notification.actions || [];
        for (let i = 0; i < actions.length; i++) {
            if (actions[i] && String(actions[i].identifier || "") === "default")
                return true;
        }
        return false;
    }

    function invokeExternalDefaultAction(eventId) {
        if (!hasExternalDefaultAction(eventId))
            return false;
        return invokeExternalAction(eventId, "default");
    }

    function expireExternalNotifications() {
        const now = Date.now();
        const ids = Object.keys(liveExternalNotifications);
        for (let i = 0; i < ids.length; i++) {
            const id = ids[i];
            const live = liveExternalNotifications[id];
            if (!live || Number(live.expiresAt || 0) > now)
                continue;
            // Forget first so a synchronous Qt close signal is harmless.
            releaseExternalNotification(id);
            live.notification.expire();
        }
    }

    // ===== NORMALIZE ============================================

    function makeNotificationId() {
        notificationSerial += 1;

        return "apollo-" + Date.now() + "-" + notificationSerial;
    }

    function normalize(notification) {
        const now = Date.now();

        const createdAt = notification.createdAt !== undefined ? Number(notification.createdAt) : now;
        const eventId = notification.id || makeNotificationId();

        return {
            // Identity
            "id": eventId,
            // Alias for Repeater delegates where QML reserves the id keyword.
            "notificationId": String(eventId),

            // Source
            "source": notification.source || "",
            "sourceId": notification.sourceId || "",
            "website": notification.website || "",
            "websiteHost": notification.websiteHost || "",
            "websiteIcon": notification.websiteIcon || "",

            // Content
            "title": notification.title || "",
            "message": notification.message || "",
            "originalTitle": notification.originalTitle !== undefined ? notification.originalTitle : notification.title || "",
            "originalMessage": notification.originalMessage !== undefined ? notification.originalMessage : notification.message || "",

            // Media
            "appIcon": notification.appIcon || "",
            "image": notification.image || "",

            // Classification
            "category": notification.category || "generic",
            "severity": notification.severity || "normal",
            "tags": normalizeTags(notification.tags),

            // Lifecycle
            "state": notification.state || "active",
            "createdAt": createdAt,
            "updatedAt": notification.updatedAt !== undefined ? Number(notification.updatedAt) : createdAt,
            "resolvedAt": notification.resolvedAt !== undefined ? Number(notification.resolvedAt) : 0,
            "dismissedAt": notification.dismissedAt !== undefined ? Number(notification.dismissedAt) : 0,

            // Rich / live presentation
            "presentation": notification.presentation || "auto",
            "live": notification.live === true,
            "liveSource": notification.liveSource || "",
            "liveKey": notification.liveKey || "",

            // Searchable event snapshot
            "metrics": notification.metrics || {},

            // Actions / subsystem information
            "context": notification.context || {},
            "actions": notification.actions || [],

            // Runtime-only popup lifetime
            "expiresAt": notification.expiresAt !== undefined ? Number(notification.expiresAt) : 0
        };
    }

    function normalizeTags(tags) {
        if (!tags)
            return [];

        const result = [];

        for (let i = 0; i < tags.length; i++) {
            const tag = tags[i];

            if (typeof tag === "string")
                result.push({
                    "name": tag
                });
            else if (tag && tag.name !== undefined)
                result.push({
                    "name": String(tag.name)
                });
        }

        return result;
    }

    function tagsToStrings(tags) {
        const result = [];

        if (!tags)
            return result;

        // Normal JavaScript array
        if (Array.isArray(tags)) {
            for (let i = 0; i < tags.length; i++) {
                const tag = tags[i];

                if (typeof tag === "string")
                    result.push(tag);
                else if (tag && tag.name !== undefined)
                    result.push(String(tag.name));
            }

            return result;
        }

        // QML ListModel-style nested list
        if (typeof tags.count === "number" && typeof tags.get === "function") {
            for (let i = 0; i < tags.count; i++) {
                const tag = tags.get(i);

                if (tag && tag.name !== undefined)
                    result.push(String(tag.name));
            }
        }

        return result;
    }

    // ===== LIFETIME =============================================

    function timeoutFor(notification) {
        const severity = String(notification.severity || "normal").toLowerCase();

        const tags = notification.tags || [];

        const tagNames = tagsToStrings(tags);

        const isFavorite = tagNames.indexOf("favorite") !== -1;

        if (isFavorite || severity === "warning" || severity === "critical")
            return extendedTimeoutMs;

        return normalTimeoutMs;
    }

    function pruneHistory() {
        while (notifications.count > maxHistoryEntries)
            notifications.remove(0);
    }

    function appendNotification(notification) {
        const entry = normalize(notification);

        const historyIndex = indexOfNotification(notifications, entry.id);

        const activeIndex = indexOfNotification(activeNotifications, entry.id);

        // Same ID = same event.
        // Update it instead of creating another history entry.
        if (historyIndex !== -1) {
            const existing = notifications.get(historyIndex);

            entry.createdAt = Number(existing.createdAt || entry.createdAt);

            entry.updatedAt = Date.now();
        }

        entry.expiresAt = Date.now() + timeoutFor(entry);

        if (historyIndex === -1) {
            notifications.append(entry);
        } else {
            replaceModelEntry(notifications, historyIndex, entry);
        }

        pruneHistory();

        const suppressed = shouldSuppress(entry.sourceId, entry.source, entry.websiteHost);

        if (suppressed) {
            if (activeIndex !== -1)
                activeNotifications.remove(activeIndex);
        } else if (activeIndex === -1) {
            activeNotifications.append(entry);
        } else {
            replaceModelEntry(activeNotifications, activeIndex, entry);
        }

        markNotificationsChanged();
        scheduleHistorySave();
    }

    // ===== UPDATE ===============================================

    function replaceModelEntry(model, index, entry) {
        for (const key in entry)
            model.setProperty(index, key, entry[key]);
    }

    function indexOfNotification(model, notificationId) {
        for (let i = 0; i < model.count; i++) {
            if (model.get(i).id === notificationId)
                return i;
        }

        return -1;
    }

    function updateModelNotification(model, notificationId, changes) {
        const index = indexOfNotification(model, notificationId);

        if (index === -1)
            return false;

        for (const key in changes)
            model.setProperty(index, key, changes[key]);

        model.setProperty(index, "updatedAt", Date.now());

        return true;
    }

    function updateNotification(notificationId, changes) {
        const historyUpdated = updateModelNotification(notifications, notificationId, changes);

        const activeUpdated = updateModelNotification(activeNotifications, notificationId, changes);

        if (historyUpdated) {
            markNotificationsChanged();
            scheduleHistorySave();
        }

        return historyUpdated || activeUpdated;
    }

    function clearNotificationsForSource(appKey) {
        const key = String(appKey || "").trim().toLowerCase();

        if (key === "")
            return 0;

        let removed = 0;

        for (let i = notifications.count - 1; i >= 0; i--) {
            const entry = notifications.get(i);

            if (sourceKey(entry.sourceId, entry.source) === key) {
                notifications.remove(i);
                removed += 1;
            }
        }

        for (let i = activeNotifications.count - 1; i >= 0; i--) {
            const entry = activeNotifications.get(i);

            if (sourceKey(entry.sourceId, entry.source) === key)
                activeNotifications.remove(i);
        }

        if (removed > 0) {
            markNotificationsChanged();
            scheduleHistorySave();
        }

        return removed;
    }

    // ===== HISTORY SERIALIZE ====================================

    function toPlainValue(value) {
        if (value === undefined || value === null)
            return null;

        const valueType = typeof value;

        if (valueType === "string" || valueType === "number" || valueType === "boolean")
            return value;

        if (Array.isArray(value)) {
            const array = [];

            for (let i = 0; i < value.length; i++)
                array.push(toPlainValue(value[i]));

            return array;
        }

        // Nested ListModel / QML list
        if (valueType === "object" && typeof value.count === "number" && typeof value.get === "function") {
            const array = [];

            for (let i = 0; i < value.count; i++)
                array.push(toPlainValue(value.get(i)));

            return array;
        }

        if (valueType === "object") {
            const object = {};

            for (const key in value) {
                if (typeof value[key] !== "function")
                    object[key] = toPlainValue(value[key]);
            }

            return object;
        }

        return String(value);
    }

    function historySnapshot(notification) {
        return {
            // Identity
            "id": String(notification.id || ""),

            // Source
            "source": String(notification.source || ""),
            "sourceId": String(notification.sourceId || ""),
            "website": String(notification.website || ""),
            "websiteHost": String(notification.websiteHost || ""),
            "websiteIcon": String(notification.websiteIcon || ""),

            // Content
            "title": String(notification.title || ""),
            "message": String(notification.message || ""),
            "originalTitle": String(notification.originalTitle || ""),
            "originalMessage": String(notification.originalMessage || ""),

            // Media
            "appIcon": String(notification.appIcon || ""),
            "image": String(notification.image || ""),

            // Classification
            "category": String(notification.category || "generic"),
            "severity": String(notification.severity || "normal"),
            "tags": tagsToStrings(notification.tags),

            // Lifecycle
            "state": String(notification.state || "active"),
            "createdAt": Number(notification.createdAt || 0),
            "updatedAt": Number(notification.updatedAt || 0),
            "resolvedAt": Number(notification.resolvedAt || 0),
            "dismissedAt": Number(notification.dismissedAt || 0),

            // Rich / live presentation
            "presentation": String(notification.presentation || "auto"),
            "live": notification.live === true,
            "liveSource": String(notification.liveSource || ""),
            "liveKey": String(notification.liveKey || ""),

            // Structured searchable data
            "metrics": toPlainValue(notification.metrics) || {},

            // Actions / subsystem information
            "context": toPlainValue(notification.context) || {},
            "actions": toPlainValue(notification.actions) || []
        };
    }

    function historyDocument() {
        const entries = [];

        for (let i = 0; i < notifications.count; i++) {
            entries.push(historySnapshot(notifications.get(i)));
        }

        return {
            "version": historyVersion,
            "savedAt": Date.now(),
            "notifications": entries
        };
    }

    function historyToJson() {
        return JSON.stringify(historyDocument(), null, 4) + "\n";
    }

    // ===== HISTORY STORAGE ======================================

    function scheduleHistorySave() {
        if (!historyReady || !historyEnabled)
            return;

        historySaveTimer.restart();
    }

    function saveHistory() {
        if (!historyReady || !historyEnabled)
            return;

        historyStatus = "saving";

        historyFile.setText(historyToJson());
    }

    function clearHistory() {
        historySaveTimer.stop();

        notifications.clear();
        markNotificationsChanged();

        historyStatus = "clearing";

        historyFile.setText(JSON.stringify({
            "version": historyVersion,
            "savedAt": Date.now(),
            "notifications": []
        }, null, 4) + "\n");
    }

    function setHistoryEnabled(enabled) {
        historyEnabled = enabled;

        if (historyEnabled && historyReady)
            saveHistory();
    }

    function loadHistory() {
        const probeStartMs = arrayCopyProbeEnabled ? Date.now() : 0;
        const raw = historyFile.text().trim();

        if (raw === "")
            return false;

        let document;

        try {
            document = JSON.parse(raw);
        } catch (error) {
            historyStatus = "parse-error";
            return false;
        }

        // Allows an old raw-array history file too.
        const entries = Array.isArray(document) ? document : Array.isArray(document.notifications) ? document.notifications : [];

        // Work only with the newest retained slice. This prevents a very
        // large legacy history file from inflating the live QML model before
        // pruning can happen.
        const copyStartMs = probeStartMs ? Date.now() : 0;
        const retainedEntries = entries.slice();
        const copyMs = copyStartMs ? Date.now() - copyStartMs : 0;

        retainedEntries.sort(function (a, b) {
            const aTime = Number((a && (a.updatedAt || a.createdAt)) || 0);
            const bTime = Number((b && (b.updatedAt || b.createdAt)) || 0);

            return aTime - bTime;
        });

        const firstRetainedIndex = Math.max(0, retainedEntries.length - maxHistoryEntries);

        for (let i = firstRetainedIndex; i < retainedEntries.length; i++) {
            const entry = normalize(retainedEntries[i]);

            // Old history should not reopen as a popup.
            entry.expiresAt = 0;

            const existingIndex = indexOfNotification(notifications, entry.id);

            if (existingIndex === -1) {
                notifications.append(entry);
            } else {
                const existing = notifications.get(existingIndex);

                const existingTime = Number(existing.updatedAt || existing.createdAt || 0);

                const incomingTime = Number(entry.updatedAt || entry.createdAt || 0);

                // Duplicate IDs can exist in old/corrupt history.
                // Keep the newest version.
                if (incomingTime >= existingTime) {
                    replaceModelEntry(notifications, existingIndex, entry);
                }
            }
        }

        pruneHistory();
        markNotificationsChanged();

        if (probeStartMs)
            console.warn("SYNTAGMA_ARRAY_PROBE // notifications-history load"
                         + " scanned=" + entries.length
                         + " retained=" + retainedEntries.length
                         + " copyMs=" + copyMs
                         + " totalMs=" + (Date.now() - probeStartMs)
                         + " tsMs=" + Date.now());
        return entries.length > notifications.count;
    }

    FileView {
        id: historyFile

        path: Quickshell.dataPath("notifications-history.json")

        atomicWrites: true
        printErrors: true

        onLoaded: {
            const historyWasTrimmed = root.loadHistory();

            root.historyReady = true;
            root.historyStatus = "ready";

            if (historyWasTrimmed && root.historyEnabled)
                root.saveHistory();
        }

        onLoadFailed: function (error) {
            root.historyReady = true;

            if (error === FileViewError.FileNotFound) {
                root.historyStatus = "new";

                root.saveHistory();
                return;
            }

            root.historyStatus = "load-error";
        }

        onSaved: {
            root.historyStatus = "saved";
        }

        onSaveFailed: function (error) {
            root.historyStatus = "save-error";
        }
    }

    Timer {
        id: historySaveTimer

        interval: 1000
        repeat: false

        onTriggered: {
            root.saveHistory();
        }
    }

    // ===== FAVORITES STORAGE ====================================
    // Keep favorite identities without storing message bodies, and do not
    // mix preference state into DND/snooze policy records.

    function favoriteDocument() {
        const entries = [];
        for (let i = 0; i < favoriteSources.count; i++) {
            const entry = favoriteSources.get(i);
            entries.push({
                "appKey": String(entry.appKey || ""),
                "source": String(entry.source || ""),
                "sourceId": String(entry.sourceId || "")
            });
        }
        return {
            "version": favoriteVersion,
            "savedAt": Date.now(),
            "favorites": entries
        };
    }

    function scheduleFavoritesSave() {
        if (favoritesReady)
            favoritesSaveTimer.restart();
    }

    function saveFavorites() {
        if (!favoritesReady)
            return;
        favoritesStatus = "saving";
        favoritesFile.setText(JSON.stringify(favoriteDocument(), null, 4) + "\n");
    }

    function loadFavorites() {
        const raw = favoritesFile.text().trim();
        if (raw === "")
            return;
        let document;
        try {
            document = JSON.parse(raw);
        } catch (error) {
            favoritesStatus = "parse-error";
            return;
        }
        const entries = Array.isArray(document.favorites) ? document.favorites : [];
        favoriteSources.clear();
        for (let i = 0; i < entries.length; i++) {
            const row = entries[i] || {};
            const key = String(row.appKey || sourceKey(row.sourceId, row.source)).trim().toLowerCase();
            if (key === "" || favoriteIndex(key) !== -1)
                continue;
            favoriteSources.append({
                "appKey": key,
                "source": String(row.source || ""),
                "sourceId": String(row.sourceId || "")
            });
        }
        favoritesRevision += 1;
    }

    FileView {
        id: favoritesFile
        path: Quickshell.dataPath("notification-favorites.json")
        atomicWrites: true
        printErrors: true

        onLoaded: {
            root.loadFavorites();
            root.favoritesReady = true;
            if (root.favoritesStatus !== "parse-error")
                root.favoritesStatus = "ready";
        }

        onLoadFailed: function(error) {
            root.favoritesReady = true;
            if (error === FileViewError.FileNotFound) {
                root.favoritesStatus = "new";
                root.saveFavorites();
            } else {
                root.favoritesStatus = "load-error";
            }
        }

        onSaved: root.favoritesStatus = "saved"
        onSaveFailed: function(error) { root.favoritesStatus = "save-error"; }
    }

    Timer {
        id: favoritesSaveTimer
        interval: 250
        repeat: false
        onTriggered: root.saveFavorites()
    }

    // ===== POLICY STORAGE ======================================

    function policyDocument() {
        const policies = [];

        for (let i = 0; i < sourcePolicies.count; i++) {
            const policy = sourcePolicies.get(i);

            policies.push({
                "appKey": String(policy.appKey || ""),
                "source": String(policy.source || ""),
                "sourceId": String(policy.sourceId || ""),
                "dnd": policy.dnd === true,
                "snoozeUntil": Number(policy.snoozeUntil || 0)
            });
        }

        return {
            "version": policyVersion,
            "savedAt": Date.now(),
            "defaultSnoozeDurationMs": Number(defaultSnoozeDurationMs),
            "policies": policies
        };
    }

    function policyToJson() {
        return JSON.stringify(policyDocument(), null, 4) + "\n";
    }

    function schedulePolicySave() {
        if (!policyReady)
            return;

        policySaveTimer.restart();
    }

    function savePolicies() {
        if (!policyReady)
            return;

        policyStatus = "saving";
        policyFile.setText(policyToJson());
    }

    function loadPolicies() {
        const raw = policyFile.text().trim();

        if (raw === "")
            return false;

        let document;

        try {
            document = JSON.parse(raw);
        } catch (error) {
            policyStatus = "parse-error";
            return false;
        }

        const loadedDuration = Number(document.defaultSnoozeDurationMs || 24 * 60 * 60 * 1000);
        defaultSnoozeDurationMs = Math.max(60 * 1000, Math.min(30 * 24 * 60 * 60 * 1000, loadedDuration));

        const policies = Array.isArray(document.policies) ? document.policies : [];
        const now = Date.now();
        let pruned = false;

        sourcePolicies.clear();

        for (let i = 0; i < policies.length; i++) {
            const incoming = policies[i] || {};
            const key = String(incoming.appKey || sourceKey(incoming.sourceId, incoming.source)).trim().toLowerCase();
            const dnd = incoming.dnd === true;
            const snoozeUntil = Number(incoming.snoozeUntil || 0);

            if (!dnd && snoozeUntil <= now) {
                pruned = true;
                continue;
            }

            sourcePolicies.append({
                "appKey": key,
                "source": String(incoming.source || ""),
                "sourceId": String(incoming.sourceId || ""),
                "dnd": dnd,
                "snoozeUntil": dnd ? 0 : snoozeUntil
            });
        }

        policyRevision += 1;

        return pruned;
    }

    FileView {
        id: policyFile

        path: Quickshell.dataPath("notification-policies.json")

        atomicWrites: true
        printErrors: true

        onLoaded: {
            const policyWasPruned = root.loadPolicies();

            root.policyReady = true;

            if (root.policyStatus !== "parse-error")
                root.policyStatus = "ready";

            if (policyWasPruned && root.policyStatus !== "parse-error")
                root.savePolicies();
        }

        onLoadFailed: function (error) {
            root.policyReady = true;

            if (error === FileViewError.FileNotFound) {
                root.policyStatus = "new";
                root.savePolicies();
                return;
            }

            root.policyStatus = "load-error";
        }

        onSaved: {
            root.policyStatus = "saved";
        }

        onSaveFailed: function (error) {
            root.policyStatus = "save-error";
        }
    }

    Timer {
        id: policySaveTimer

        interval: 250
        repeat: false

        onTriggered: {
            root.savePolicies();
        }
    }

    Timer {
        interval: 60000
        repeat: true
        running: root.sourcePolicies.count > 0

        onTriggered: {
            root.expireSnoozes();
        }
    }

    // ===== SIMPLE PATH ==========================================

    function push(source, title, message) {
        appendNotification({
            "source": source,
            "title": title,
            "message": message
        });
    }

    // ===== RICH PATH ============================================

    function pushRich(notification) {
        appendNotification(notification);
    }

    // ===== EXTERNAL / CONVERTED PATH ============================

    function pushConverted(notification) {
        appendNotification(notification);
    }

    // ===== ACTIONS ==============================================

    function triggerAction(actionId, context) {
        NotificationsBackend.NotificationsActionRouter.route(actionId, context);
    }

    // ===== APOLLO DESTINATION ===================================
    // Route from the actual historical record. A caller supplies only the
    // event ID, not arbitrary destination fields, and saved events remain
    // navigable without storing native action objects.
    function apolloDestinationFor(eventId) {
        const id = String(eventId || "");
        if (id === "")
            return null;
        const index = indexOfNotification(notifications, id);
        if (index < 0)
            return null;
        return ApolloNotificationRoute.routeFor(notifications.get(index));
    }

    function hasApolloDestination(eventId) {
        return apolloDestinationFor(eventId) !== null;
    }

    function requestApolloDestination(eventId) {
        const destination = apolloDestinationFor(eventId);
        if (!destination)
            return false;
        apolloNavigationRequested(destination);
        return true;
    }

    // ===== SCROLL SPEED SETTINGS ================================
    function normalizeScrollSpeed(value) {
        const number = Number(value);
        if (!Number.isFinite(number))
            return 1.0;
        return Math.round(Math.max(0.5, Math.min(7.0, number)) * 10) / 10;
    }

    function setScrollSpeed(value) {
        if (scrollSpeedLocked)
            return false;
        const next = normalizeScrollSpeed(value);
        if (next === scrollSpeedMultiplier)
            return false;
        scrollSpeedMultiplier = next;
        scheduleScrollSettingsSave();
        return true;
    }

    function toggleScrollSpeedLock() {
        scrollSpeedLocked = !scrollSpeedLocked;
        scheduleScrollSettingsSave();
    }

    function scheduleScrollSettingsSave() {
        if (scrollSettingsReady)
            scrollSettingsSaveTimer.restart();
    }

    function saveScrollSettings() {
        if (!scrollSettingsReady)
            return;
        scrollSettingsFile.setText(JSON.stringify({
            "version": 1,
            "scrollSpeedMultiplier": scrollSpeedMultiplier,
            "scrollSpeedLocked": scrollSpeedLocked
        }, null, 2) + "\n");
    }

    function loadScrollSettings() {
        const raw = scrollSettingsFile.text().trim();
        if (raw === "")
            return;
        try {
            const document = JSON.parse(raw);
            if (!document || typeof document !== "object" || Array.isArray(document))
                return;
            if (document.scrollSpeedMultiplier !== undefined)
                scrollSpeedMultiplier = normalizeScrollSpeed(document.scrollSpeedMultiplier);
            scrollSpeedLocked = document.scrollSpeedLocked === true;
        } catch (error) {
            console.warn("Notifications scroll settings: invalid preferences; defaults retained");
        }
    }

    FileView {
        id: scrollSettingsFile
        path: Quickshell.dataPath("notification-scroll-settings.json")
        atomicWrites: true
        printErrors: true
        onLoaded: {
            root.loadScrollSettings();
            root.scrollSettingsReady = true;
        }
        onLoadFailed: function(error) {
            root.scrollSettingsReady = true;
            if (error !== FileViewError.FileNotFound)
                console.warn("Notifications scroll settings: could not load preferences");
        }
    }

    Timer {
        id: scrollSettingsSaveTimer
        interval: 250
        repeat: false
        onTriggered: root.saveScrollSettings()
    }

    // ===== EXPIRATION ===========================================

    function expireActiveNotifications() {
        // Close expired native notifications as well as fading the UI.
        expireExternalNotifications();
        const now = Date.now();

        for (let i = activeNotifications.count - 1; i >= 0; i--) {
            const entry = activeNotifications.get(i);

            if (Number(entry.expiresAt || 0) <= now)
                activeNotifications.remove(i);
        }
    }

    Timer {
        id: expiryTimer

        interval: 250
        repeat: true

        running: root.activeNotifications.count > 0
            || Object.keys(root.liveExternalNotifications).length > 0

        onTriggered: {
            root.expireActiveNotifications();
        }
    }
}
