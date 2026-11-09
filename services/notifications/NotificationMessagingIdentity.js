// Pure provider-record -> notificationScope translation.
// This is NOT a provider transport, credential source, or identity proof.
// Only a host that already owns an authorized live delivery may attach the
// resulting metadata to a notification. Never mine titles/bodies for IDs.
function messagingId(value) {
    if (typeof value !== "string")
        return "";
    const s = value.trim();
    return s.length > 0 && s.length <= 256
        && /^[A-Za-z0-9_.:@/+~-]+$/.test(s) ? s : "";
}

function messagingName(value) {
    return typeof value === "string"
        ? value.trim().slice(0, 120) : "";
}

function compactScope(scope) {
    const result = {};
    for (const key in scope) {
        if (Object.prototype.hasOwnProperty.call(scope, key) && scope[key])
            result[key] = scope[key];
    }
    return result;
}

// BlueFerrySocialProjection / BlueFerryProjectionView's read-only shapes.
// A cached snapshot is NOT itself a live message event; callers need an
// separately authorized delivery and current phone profile to emit one.
function blueFerryScope(conversation, message, profileId) {
    const profile = messagingId(profileId);
    if (!profile || !conversation || !message
            || conversation.serviceId !== "blueferry"
            || (conversation.type !== "direct" && conversation.type !== "group"))
        return {};
    const conversationId = messagingId(conversation.id);
    if (!conversationId || conversationId.indexOf(profile + ":") !== 0
            || message.conversationId !== conversation.id
            || message.direction !== "incoming")
        return {};
    const result = {
        accountId: profile,
        conversationId: conversationId,
        conversationType: conversation.type,
        conversationName: messagingName(conversation.displayNameInProfile)
    };
    // Group sender identity is available separately. Do not turn the
    // conversation title into a person/contact ID for direct messages.
    if (conversation.type === "group")
        result.senderId = messagingId(message.senderId);
    return compactScope(result);
}

// Matches Telegram bridge.py's normalize_dialog / normalize_message fields.
// Telegram currently has no liveUpdates capability in Social; this helper
// does not poll dialogs or create notifications from history.
function telegramScope(dialog, message, accountId) {
    if (!dialog || dialog.serviceId !== "telegram" || !message
            || message.direction !== "incoming"
            || message.conversationId !== dialog.id)
        return {};
    const peer = messagingId(dialog.id);
    if (!peer || !["private", "group", "channel"].includes(dialog.type))
        return {};
    const kind = dialog.type === "private" ? "direct" : dialog.type;
    const result = {
        accountId: messagingId(accountId),
        conversationId: peer,
        conversationType: kind,
        conversationName: messagingName(dialog.displayNameInProfile)
    };
    // A private dialog ID identifies the peer, but the bridge supplies
    // no sender ID for a member's message inside groups or channels.
    if (kind === "direct")
        result.contactId = peer;
    return compactScope(result);
}

// Discord/Vesktop opt-in metadata contract for a provider-side producer.
// Explicit native IDs only. A notification title, server name, or body is
// never accepted as a substitute for these IDs.
function discordScope(meta) {
    if (!meta || typeof meta !== "object")
        return {};
    const groupId = messagingId(meta.groupDmId);
    const dmId = messagingId(meta.dmId);
    const account = messagingId(meta.accountId);
    const guild = messagingId(meta.guildId);
    const channel = messagingId(meta.channelId);
    const sender = messagingId(meta.userId);
    return compactScope({
        accountId: account,
        accountName: messagingName(meta.accountName),
        serverId: guild,
        serverName: messagingName(meta.guildName),
        channelId: channel,
        channelName: messagingName(meta.channelName),
        groupId: groupId,
        groupName: messagingName(meta.groupDmName),
        conversationId: groupId || dmId,
        conversationType: groupId ? "group" : dmId ? "direct" : "",
        conversationName: messagingName(meta.groupDmName || meta.dmName),
        senderId: sender,
        senderName: messagingName(meta.userName)
    });
}

// Account-bound email sender and thread IDs must come from a provider
// adapter that actually knows which mailbox/message was delivered.
// The current Proton browser count-only pilot cannot provide these.
function emailScope(record) {
    if (!record || typeof record !== "object")
        return {};
    return compactScope({
        accountId: messagingId(record.accountId),
        accountName: messagingName(record.accountName),
        senderId: messagingId(record.senderAddress),
        senderName: messagingName(record.senderName),
        threadId: messagingId(record.threadId),
        threadName: messagingName(record.threadName)
    });
}
