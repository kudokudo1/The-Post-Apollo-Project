# Social Telegram application setup inside the widget

**Scope:** The existing Telegram connection panel and Settings workspace. This document covers **application credentials**, not provider credential issuance. Per-identity session routing is documented separately in [TELEGRAM-IDENTITY-SCOPES.md](./TELEGRAM-IDENTITY-SCOPES.md).

## User experience

In the existing Social widget:

1. Open **USER // SETTINGS → LINKED ACCOUNTS → Telegram**.
2. Choose **CONFIGURE UNIVERSAL API KEYS** to save one Post-Apollo installation-wide app pair, or **OPTIONAL IDENTITY API KEYS** to save a complete override for the selected saved identity.
3. The same Telegram connection pane appears within Social's chat area, with masked API hash input, an explicit **CHECK API CONFIGURATION** action, and **SAVE APP KEYS**. No terminal or separate settings program is involved.
4. Key status reports only `UNIVERSAL APP KEYS CONFIGURED`, `IDENTITY OVERRIDE CONFIGURED`, or `APP KEYS MISSING OR INVALID`. No application secret or API ID is printed in status output.
5. After universal keys are saved, the existing backend automatically continues to the established **QR / phone / code / two-step** Telegram login experience inside Social. An identity override is **configuration only** and MUST NOT start the shared native Telegram login. It becomes effective for that identity only when the separately opted-in private account is selected and paired.
6. **BACK TO TELEGRAM** returns to the existing chat/connection pane. Any unsaved API-key input is cleared when the panel closes, the editor mode changes, or the targeted identity changes.

The existing **APP_REQUIRED** first-run path still uses the same API ID/hash form and private stdin-only login helper. Existing browser-backed service indices and the Social floating-window layout are unchanged.

## Telegram-controlled registration boundary

Telegram developer application creation requires signing in to its official **my.telegram.org → API development tools** and submitting Telegram's application registration form. Post-Apollo cannot mint an API ID/hash itself or claim to have authenticated the developer portal.

We investigated embedding that page directly into the Quickshell QML process, but Qt's WebEngineView requires process-level initialization and a known Quickshell upstream issue (#298) reports a hard crash simply from using WebEngineView. **Do not import or instantiate QtWebEngine inside Quickshell as a shortcut.** This PR therefore does NOT claim to display Telegram's developer portal inside Social, automate its website login, scrape keys, or avoid Telegram's own account verification step.

For a fully self-contained end-user flow, an authorized Post-Apollo deployment can provision the official registered application keys **once**, privately, as the universal app configuration. Then regular account holders never need the developer portal: QR/phone login and all account interactions already happen inside Social. Do **not** hardcode/commit the API hash in a public repository or expose it to chat logs. A separately reviewed, isolated browser process docked into the Social window may support *optional* developer registration later; it needs geometry, security and actual desktop acceptance first.

## Technical implementation and rollback

- `TelegramConnectPanel.qml` reuses the existing credential inputs even after a Telegram account is READY; universal and profile-key editor modes are explicit and the API hash is masked.
- `TelegramAdapter.qml` passes `--identity identity-N` to `login_ui.py configure` only for scoped overrides, through the existing stdin credential channel. **Health/list/messages/send/pairing remain shared by default**. Only the explicit private-account toggle scopes them to a saved identity; scoped app-key configuration alone never starts QR pairing.
- `login_ui.py status [--identity identity-N]` is read-only: it checks the existing private configuration source, reports only scope/configured status and never initializes Telethon or touches a session. Invalid/unreadable credentials fail closed.
- `MessagingW.qml` and `AppSelector.qml` add two Settings entry points, route to the existing Telegram pane, and invalidate the UI when identity changes. No new floating window, browser, provider process, credential store or automatic session migration.
- The new synthetic tests cover universal setup, inherited config, profile override, private file permissions, unreadable/corrupt keys, no Telegram session creation, no secret stdout, UI wiring, and old shared command compatibility.

No user files were changed while preparing this GitHub PR. Any deployment, Quickshell reload or live provider interaction needs operator approval. On rollback, do not merge the PR (or revert the source changes). Existing `client.json` and `personal.session` continue to be used exactly as before.

**Next gate:** An independently reviewed **Telegram developer portal viewer hosted in a separate process** (only if reliable focus/keyboard/privacy integration can be established), plus opt-in per-identity session runtime acceptance. Hospital-compatible external GitHub draft; no registered Room/Session.
