pragma Singleton

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Services.Notifications
import "." as NotificationsBackend

Singleton {
    id: root

    property ListModel notifications: ListModel {}
    property ListModel activeNotifications: ListModel {}

    property int normalTimeoutMs: 5000
    property int extendedTimeoutMs: 10000

    property int notificationSerial: 0

    property int historyVersion: 1
    property bool historyReady: false
    property bool historyEnabled: true
    property string historyStatus: "loading"

    // ===== EXTERNAL NOTIFICATIONS ===============================

    NotificationServer {
        id: notificationServer

        keepOnReload: false

        onNotification: function (notification) {
            notification.tracked = true;

            // root.pushConverted({
            //     "source": "CONVERTER BYPASS",
            //     "title": notification.summary,
            //     "message": notification.body
            // });

            // root.push(
            //     "EXTERNAL",
            //     notification.summary,
            //     notification.body
            // );

            root.pushConverted(NotificationsBackend.NotificationsConverter.convert(notification));
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

        return {
            // Identity
            "id": notification.id || makeNotificationId(),

            // Source
            "source": notification.source || "",
            "sourceId": notification.sourceId || "",

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

        if (activeIndex === -1) {
            activeNotifications.append(entry);
        } else {
            replaceModelEntry(activeNotifications, activeIndex, entry);
        }

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

        if (historyUpdated)
            scheduleHistorySave();

        return historyUpdated || activeUpdated;
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
        const raw = historyFile.text().trim();

        if (raw === "")
            return;

        let document;

        try {
            document = JSON.parse(raw);
        } catch (error) {
            historyStatus = "parse-error";
            return;
        }

        // Allows an old raw-array history file too.
        const entries = Array.isArray(document) ? document : document.notifications || [];

        for (let i = 0; i < entries.length; i++) {
            const entry = normalize(entries[i]);

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
    }

    FileView {
        id: historyFile

        path: Quickshell.dataPath("notifications-history.json")

        atomicWrites: true
        printErrors: true

        onLoaded: {
            root.loadHistory();

            root.historyReady = true;
            root.historyStatus = "ready";
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

    // ===== EXPIRATION ===========================================

    function expireActiveNotifications() {
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

        onTriggered: {
            root.expireActiveNotifications();
        }
    }
}
