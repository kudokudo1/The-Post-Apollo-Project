// Vencord native helper: opt-in, metadata-only Linux notification producer.
// Narrowly validate all browser-provided values; no arbitrary paths, commands,
// network, tokens, message bodies, webhooks or shell interpretation.
import { execFile } from "node:child_process";
import type { IpcMainInvokeEvent } from "electron";

const snowflake = (v: unknown): string =>
    typeof v === "string" && /^\d{15,22}$/.test(v) ? v : "";

function safeDisplay(v: unknown): string {
    return typeof v === "string"
        ? v.trim().replace(/[\r\n\x00-\x1f\x7f]/g, " ").slice(0, 80)
        : "";
}

type Identity = {
    accountId: string;
    senderId: string;
    messageId: string;
    channelId: string;
    guildId?: string;
    groupId?: string;
    conversationId?: string;
    conversationType?: string;
    senderName?: string;
    channelName?: string;
    conversationName?: string;
};

// Only the exact fields Post-Apollo's NotificationsConverter already reads.
// All outgoing content is generic. The native helper cannot be used to
// deliver arbitrary notification text or execute arbitrary shell commands.
function notificationArgs(raw: unknown): string[] | null {
    if (!raw || typeof raw !== "object" || Array.isArray(raw))
        return null;
    const m = raw as Record<string, unknown>;
    const accountId = snowflake(m.accountId);
    const senderId = snowflake(m.senderId);
    const channelId = snowflake(m.channelId);
    const messageId = snowflake(m.messageId);
    if (!accountId || !senderId || !channelId || !messageId
            || accountId === senderId)
        return null;
    const guildId = snowflake(m.guildId);
    const groupId = snowflake(m.groupId);
    const conversationId = snowflake(m.conversationId);
    const conversationType = m.conversationType === "direct" ? "direct"
        : m.conversationType === "group" ? "group" : "";
    if ((guildId && (groupId || conversationId))
            || (!guildId && (!conversationType || conversationId !== channelId))
            || (conversationType === "group" && groupId !== channelId)
            || (conversationType === "direct" && groupId))
        return null;
    const hints: Array<[string, string]> = [
        ["desktop-entry", "vesktop"],
        ["category", "im.received"],
        ["x-post-apollo-account-id", accountId],
        ["x-post-apollo-sender-id", senderId],
    ];
    if (guildId) {
        hints.push(["x-post-apollo-server-id", guildId]);
        hints.push(["x-post-apollo-channel-id", channelId]);
        const channelName = safeDisplay(m.channelName);
        if (channelName) hints.push(["x-post-apollo-channel-name", channelName]);
    } else {
        hints.push(["x-post-apollo-conversation-id", conversationId]);
        hints.push(["x-post-apollo-conversation-type", conversationType]);
        if (groupId) hints.push(["x-post-apollo-group-id", groupId]);
        const conversationName = safeDisplay(m.conversationName);
        if (conversationName)
            hints.push(["x-post-apollo-conversation-name", conversationName]);
    }
    const senderName = safeDisplay(m.senderName);
    if (senderName) hints.push(["x-post-apollo-sender-name", senderName]);
    const args = ["--app-name=Vesktop", "--urgency=normal", "--expire-time=6500"];
    for (const [name, value] of hints)
        args.push("--hint=string:" + name + ":" + value);
    // notify-send is invoked with execFile, never a shell. ID input never
    // controls the program, options, title, body, or executable path.
    args.push("--", "Discord // New message",
        "From an explicitly allowed Discord channel or conversation");
    return args;
}

const sent = new Map<string, number>();
let minuteStart = 0;
let minuteCount = 0;
const PER_MINUTE = 12;

export async function emit(_event: IpcMainInvokeEvent,
                           raw: unknown): Promise<{ status: string }> {
    const args = notificationArgs(raw);
    if (!args) return { status: "INVALID" };
    const messageId = (raw as Identity).messageId;
    const now = Date.now();
    if (now - minuteStart >= 60000) {
        minuteStart = now;
        minuteCount = 0;
    }
    if (minuteCount >= PER_MINUTE || sent.has(messageId))
        return { status: "RATE_LIMITED_OR_DUPLICATE" };
    // Memory only, bounded. No message content or IDs written to storage.
    minuteCount += 1;
    sent.set(messageId, now);
    if (sent.size > 128) {
        const oldest = sent.keys().next().value;
        if (oldest !== undefined) sent.delete(oldest);
    }
    return new Promise(resolve => {
        execFile("notify-send", args,
            { timeout: 2500, windowsHide: true, maxBuffer: 4096 },
            error => resolve({ status: error ? "NOTIFY_UNAVAILABLE" : "DELIVERED" }));
    });
}
