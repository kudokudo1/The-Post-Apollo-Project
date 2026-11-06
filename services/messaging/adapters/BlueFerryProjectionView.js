// P18e // Pure display validation for an already delivered P18a projection.
// NOT a trust decision: a hostile QML caller can forge any snapshot and token.
// No transport, filesystem, Bluetooth, account, or provider access here.
var PROJECTION_SCHEMA = "post-apollo.phone.blueferry-social-projection.v0";
var PROFILE_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
var TIME_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;

function objectOnly(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function safeText(value, max, emptyAllowed) {
    if (typeof value !== "string" || value.length > max
            || (!emptyAllowed && value.length === 0))
        return false;
    return !/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(value);
}

function countValue(value, max) {
    return typeof value === "number" && Number.isInteger(value)
           && value >= 0 && value <= max;
}

function validProfile(profileId) {
    return typeof profileId === "string" && PROFILE_RE.test(profileId);
}

function validOpaqueContext(key) {
    return typeof key === "string" && /^[A-Za-z0-9_-]{16,96}$/.test(key);
}

function validDeliveryEpoch(value) {
    return countValue(value, 2147483647) && value > 0;
}

function headerValid(payload, profileId) {
    return objectOnly(payload) && validProfile(profileId)
            && payload.schema === PROJECTION_SCHEMA
            && payload.execution === "OFFLINE_PROJECTION_ONLY"
            && payload.serviceId === "blueferry"
            && payload.deviceProfileId === profileId
            && payload.authorization === "NOT_EVALUATED"
            && payload.routeEligible === false;
}

function messagesView(payload, profileId) {
    if (!headerValid(payload, profileId) || !Array.isArray(payload.conversations)
            || !Array.isArray(payload.messageSets)
            || payload.conversations.length > 64
            || payload.messageSets.length !== payload.conversations.length)
        return null;
    var conversations = [];
    var ids = Object.create(null);
    var messagesById = Object.create(null);
    var prefix = profileId + ":";
    for (var i = 0; i < payload.conversations.length; i++) {
        var row = payload.conversations[i];
        if (!objectOnly(row) || !safeText(row.id, 2048, false)
                || row.id.indexOf(prefix) !== 0
                || Object.prototype.hasOwnProperty.call(ids, row.id)
                || row.serviceId !== "blueferry"
                || (row.type !== "direct" && row.type !== "group")
                || !safeText(row.displayNameInProfile, 256, false)
                || !safeText(row.lastMessage, 16384, true)
                || !countValue(row.unreadCount, 1000000))
            return null;
        ids[row.id] = true;
        conversations.push({
            id: row.id,
            serviceId: "blueferry",
            type: row.type,
            displayNameInProfile: row.displayNameInProfile,
            lastMessage: row.lastMessage,
            unreadCount: row.unreadCount
        });
    }
    for (var j = 0; j < payload.messageSets.length; j++) {
        var group = payload.messageSets[j];
        if (!objectOnly(group) || typeof group.conversationId !== "string"
                || !Object.prototype.hasOwnProperty.call(ids, group.conversationId)
                || Object.prototype.hasOwnProperty.call(messagesById, group.conversationId)
                || !Array.isArray(group.messages) || group.messages.length > 256)
            return null;
        var messages = [];
        var messageIds = Object.create(null);
        var previousTime = -Infinity;
        for (var k = 0; k < group.messages.length; k++) {
            var item = group.messages[k];
            if (!objectOnly(item) || !safeText(item.id, 3200, false)
                    || item.id.indexOf(group.conversationId + ":message:") !== 0
                    || Object.prototype.hasOwnProperty.call(messageIds, item.id)
                    || item.conversationId !== group.conversationId
                    || !safeText(item.body, 16384, true)
                    || (item.direction !== "incoming" && item.direction !== "outgoing")
                    || typeof item.sent_at !== "string" || item.sent_at.length > 64
                    || !TIME_RE.test(item.sent_at)
                    || item.timestampUnit !== "iso8601-offset"
                    || typeof item.read !== "boolean")
                return null;
            var when = Date.parse(item.sent_at);
            if (!Number.isFinite(when) || when < previousTime)
                return null;
            previousTime = when;
            messageIds[item.id] = true;
            var view = {
                id: item.id,
                conversationId: item.conversationId,
                body: item.body,
                direction: item.direction,
                sent_at: item.sent_at,
                timestampUnit: "iso8601-offset"
            };
            if (item.senderId !== undefined) {
                if (!safeText(item.senderId, 254, false))
                    return null;
                view.senderId = item.senderId;
            }
            messages.push(view);
        }
        messagesById[group.conversationId] = messages;
    }
    for (var n = 0; n < conversations.length; n++) {
        if (!Object.prototype.hasOwnProperty.call(messagesById, conversations[n].id))
            return null;
    }
    return {conversations: conversations, messagesById: messagesById};
}

function contactsView(payload, profileId) {
    if (!headerValid(payload, profileId) || !Array.isArray(payload.contacts)
            || payload.contacts.length > 100
            || !safeText(payload.daemonEpoch, 64, false)
            || !countValue(payload.offset, 1000000)
            || !countValue(payload.total, 1000000)
            || payload.offset + payload.contacts.length > payload.total)
        return null;
    var rows = [], ids = Object.create(null);
    var prefix = profileId + ":" + payload.daemonEpoch + ":";
    for (var i = 0; i < payload.contacts.length; i++) {
        var card = payload.contacts[i];
        if (!objectOnly(card) || !safeText(card.id, 2048, false)
                || card.id.indexOf(prefix) !== 0
                || Object.prototype.hasOwnProperty.call(ids, card.id)
                || card.serviceId !== "blueferry"
                || card.deviceProfileId !== profileId
                || !safeText(card.displayNameInProfile, 256, false)
                || !safeText(card.organization, 256, true)
                || !safeText(card.primary, 254, true)
                || !countValue(card.phoneCount, 10000)
                || !countValue(card.emailCount, 10000)
                || typeof card.hasPhoto !== "boolean")
            return null;
        ids[card.id] = true;
        rows.push({
            id: card.id,
            serviceId: "blueferry",
            displayNameInProfile: card.displayNameInProfile,
            organization: card.organization,
            primary: card.primary,
            phoneCount: card.phoneCount,
            emailCount: card.emailCount,
            hasPhoto: card.hasPhoto
        });
    }
    return rows;
}
