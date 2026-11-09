// Custom Vencord userplugin, NOT part of a default Vesktop installation.
// Requires explicit enablement and allowlisted Discord channels/servers.
// Uses structured Discord message events, never titles, DOM, tokens or bodies.
import { definePluginSettings } from "@api/Settings";
import definePlugin, { OptionType, PluginNative } from "@utils/types";
import { ChannelStore, FluxDispatcher, UserStore } from "@webpack/common";
import { allowedDiscordChannels, scopedDiscordEvent } from "./identity";

const Native = VencordNative.pluginHelpers.PostApolloNotificationBridge
    as PluginNative<typeof import("./native")>;

const settings = definePluginSettings({
    enabled: {
        type: OptionType.BOOLEAN,
        description: "Explicitly forward identity-only alerts from allowlisted channels/servers to Post-Apollo Notifications. Off by default.",
        default: false
    },
    channelIds: {
        type: OptionType.STRING,
        description: "Discord channel IDs to include, comma-separated. Leave empty for none.",
        default: ""
    },
    serverIds: {
        type: OptionType.STRING,
        description: "Discord server IDs to include ALL channels within each server. Leave empty for none.",
        default: ""
    }
});

const recent = new Set<string>();

function onMessage(event: any): void {
    if (settings.store.enabled !== true)
        return;
    const channelAllowed = allowedDiscordChannels(settings.store.channelIds);
    const serverAllowed = allowedDiscordChannels(settings.store.serverIds);
    if (channelAllowed.size === 0 && serverAllowed.size === 0)
        return;
    const messageId = String(event?.message?.id || "");
    if (recent.has(messageId))
        return;
    const channelId = String(event?.channelId ?? event?.channel_id
        ?? event?.message?.channel_id ?? "");
    const channel = ChannelStore.getChannel(channelId);
    const currentUser = UserStore.getCurrentUser();
    const payload = scopedDiscordEvent(event, channel, currentUser?.id,
        channelAllowed, serverAllowed);
    if (!payload)
        return;
    recent.add(payload.messageId);
    if (recent.size > 256) {
        const first = recent.values().next().value;
        if (first !== undefined) recent.delete(first);
    }
    // The native helper only creates a generic FDO notification with IDs
    // in typed hints. It never receives the actual Discord message text.
    void Native.emit(payload).then(result => {
        if (result.status === "NOTIFY_UNAVAILABLE")
            console.warn("Post-Apollo identity alerts: local notify-send unavailable");
    }).catch(() => {
        console.warn("Post-Apollo identity alerts: native notification unavailable");
    });
}

export default definePlugin({
    name: "PostApolloNotificationBridge",
    description: "Opt-in per-channel/server Discord identity-only notifications for Post-Apollo",
    authors: [{ name: "Post Apollo", id: 0n }],
    settings,
    start() {
        FluxDispatcher.subscribe("MESSAGE_CREATE", onMessage);
    },
    stop() {
        FluxDispatcher.unsubscribe("MESSAGE_CREATE", onMessage);
        recent.clear();
    }
});
