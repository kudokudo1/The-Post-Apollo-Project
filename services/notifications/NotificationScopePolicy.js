// Notifications scope contract. Keys are always app-namespaced and never
// derived by guessing people, DMs, channels, or servers from message bodies.
// A literal TITLE option is available only as an explicitly selected fallback.

function token(value) {
    return String(value === undefined || value === null ? "" : value).trim();
}

function stableId(value) {
    const s = token(value);
    return s.length > 0 && s.length <= 160 && /^[a-zA-Z0-9_.:@\/-]+$/.test(s)
        ? s : "";
}

function label(value, fallback) {
    const s = token(value);
    return s ? s.slice(0, 120) : token(fallback).slice(0, 120);
}

// Only specifically named metadata is treated as sender/channel identity.
// These are defined by a producer, never extracted from title/body guesses.
function scopeFromHints(hints) {
    const h = hints || {};
    const fields = [
        ["senderId", "x-post-apollo-sender-id"],
        ["senderName", "x-post-apollo-sender-name"],
        ["conversationId", "x-post-apollo-conversation-id"],
        ["conversationName", "x-post-apollo-conversation-name"],
        ["serverId", "x-post-apollo-server-id"],
        ["serverName", "x-post-apollo-server-name"],
        ["channelId", "x-post-apollo-channel-id"],
        ["channelName", "x-post-apollo-channel-name"]
    ];
    const out = {};
    for (let i = 0; i < fields.length; i++) {
        const [name, hintName] = fields[i];
        const value = h[hintName];
        const normalized = name.endsWith("Id") ? stableId(value) : token(value).slice(0, 120);
        if (normalized)
            out[name] = normalized;
    }
    return out;
}

function scopeKey(appKey, kind, scopeId) {
    const app = token(appKey).toLowerCase();
    const value = token(scopeId);
    if (!app || !value || !/^(sender|conversation|server|channel|event|title)$/.test(kind))
        return "";
    return "scope:" + kind + ":" + encodeURIComponent(app) + "::"
        + encodeURIComponent(value);
}

function scopeOptionsFor(entry, appKey, websiteKey) {
    const e = entry || {};
    const ctx = e.context || {};
    const raw = ctx.notificationScope || {};
    const s = {
        senderId: stableId(raw.senderId),
        senderName: token(raw.senderName),
        conversationId: stableId(raw.conversationId),
        conversationName: token(raw.conversationName),
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
    function add(kind, id, text, verified, key) {
        const ruleKey = key || scopeKey(app, kind, id);
        if (!ruleKey || seen[ruleKey])
            return;
        seen[ruleKey] = true;
        options.push({
            kind: kind,
            key: ruleKey,
            label: label(text, kind.toUpperCase()),
            verified: verified === true
        });
    }

    // A channel is scoped to its containing server, where known.
    if (s.conversationId)
        add("conversation", s.conversationId, "DM // " + label(s.conversationName, s.conversationId), true);
    if (s.channelId)
        add("channel", (s.serverId ? s.serverId + "/" : "") + s.channelId,
            "CHANNEL // " + label(s.channelName, s.channelId), true);
    if (s.serverId)
        add("server", s.serverId, "SERVER // " + label(s.serverName, s.serverId), true);
    if (s.senderId)
        add("sender", s.senderId, "SENDER // " + label(s.senderName, s.senderId), true);

    // Apollo event families can be independently managed when the producer
    // supplied a stable explicit event type.
    const eventId = stableId(ctx.eventType);
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
    if (title && title.length <= 160)
        add("title", title, "TITLE EXACT // " + title, false);

    // For sources without verified child identity, put the exact-title option
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
