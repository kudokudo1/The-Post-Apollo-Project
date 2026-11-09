// Notifications scope contract. Keys are always app-namespaced and never
// derived by guessing people, DMs, channels, or servers from message bodies.
// A literal TITLE option is available only as an explicitly selected fallback.

function token(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function stableId(value) {
    const s = token(value);
    return s.length > 0 && s.length <= 160 && /^[a-zA-Z0-9_.:@/+~-]+$/.test(s)
        ? s : "";
}

function label(value, fallback) {
    const s = token(value);
    return s ? s.slice(0, 120) : token(fallback).slice(0, 120);
}

// Only specifically named metadata is treated as sender/channel identity.
// These are defined by a producer, never extracted from title/body guesses.
// Nonempty only for explicit producer-declared types. Never infer from a
// title, displayed contact name, or a notification message body.
function conversationKind(value) {
    const kind = token(value).toLowerCase();
    return /^(direct|group|thread|channel)$/.test(kind) ? kind : "";
}

// IDs are separated by lengths, not a delimiter alone: provider/account
// names and native IDs can legally contain '/' or ':'.
function scopedIdentity(accountId, value) {
    const account = stableId(accountId);
    const id = stableId(value);
    if (!id)
        return "";
    return account ? account.length + ":" + account + ":" + id : id;
}

function scopeFromHints(hints) {
    const h = hints || {};
    const fields = [
        ["senderId", "x-post-apollo-sender-id"],
        ["senderName", "x-post-apollo-sender-name"],
        ["contactId", "x-post-apollo-contact-id"],
        ["contactName", "x-post-apollo-contact-name"],
        ["accountId", "x-post-apollo-account-id"],
        ["accountName", "x-post-apollo-account-name"],
        ["conversationType", "x-post-apollo-conversation-type"],
        ["conversationId", "x-post-apollo-conversation-id"],
        ["conversationName", "x-post-apollo-conversation-name"],
        ["groupId", "x-post-apollo-group-id"],
        ["groupName", "x-post-apollo-group-name"],
        ["threadId", "x-post-apollo-thread-id"],
        ["threadName", "x-post-apollo-thread-name"],
        ["serverId", "x-post-apollo-server-id"],
        ["serverName", "x-post-apollo-server-name"],
        ["channelId", "x-post-apollo-channel-id"],
        ["channelName", "x-post-apollo-channel-name"]
    ];
    const out = {};
    for (let i = 0; i < fields.length; i++) {
        const [name, hintName] = fields[i];
        const value = h[hintName];
        const normalized = name.endsWith("Id") ? stableId(value)
            : name === "conversationType" ? conversationKind(value)
            : token(value).slice(0, 120);
        if (normalized)
            out[name] = normalized;
    }
    return out;
}

function scopeKey(appKey, kind, scopeId) {
    const app = token(appKey).toLowerCase();
    const value = token(scopeId);
    if (!app || !value || !/^(account|sender|conversation|group|thread|server|channel|resource|resourceEvent|event|title)$/.test(kind))
        return "";
    // Existing policy stores lowercase keys. Encode UTF-16 code units in
    // fixed-width hexadecimal so case-sensitive sender IDs and literal
    // titles do not collapse into the same policy key.
    let encoded = "";
    for (let i = 0; i < value.length; i++) {
        const part = value.charCodeAt(i).toString(16);
        encoded += ("0000" + part).slice(-4);
    }
    return "scope:" + kind + ":" + encodeURIComponent(app) + "::" + encoded;
}

function scopeOptionsFor(entry, appKey, websiteKey) {
    const e = entry || {};
    const ctx = e.context || {};
    const raw = ctx.notificationScope || {};
    const s = {
        accountId: stableId(raw.accountId),
        accountName: token(raw.accountName),
        senderId: stableId(raw.senderId || raw.contactId),
        senderName: token(raw.senderName || raw.contactName),
        isContact: !raw.senderId && !!stableId(raw.contactId),
        conversationType: conversationKind(raw.conversationType),
        conversationId: stableId(raw.conversationId),
        conversationName: token(raw.conversationName),
        groupId: stableId(raw.groupId),
        groupName: token(raw.groupName),
        threadId: stableId(raw.threadId),
        threadName: token(raw.threadName),
        serverId: stableId(raw.serverId),
        serverName: token(raw.serverName),
        channelId: stableId(raw.channelId),
        channelName: token(raw.channelName)
    };
    const app = token(appKey).toLowerCase();
    const site = token(websiteKey);
    if (!app)
        return [];
    const options = [];
    const seen = {};
    function add(kind, id, text, structured, key) {
        const ruleKey = key || scopeKey(app, kind, id);
        if (!ruleKey || seen[ruleKey])
            return;
        seen[ruleKey] = true;
        options.push({
            kind: kind,
            key: ruleKey,
            label: label(text, kind.toUpperCase()),
            structured: structured === true
        });
    }

    // Group, thread and direct conversation identities are different rule
    // kinds. A group mute never becomes a sender mute or an app-wide mute.
    // Legacy untyped conversationId keeps the original key, but is displayed
    // as CHAT rather than making a false DM claim.
    const groupId = s.groupId || (s.conversationType === "group" ? s.conversationId : "");
    const threadId = s.threadId || (s.conversationType === "thread" ? s.conversationId : "");
    const groupName = s.groupName || s.conversationName;
    const threadName = s.threadName || s.conversationName;
    if (groupId)
        add("group", scopedIdentity(s.accountId, groupId),
            "GROUP // " + label(groupName, groupId), true);
    if (threadId)
        add("thread", scopedIdentity(s.accountId, threadId),
            "THREAD // " + label(threadName, threadId), true);
    if (s.conversationId && !groupId && !threadId
            && s.conversationType !== "channel")
        add("conversation", scopedIdentity(s.accountId, s.conversationId),
            (s.conversationType === "direct" ? "DM // " : "CHAT // ")
                + label(s.conversationName, s.conversationId), true);
    if (s.channelId)
        // Length-prefix server and account components separately to avoid
        // collision even if the native IDs contain '/' or ':'.
        add("channel", scopedIdentity(s.accountId,
            s.serverId.length + ":" + s.serverId + ":" + s.channelId),
            "CHANNEL // " + label(s.channelName, s.channelId), true);
    if (s.serverId)
        add("server", scopedIdentity(s.accountId, s.serverId),
            "SERVER // " + label(s.serverName, s.serverId), true);
    if (s.senderId)
        add("sender", scopedIdentity(s.accountId, s.senderId),
            (s.isContact ? "CONTACT // " : "SENDER // ")
                + label(s.senderName, s.senderId), true);
    if (s.accountId)
        add("account", s.accountId, "ACCOUNT // "
            + label(s.accountName, s.accountId), true);

    // A producer-declared resource identity is stable within its APP.
    // Old CPU++ pressure history stored only "metric"; accept it exclusively
    // for that known producer and explicit pressure event family. Never parse
    // arbitrary titles, bodies or numeric readings to guess a resource.
    const eventId = stableId(ctx.eventType);
    const legacyPressure = token(e.sourceId).toLowerCase() === "cpu-plus-resource-pressure"
        && /^resource-pressure-(warning|critical|recovered)$/.test(eventId);
    let resourceId = stableId(ctx.resourceId);
    if (!resourceId && legacyPressure
            && (ctx.metric === "memory" || ctx.metric === "storage"))
        resourceId = ctx.metric;
    const defaultName = resourceId === "memory" ? "MEMORY"
        : resourceId === "storage" ? "ROOT STORAGE"
        : resourceId.toUpperCase();
    const resourceName = label(ctx.resourceLabel, defaultName);
    if (resourceId && eventId) {
        const displayEvent = legacyPressure
            ? eventId.slice("resource-pressure-".length).toUpperCase()
            : eventId.toUpperCase();
        // Length-prefix the first component, avoiding separator collisions.
        const pair = resourceId.length + ":" + resourceId + ":" + eventId;
        add("resourceEvent", pair,
            "RESOURCE + EVENT // " + resourceName + " // " + displayEvent, true);
    }
    if (resourceId)
        add("resource", resourceId, "RESOURCE // " + resourceName, true);

    // EVENT remains intentionally cross-resource. Existing EVENT rules and
    // saved keys retain their exact meaning and are never migrated.
    if (eventId)
        add("event", eventId, "EVENT // " + eventId, true);

    // The browser-site identity is already derived from origin metadata.
    // Keep SITE -> APP as the first two choices for legacy website cards.
    if (site) {
        if (options.length === 0) {
            add("website", site, "SITE // " + label(e.website, e.websiteHost), true, site);
            add("app", app, "APP // " + label(e.source, app), true, app);
        } else {
            add("website", site, "SITE // " + label(e.website, e.websiteHost), true, site);
        }
    }
    if (!site || options[options.length - 1].kind !== "app")
        add("app", app, "APP // " + label(e.source, app), true, app);

    // Exact TITLE is a deliberately weaker matching option. It never claims
    // to identify a person/server, and the body is never included in its key.
    const title = token(e.originalTitle || e.title);
    const genericTitle = title.toLowerCase();
    const appTitle = token(e.source).toLowerCase();
    // "Discord" or "New message" would match unrelated conversations.
    // Refuse this misleading "narrow" target rather than muting everyone.
    const ambiguousTitles = [
        "message", "new message", "new messages", "notification",
        "new notification", "notifications", "direct message", "dm"
    ];
    if (title && title.length <= 160 && genericTitle !== appTitle
            && ambiguousTitles.indexOf(genericTitle) === -1)
        add("title", title, "TITLE EXACT // " + title, false);

    // For sources without structured child identity, put the exact-title option
    // before APP so a card star/DND defaults to the narrower observable text.
    if (!site && options.length > 0 && options[0].kind === "app") {
        const titleIndex = options.findIndex(x => x.kind === "title");
        if (titleIndex > 0) {
            const value = options.splice(titleIndex, 1)[0];
            options.unshift(value);
        }
    }
    return options;
}
