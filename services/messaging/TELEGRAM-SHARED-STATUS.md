# Social Settings // shared Telegram authorization status

**State:** Repository-only implementation proposal. The user-approved layout is preserved. This feature does not add Telegram identity-specific sessions or automatic authentication.

## Why this is separate from browser status

Existing Telegram integration already uses Telethon's supported `is_user_authorized()` inside `services/messaging/bridges/telegram/bridge.py health`, surfaced through `TelegramAdapter.qml backendMode`.

The browser Sway window diagnostic added in PR #863 has no equivalent authorization proof, so browser sessions **must continue to say SIGN-IN UNKNOWN**.

However, Telegram currently uses a **single** `post-apollo/telegram/personal.session` across Post-Apollo identities. A READY health result establishes that Telegram's *shared native account* was authorized at that specific provider check, **not** that the current Post-Apollo organization identity owns it or that every future operation will succeed.

## Controls in the current Settings workspace

Within `Social → USER // SETTINGS → LINKED ACCOUNTS`, select Telegram.

- **TELEGRAM // SHARED SESSION** explains that Post-Apollo identity switching does not switch Telegram accounts.
- **Provider status** is shown only while Telegram's native adapter is currently active. It reports `READY` as **PROVIDER AUTHORIZED AT LAST CHECK // SHARED SESSION**, `AUTH_REQUIRED` as **SIGN-IN REQUIRED**, `APP_REQUIRED` as **APP SETUP REQUIRED**, other failures as unavailable, and `PROBING` as checking. When Telegram is not the active adapter, the UI shows **NOT CHECKED IN THIS VIEW**, even if it was READY earlier. QR/phone pairing in progress is shown separately.
- **OPEN TELEGRAM** closes Settings and switches to the existing Telegram native pane, where the existing health probe and same-pane QR/phone pairing wizard run normally. This is explicit navigation, not an automatic credential exchange.
- **RECHECK SHARED TELEGRAM** is enabled only when the native Telegram adapter is active, has a saved/current Settings identity for context, is not pairing, and is not already probing. It calls the existing adapter's `probe()` and does not introduce another session file, API client, or owner.

No user-specific Telegram session, API hash, QR URL, login code or password is copied, exposed or stored by these controls. Existing account nicknames remain setup notes only.

## Compatibility and verification

No changes to `services/messaging/adapters/TelegramAdapter.qml`, `services/messaging/bridges/telegram/bridge.py`, `login_ui.py`, `SocialMessageRouter.qml`, native Sessions, Discord/Vesktop, browser launcher, identity store or their runtime credentials.

The added Node test executes the actual status formatter against nine synthetic states and checks that legacy status cannot be misrepresented as an identity-specific session. The CI workflow also runs Social workspace, account-details, Telegram and browser regressions.

Green CI proves source contracts and formatting, not a live Telegram authorization result, session migration or desktop acceptance. A Telegram sign-in can expire between checks.

## Next and rollback

This is the last safe shared-session visibility step. **Telegram identity-specific sessions** must be developed separately with explicit session ownership and migration policies, profile isolation, stale-result guards, QR/phone flows and rollback verification. Until that work is reviewed and accepted, identity selection remains *organization only* for Telegram.

Rollback: do not merge this draft PR. No local files or provider accounts are modified by repository work.

Hospital-compatible external contribution, not a registered Hospital Room/Assignment/Session.
