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
                                    allowed: Set<string>): Record<string, string> | null {
    const msg = event?.message;
    const accountId = discordSnowflake(selfId);
    const senderId = discordSnowflake(msg?.author?.id);
    const messageId = discordSnowflake(msg?.id);
    const channelId = discordSnowflake(event?.channelId ?? event?.channel_id ?? msg?.channel_id);
    if (!accountId || !senderId || !messageId || !channelId
            || senderId === accountId || event?.optimistic || msg?.state === "SENDING"
            || !allowed.has(channelId) || discordSnowflake(channel?.id) !== channelId)
        return null;
    const guildId = discordSnowflake(channel?.guild_id ?? event?.guildId ?? msg?.guild_id);
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
