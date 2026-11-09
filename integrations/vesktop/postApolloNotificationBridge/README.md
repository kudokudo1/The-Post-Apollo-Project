# Post-Apollo Notification Bridge // Vesktop Vencord userplugin

**State:** Source-built opt-in candidate; NOT installed, enabled, or accepted on the operator's desktop.  
**Owner:** Notifications integration. Vesktop/Vencord installation requires separate operator approval.  
**Native scope:** FDO `notify-send`, not Discord's API, DOM scraping, tokens, webhooks, or direct messaging.

## Mechanism

This three-file Vencord userplugin registers a `MESSAGE_CREATE` Flux listener, resolves the current account and native channel, and checks an **explicit allowlist** of Discord channel IDs or server IDs. Every eligible message except the current user's own is reduced to a small identity object: account ID, sender ID, channel or group-DM ID, guild/server ID when available, message ID for in-memory deduplication, and optional display names.

The renderer passes that object to one bounded native IPC method. The native method **only** invokes `notify-send` with a generic headline/body, plus the `x-post-apollo-*` freedesktop notification hints already recognized by `NotificationsConverter.qml`. No Discord message body, attachments, token, message content, or HTTP request is forwarded. The native method cannot choose arbitrary paths, programs, commands, notification text or URLs.

The existing Post-Apollo notification pipeline receives the structured hints and applies **BLOCK before history** and **DND/ZZ before popups**. Source IDs are `vesktop` and account/sender/server/channel/group/DM identities remain scoped independently. Rate-limits are 12 forwarded events per minute in native code, 256 renderer-side and 128 native in-memory recent IDs.

## Installation and activation are NOT automatic

**Do not install this while the operator's existing Vesktop/Quickshell state is unapproved for modification.**

To activate in a separately authorized test:

1. Have a compatible custom Vencord **source build** available. Copy this complete `postApolloNotificationBridge` folder into Vencord's `src/userplugins/`, build that Vencord source, and select its `dist` in **Vesktop Settings → Open Developer Settings → Vencord Location → Change**. A full Vesktop restart is required for `native.ts`; this is not an ordinary toggle in stock Vesktop.
2. Under **Discord User Settings → Vencord → Plugins**, find `PostApolloNotificationBridge`. Leave **Enable identity-only alerts** OFF until the source/build and notification routing have been reviewed.
3. Fill `channelIds` with individual authorized Discord channel IDs, or `serverIds` with whole-server IDs. These are **IDs**, not names, message text or invite URLs. Both fields default empty. There is no wildcard.
4. Prevent duplicates by disabling Vesktop's ordinary desktop alerts for the same conversations during the test, or temporarily using a single dedicated test channel. This producer emits **new** desktop alerts rather than enriching a separate existing popup. Do not enable broad server allowlists alongside ordinary Vesktop notifications.
5. Enable the plugin's `enabled` switch, send **one new** message to an allowlisted test channel from a separate authorized account, and confirm the message arrives in Notifications with APP, ACCOUNT, SERVER/CHANNEL or DM/GROUP, and SENDER policy choices. Block that scope and repeat: the second matching message must not appear in Post-Apollo history or popups. An unrelated new message should still pass.
6. Turn `enabled` OFF before concluding the test. If `notify-send` is unavailable inside the Vesktop sandbox, the helper returns `NOTIFY_UNAVAILABLE` without falling back to `flatpak-spawn --host` or arbitrary host execution. That is a documented deployment blocker, not permission to alter the sandbox silently.

Official references: [Vencord custom plugins](https://docs.vencord.dev/installing/custom-plugins/), [Vencord native helpers](https://docs.vencord.dev/plugins/native/), and [Vesktop custom Vencord location](https://docs.vencord.dev/installing/).

## Limitations and safety

- **No automatic Discord notification eligibility check.** Each new message in an allowlisted server/channel can produce a new generic alert regardless of Discord's own mute, mentions, read-state, blocked-user or quiet-hours behavior. Use **one test channel only** until that eligibility gate is independently designed and verified.
- The plugin does **not** connect to the Discord API, read tokens, fetch message history or store message bodies.
- The renderer-provided IDs are native-client metadata, **not cryptographically authenticated identity**. A malicious same-user notification sender could forge the same FDO hints. Post-Apollo scopes express claimed origin metadata, not verified user identity.
- `notify-send` availability within Fedora Silverblue/Flatpak Vesktop is **unverified**. The native helper will fail without broader host access rather than shell out to the host.
- The plugin works on a compatible custom Vencord build, which has not been built or tested in this repository's CI. Source-level and synthetic converter tests are separate from an actual Vesktop build.
- No global interception or replacement of stock desktop notifications. No attempt to suppress/alter Discord's own notifications or reverse-engineer its notification eligibility.
- This is **Discord/Vesktop only**. The BlueFerry, Telegram, and Proton adapters require their separately authorized live event sources, as documented in `docs/notifications/MESSAGING_IDENTITY_BRIDGE.md`.

## Rollback

Turn the Vencord plugin OFF, remove test allowlists, and restore the previous Vesktop `Vencord Location` to disable this source. After user-authorized restart, the plugin cannot emit new events. Existing Post-Apollo saved DND/ZZ/BLOCK policies remain intentionally unchanged and can be cleared in Notifications → Manager.

## Recovery and tests

- `identity.ts`: explicit input allowlist, schema checks, generic `notify-send` argument construction
- `index.ts`: Vencord disabled-by-default Flux subscription, current-account and channel resolution
- `native.ts`: one narrow IPC function, host-execution guard, rate limit, deduplication
- `tests/notifications/test_vesktop_identity_producer.py`: typed FDO hint output through actual Notifications converter
- `.github/workflows/notification-scoped-policy-contracts.yml`: CI source-only check

**No live provider installation or operator acceptance is claimed.**
