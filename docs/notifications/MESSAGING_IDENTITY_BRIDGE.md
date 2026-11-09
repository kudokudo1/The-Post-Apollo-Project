# Notification identity scopes // Provider handoff

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Scope:** Notifications-owned identity policy and metadata translation  
**Live activation:** NOT authorized or implemented by this contract alone  
**Status:** Draft PR #1684, operator acceptance pending

## Existing runtime path

Freedesktop notification → `NotificationsConverter.qml` → `NotificationScopePolicy.scopeFromHints` → `NotificationsService.appendNotification` (BLOCK gate first) → popup/history → Notifications Hub scope selector.

The runtime accepts optional producer-supplied string hints. Missing IDs do **not** become guessed identities. These names are not standardized freedesktop fields; a producer or companion must explicitly emit them:

| Producer-owned hint | Meaning |
| --- | --- |
| `x-post-apollo-account-id` | Stable local ID for the receiving provider account |
| `x-post-apollo-account-name` | Display only, not an identity key |
| `x-post-apollo-contact-id` / `x-post-apollo-contact-name` | Contact/person reference (uses existing SENDER policy kind) |
| `x-post-apollo-sender-id` / `x-post-apollo-sender-name` | Explicit message author identity |
| `x-post-apollo-conversation-id` / `x-post-apollo-conversation-name` | Provider conversation |
| `x-post-apollo-conversation-type` | `direct`, `group`, `thread`, `channel`; missing type displays CHAT rather than making a false DM claim |
| `x-post-apollo-group-id` / `x-post-apollo-group-name` | Group conversation ID |
| `x-post-apollo-thread-id` / `x-post-apollo-thread-name` | Email/forum thread identity |
| `x-post-apollo-server-id` / `x-post-apollo-server-name` | Discord-style server identity |
| `x-post-apollo-channel-id` / `x-post-apollo-channel-name` | Channel identity within server |

Only explicit stable IDs produce the corresponding scope. Display names and bodies never manufacture IDs. IDs are app-namespaced and, when the producer supplies an account, also account-qualified. The existing app-wide rule still applies; old scoped keys without account IDs continue to work for older notifications without new metadata. The settings store remains `notification-policies.json` (plus independent Favorites). BLOCK rejects new history and popups, DND/ZZ suppress popups but retain history.

## Provider mapping, without activation

`services/notifications/NotificationMessagingIdentity.js` is a **pure translation helper**, not a live listener. No provider notifications are generated from previously read snapshots.

- **Discord/Vesktop:** `discordScope({accountId, guildId, channelId, dmId, groupDmId, userId, ...})` accepts explicit native IDs. Ordinary desktop notifications may not include them. To finish, a separately reviewed, opt-in Vesktop/Discord producer must supply IDs from an authorized event source and deliver them through an approved local boundary. Do not parse UI titles, harvest tokens or scrape message bodies.
- **BlueFerry:** `blueFerryScope(conversation, message, profileId)` consumes the existing approved read-only projection's `serviceId:blueferry`, `type:direct|group`, `conversationId`, `senderId` (when present), and profile ID. This does not turn a cached phone snapshot into a live event. Social PHONE owns delivery permission, current device/profile binding and any future live subscription. Direct chats without provider sender identity have a conversation rule, not a fabricated contact ID.
- **Telegram:** `telegramScope(dialog, message, accountId)` uses the existing Telegram bridge's `private|group|channel` dialog types and `conversationId`. A private dialog's ID identifies its peer; a group message from the present bridge does not include a member's sender ID. The current adapter has `liveUpdates:false` and does not deliver live events into Notifications.
- **Email / Proton:** `emailScope({accountId,senderAddress,threadId,...})` requires an authorized mailbox event carrying account and message/thread binding. The current Proton browser pilot is count/presence-only and explicitly cannot establish sender or message identity. Do not attach an email address or thread based only on a native notification title or browser site.
- **Other providers:** Supply the same stable, typed fields through a separately authorized adapter. The notification policy does not need one special-case rule system per app.

## Required provider-ownership handoff before live hookup

1. **Owner and authority:** Confirm the Social PHONE, Telegram, email or Vesktop producer worker and permitted API. Do not write live data to the Notifications bridge without an approved host boundary.
2. **Identity and account binding:** Resolve native conversation/contact/thread IDs within the current authorized account/device and reject changed sessions or revoked permissions. Strings supplied by a caller are metadata assertions, not an authentication proof.
3. **Live event versus historical read:** Emit only a new, authorized notification occurrence. Reading a snapshot, test fixture or message history cannot generate surprise popups.
4. **Privacy:** No message body, token, phonebook, credential, email header or profile is logged by the pure normalization functions. Do not introduce background scraping or unauthorized provider polling.
5. **Verification:** Demonstrate two different conversations, two accounts with the same sender ID, sender mute versus group mute, and one email thread versus another. Test DND, ZZ, Favorites and ✞ BLOCK (including absence from history) and actual Quickshell popup behavior.
6. **Operator acceptance:** Native producer integration remains a separate live checkpoint. Do not label this contract as having connected a user account.

## Recovery pointers

- Source: `services/notifications/NotificationScopePolicy.js`, `NotificationsConverter.qml`, `NotificationsService.qml`, `NotificationMessagingIdentity.js`
- UI: `widgets/notifications/NotificationsHubW.qml`
- Tests: `tests/notifications/test_notification_messaging_identity.py`, plus prior scoped-policy and hard-block regressions
- CI: `.github/workflows/notification-scoped-policy-contracts.yml`
- No local machine writes or activation, no change to existing BlueFerry/Telegram/Proton transport files.
