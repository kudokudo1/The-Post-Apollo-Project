// Discord event -> minimal Post-Apollo identity metadata.
// No token lookup, network calls, message content, files, or DOM parsing.
// A caller MUST opt in and explicitly allow each channel first.
export function discordSnowflake(value: unknown): string {
    const id = typeof value === "string" ? value : "";
    return /^\d{15,22}$/.test(id) ? id : "";
}

export function allowedDiscordChannels(raw: unknown): Set<string> {
    const ids = typeof raw === "string" ? raw.split(/[\s,;]+/) : [];
    const allowed = new Set<string>();
    for (const candidate of ids.slice(0, 64)) {
        const id = discordSnowflake(candidate);
        if (id) allowed.add(id);
    }
    return allowed.size <= 32 ? allowed : new Set<string>();
}

function label(value: unknown): string {
    if (typeof value !== "string") return "";
    const text = value.trim();
    // Display metadata is bounded, single-line, and never message content.
    return text.replace(/[\r\n\x00-\x1f\x7f]/g, " ").slice(0, 80);
}

// Event and channel originate in the authorized client dispatcher/store.
// These objects are not trusted just because the renderer passed them.
export function scopedDiscordEvent(event: any, channel: any, selfId: unknown,
                                    allowed: Set<string>,
                                    allowedServers: Set<string>): Record<string, string> | null {
    const msg = event?.message;
    const accountId = discordSnowflake(selfId);
    const senderId = discordSnowflake(msg?.author?.id);
    const messageId = discordSnowflake(msg?.id);
    const channelId = discordSnowflake(event?.channelId ?? event?.channel_id ?? msg?.channel_id);
    if (!accountId || !senderId || !messageId || !channelId
            || senderId === accountId || event?.optimistic || msg?.state === "SENDING"
            || discordSnowflake(channel?.id) !== channelId)
        return null;
    const guildId = discordSnowflake(channel?.guild_id ?? event?.guildId ?? msg?.guild_id);
    if (!allowed.has(channelId)
            && !(guildId && allowedServers.has(guildId)))
        return null;
    const groupDm = !guildId && channel?.type === 3;
    const direct = !guildId && channel?.type === 1;
    // Unknown channel kinds never imply group/DM (or generate new popups).
    if (!guildId && !groupDm && !direct) return null;
    const result: Record<string, string> = {
        accountId, senderId, channelId, messageId
    };
    const senderName = label(msg?.author?.username);
    if (senderName) result.senderName = senderName;
    if (guildId) {
        result.guildId = guildId;
        const channelName = label(channel?.name);
        if (channelName) result.channelName = channelName;
    } else {
        result.conversationId = channelId;
        result.conversationType = groupDm ? "group" : "direct";
        if (groupDm) result.groupId = channelId;
        const conversationName = label(channel?.name);
        if (conversationName) result.conversationName = conversationName;
    }
    return result;
}


function oneLineLabel(value: unknown): string {
    if (typeof value !== "string") return "";
    return value.trim().replace(/[\r\n\x00-\x1f\x7f]/g, " ").slice(0, 80);
}

// Pure command-argument builder, shared by native code and contract tests.
// It does NOT execute a process. Only this fixed, generic notification is
// possible through the paired native helper.
export function notificationArgs(raw: unknown,
                                 desktopEntry = "vesktop"): string[] | null {
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
    const m = raw as Record<string, unknown>;
    const accountId = discordSnowflake(m.accountId);
    const senderId = discordSnowflake(m.senderId);
    const messageId = discordSnowflake(m.messageId);
    const channelId = discordSnowflake(m.channelId);
    if (!accountId || !senderId || !messageId || !channelId
            || accountId === senderId) return null;
    const guildId = discordSnowflake(m.guildId);
    const groupId = discordSnowflake(m.groupId);
    const conversationId = discordSnowflake(m.conversationId);
    const kind = m.conversationType;
    if ((guildId && (groupId || conversationId || kind))
            || (!guildId && (!conversationId || conversationId !== channelId))
            || (!guildId && kind !== "group" && kind !== "direct")
            || (kind === "group" && groupId !== channelId)
            || (kind === "direct" && groupId))
        return null;

    // The Flatpak desktop entry is dev.vencord.Vesktop, while a native
    // Vesktop install commonly reports vesktop. Reject arbitrary callers.
    if (desktopEntry !== "vesktop" && desktopEntry !== "dev.vencord.Vesktop")
        return null;
    const hints: Array<[string, string]> = [
        ["desktop-entry", desktopEntry],
        ["category", "im.received"],
        ["x-post-apollo-account-id", accountId],
        ["x-post-apollo-sender-id", senderId]
    ];
    if (guildId) {
        hints.push(["x-post-apollo-server-id", guildId]);
        hints.push(["x-post-apollo-channel-id", channelId]);
        const channelName = oneLineLabel(m.channelName);
        if (channelName) hints.push(["x-post-apollo-channel-name", channelName]);
    } else {
        hints.push(["x-post-apollo-conversation-id", conversationId]);
        hints.push(["x-post-apollo-conversation-type", String(kind)]);
        if (groupId) hints.push(["x-post-apollo-group-id", groupId]);
        const conversationName = oneLineLabel(m.conversationName);
        if (conversationName)
            hints.push(["x-post-apollo-conversation-name", conversationName]);
    }
    const senderName = oneLineLabel(m.senderName);
    if (senderName) hints.push(["x-post-apollo-sender-name", senderName]);
    const args = ["--app-name=Vesktop", "--urgency=normal", "--expire-time=6500"];
    for (const [key, value] of hints)
        args.push("--hint=string:" + key + ":" + value);
    args.push("--", "Discord // New message",
        "Incoming message from an explicitly allowed Discord conversation");
    return args;
}
