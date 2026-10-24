# Telegram personal-account bridge // Work package A

**State:** independent adapter candidate; no shared router hookup, no live account test.

The bridge uses Telegram's documented MTProto client API through community-maintained **Telethon 1.x**, not the Bot API. It supports personal-account conversations, text history, and text sends. The Quickshell adapter exposes the v1.0 common fields and disables network polling unless selected. Real account authentication is never attempted by the GUI.

## Explicit one-time operator setup (after separate desktop activation approval)

1. Install the Telethon 1.x Python package into the Python interpreter used by `TelegramAdapter.qml`. It currently defaults to `/usr/bin/python3`; change only the adapter's `pythonPath` if necessary.
2. Create your own Telegram application credentials at <https://my.telegram.org/>. Set `POST_APOLLO_TELEGRAM_API_ID` and `POST_APOLLO_TELEGRAM_API_HASH` **in your own private process environment**. Never paste them into a PR or chat, store them in Git, or expose them in shell history. Avoid logging environment dumps.
3. Run `python3 services/messaging/bridges/telegram/bridge.py login` deliberately in an interactive terminal to pair your personal account. Do not automate or repeatedly attempt login.
4. The persistent Telethon session file will be stored at `${XDG_DATA_HOME:-$HOME/.local/share}/post-apollo/telegram/personal.session`, in a private directory. It is a sensitive credential and must not be uploaded/shared. Log out or revoke the Telegram session in Telegram's device controls when needed.
5. With the *same interpreter and environment* used by Quickshell, `python3 services/messaging/bridges/telegram/bridge.py health` returns `READY` or a truthful unavailable/auth-needed state. Activation within Social requires the **separate shared-router assignment**.

Supported bridge commands: `health`, `login`, `list`, `messages <conversation_id> [--limit 100]`, and `send <conversation_id>` (receives one newline-terminated JSON object with `text` on stdin). Send success means Telegram returned a message ID, **not** that the recipient read it.

## Known limits and open integration questions

- Native Telegram dates are converted to *Unix seconds* here. Universal timestamp units are not yet frozen in shared contract v1.0; the integration owner must finalize the common representation before cross-service sorting.
- The adapter's capability property uses **provisional service-local key names**. Do not copy these as canonical global keys until the integration owner freezes the schema.
- This implementation polls conversations every 7 seconds and selected history every 4 seconds while active. A push subscription or persistent connection may be more efficient later.
- Text-only; attachments, reactions, calls, voice messages and Telegram secret-chat support are **not** claimed. Some channel/group conversations may be read-only; a failed send leaves the composer text intact.
- The bridge opens a short-lived Telethon client per request. Session cache and process concurrency require **live runtime verification** before acceptance.
- No account credentials or provider network are used in offline contract tests.
