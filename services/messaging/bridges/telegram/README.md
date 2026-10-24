# Telegram personal-account bridge // Work package A

**State:** Adapter and shared router are merged into the repository (PRs #740, #744, #746). **No live Quickshell/Telegram account verification and no desktop activation are certified.**

The bridge uses Telegram's documented MTProto client API through community-maintained **Telethon 1.x**, not the Bot API. It supports personal-account conversations, text history, and text sends. The Quickshell adapter exposes the v1.0 common fields and disables network polling unless selected. Real account authentication is never attempted by the GUI.

## Explicit one-time operator setup (after separate desktop activation approval)

1. Install the Telethon 1.x Python package into the Python interpreter used by `TelegramAdapter.qml`. It currently defaults to `/usr/bin/python3`; change only the adapter's `pythonPath` if necessary.
2. Create your own Telegram application credentials at <https://my.telegram.org/>. Set `POST_APOLLO_TELEGRAM_API_ID` and `POST_APOLLO_TELEGRAM_API_HASH` **in your own private process environment**. Never paste them into a PR or chat, store them in Git, or expose them in shell history. Avoid logging environment dumps.
3. Run `python3 services/messaging/bridges/telegram/bridge.py login` deliberately in an interactive terminal to pair your personal account. Do not automate or repeatedly attempt login.
4. The persistent Telethon session file will be stored at `${XDG_DATA_HOME:-$HOME/.local/share}/post-apollo/telegram/personal.session`, in a private directory. It is a sensitive credential and must not be uploaded/shared. Log out or revoke the Telegram session in Telegram's device controls when needed.
5. With the *same interpreter and environment* used by Quickshell, `python3 services/messaging/bridges/telegram/bridge.py health` returns `READY` or a truthful unavailable/auth-needed state. The router now selects Telegram at Social index 2 **in repository source**; enabling it on the operator desktop remains a separate approval and verification step.

Supported bridge commands: `health`, `login`, `list`, `messages <conversation_id> [--limit 100]`, and `send <conversation_id>` (receives one newline-terminated JSON object with `text` on stdin). Send success means Telegram returned a message ID, **not** that the recipient read it.

## Known limits and open integration questions

- Native Telegram dates are converted to *Unix seconds* here. Universal timestamp units are not yet frozen in shared contract v1.0; the integration owner must finalize the common representation before cross-service sorting.
- The adapter's capability property uses **provisional service-local key names**. Do not copy these as canonical global keys until the integration owner freezes the schema.
- This implementation polls conversations every 7 seconds and selected history every 4 seconds while active. A push subscription or persistent connection may be more efficient later.
- Text-only; attachments, reactions, calls, voice messages and Telegram secret-chat support are **not** claimed. Some channel/group conversations may be read-only; a failed send leaves the composer text intact.
- The bridge opens a short-lived Telethon client per request. Session cache and process concurrency require **live runtime verification** before acceptance.
- No account credentials or provider network are used in offline contract tests.

## Controlled desktop acceptance plan (operator-run only; not yet performed)

**Do not initiate this plan from a ChatGPT/CI environment.** It applies only
after the operator explicitly authorizes a desktop deployment and opts into
Telegram account pairing. No live credentials, session files or message content
should be shared in issues, PRs, test artifacts, terminal capture or chats.

**Before account linking (no Telegram sign-in required):**

1. Inspect the running Post-Apollo version and preserve a known-good rollback
   reference; confirm the Social change is actually deployed, not only merged.
2. Open **Social → Sessions** and verify the existing conversation list,
   selected chat, send composer, window geometry and focus behavior still work.
   If a real send test is needed, use an operator-controlled safe recipient.
3. Choose **Social → Telegram** (index 2). With no API credentials or account
   paired, it must show an explicit `AUTH_REQUIRED` or `UNSUPPORTED` state,
   no fabricated conversations, and no active send control.
4. Switch to a managed-browser Social service and back to Sessions. Existing
   browser/Sway geometry and the original Session path must remain usable.

**After separately approved account setup:**

5. Create Telegram API credentials privately, provision the runtime
   environment securely, and perform deliberate interactive `login` as
   described above. **Do not paste the API hash, verification codes or session
   files into a ChatGPT conversation.**
6. Use the noninteractive `health` probe and expect `READY` only when the
   personal account is authorized. In Social → Telegram, verify that the
   real conversation list and oldest-to-newest text history load. Media,
   secret chats and calling are intentionally outside this test.
7. Send **one plain-text message to your own Saved Messages** using the shared
   composer, verify it reaches Telegram and clears its originating composer
   only *after* provider confirmation. Repeat with a draft left unsent,
   switch conversations and services, and verify the draft is preserved.
8. Check a provider refusal (such as selecting an unsupported/read-only
   destination) leaves the unsent text intact. Test quick selector switches
   while conversation history loads, without accidentally sending anything.
9. Confirm no unsolicited login prompts or repeated backend polling from an
   inactive Telegram adapter. Capture **redacted** log diagnostics only if
   needed. Do not expose account IDs, tokens, contacts or message contents.

**STOP if:** Telegram opens a login prompt by itself, Sessions regresses,
messages from another chat appear under the selected conversation, a rejected
send clears a draft, or credentials appear in logs. Do not certify the runtime.

**Rollback boundary:** Stop testing and return to the previously known-good
Social mode. A repository revert, local package rollback, or Quickshell reload
requires its own operator-authorized action. **Do not delete or share the
Telegram session file as a casual rollback step.** Telegram device session
revocation is handled through the official Telegram application.

## Offline CI scope

`tests/messaging/test_telegram_bridge_cli_contracts.py` launches the actual
bridge script in subprocesses while injecting a fake `telethon` dependency
through a temporary `PYTHONPATH`. It tests `health`, `list`, `messages`,
`send` via stdin, refusal/error states and private mock session permissions.
It never imports the real provider client or opens a network connection.
Passing these tests does **not** prove login, live network transport or Sway
display behavior.

## In-menu Telegram connection (new proposed flow)

The Social menu can now display `TelegramConnectPanel.qml` instead of an
empty conversation pane when Telegram is not yet connected.

1. Select **Social → Telegram → CONNECT WITH QR**. After the operator has
   configured client application keys, the pane presents a rotating QR code.
   Use the **Telegram phone app → Settings → Devices → Link Desktop Device** to
   scan. **The Post-Apollo Social pane stays open**.
2. If QR is unavailable, choose **USE PHONE NUMBER**. Enter the international
   number, then the verification code Telegram sends, and any required
   two-step verification password **inside the same panel**.
3. Upon provider-authorized success, the adapter rechecks `health` and loads
   the real conversation list via the existing router.

**First-time application keys:** Without configured API credentials, selecting
Connect shows an **APP_REQUIRED** panel with API ID and API hash fields.
Telegram requires registering a client at <https://my.telegram.org/> to obtain
these keys. That external registration is an upstream requirement until a
release-approved Post-Apollo client identity is provisioned. Copy keys into
the Social panel once. They are never placed in command-line arguments or
GitHub; the adapter sends them via process stdin and the bridge atomically
stores them at `${XDG_CONFIG_HOME:-$HOME/.config}/post-apollo/telegram/client.json`
with parent mode `0700` and file mode `0600`. The old private process
environment variables take precedence when already configured.

**Dependencies:** The selected `TelegramAdapter.qml` Python interpreter
needs Telethon 1.x for login. QR module generation requires the pure-Python `qrcode` package. The Social pane draws the QR pattern using Qt Quick `Canvas` directly: **Pillow is not required** and no QR image needs to be loaded from a data URL. Without `qrcode`, phone verification remains available. These are application
dependencies, not account credentials; bundling them in Post-Apollo would be
the polished deployment path.

**Safety:** Only direct button interactions initiate the new login subprocess.
Neither the health probe nor selecting another Social mode submits credentials,
prompts for codes or starts new provider authentication. Switching away from
Telegram cancels pending login and clears the QR image. Login codes, app hash,
password, and the QR token are not recorded in stdout/stderr diagnostics, PR
artifacts or the QML console. The QR image itself is an ephemeral authorization
secret, so avoid screenshots while pairing.

**Acceptance status:** The in-menu code is a candidate until operator review,
merge, offline checks, and a separately approved desktop/Telegram live test.
Do not assume a QR image or a mocked success proves Telegram has authorized a
real account. Do not automatically restart Quickshell or alter a live session.

## QR rendering simplification // validation candidate

The QR bridge emits a newline-terminated JSON `QR_READY` event containing
boolean matrix rows encoded as `0`/`1` strings with a standard quiet border.
`TelegramConnectPanel.qml` renders that matrix as crisp black/white squares
on the existing Qt Quick `Canvas`. **No PNG data URI, Pillow image encoder,
QR token URL exposure or intermediate image file is necessary.** The rows
are ephemeral authorization material and must never be copied into debug logs.
This change does not replace real Telegram/Quickshell runtime acceptance.
