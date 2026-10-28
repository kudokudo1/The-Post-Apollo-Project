# Telegram // optional private accounts inside Social

**State:** GitHub review candidate. No local deployment, Telegram login, identity migration, or runtime acceptance has been performed.

## How to use after operator-reviewed merge and safe desktop deployment

1. Open **Social → USER // SETTINGS → LINKED ACCOUNTS → Telegram**.
2. The default is **SHARED TELEGRAM**. It continues to use the existing `$XDG_DATA_HOME/post-apollo/telegram/personal.session` and universal app keys. No identity is assigned ownership of that old session.
3. Select **USE PRIVATE TELEGRAM ACCOUNTS** to opt in *for the current Quickshell run*. The currently saved Social identity selects its own session at `$XDG_DATA_HOME/post-apollo/telegram/identities/identity-N/personal.session`.
4. Choose **OPEN TELEGRAM**, then deliberately pair this identity with Telegram QR or phone, code, and optional 2FA **inside the existing Social pane**. Simply selecting an identity never initiates pairing.
5. Returning to Settings and selecting another saved identity changes the Telegram session scope. Unpaired identities show **SIGN-IN REQUIRED**, not another identity's conversations. Provider status and account nicknames are separate.
6. **USE SHARED TELEGRAM** returns to the legacy session without migrating, copying, deleting or revoking any account. Private mode is intentionally OFF after a Quickshell restart until a separate persistence decision and runtime verification.

## Credential versus account boundary

Universal application `apiId`/`apiHash` belong to the Post-Apollo application and are shared by default:
`$XDG_CONFIG_HOME/post-apollo/telegram/client.json`.

An optional full per-identity *application* key pair may be configured at
`$XDG_CONFIG_HOME/post-apollo/telegram/identities/identity-N/client.json`.
It is not a Telegram login and does not prove an account is linked. Invalid or unsafe scoped overrides fail closed. API hashes, phone codes, passwords and QR tokens are never placed into process command arguments or GitHub.

The Telegram provider issues API keys externally. This feature does not automate Telegram developer registration. A privately provisioned universal app pair means normal account owners can complete all subsequent Telegram pairing inside Social.

## Implementation boundaries

- `MessagingW.qml` owns the operator-controlled **Shared / Private** mode, using only the confirmed persisted active Social identity. No new Social window.
- `SocialMessageRouter.qml` passes that scope to the Telegram adapter, and scopes conversation composer drafts and send-success acknowledgements by `telegram@identity-N` rather than treating matching conversation IDs as the same chat.
- `TelegramAdapter.qml` adds `--identity identity-N` only when private mode is active, to **health, list, messages, send, QR and phone** commands. The original commands with no scope retain shared behavior. Switching scope resets old conversations and login input, increments read generations, and ignores stale send acknowledgements.
- `bridge.py health --identity identity-N` returns `AUTH_REQUIRED` **without creating an empty private session** for an unpaired identity. Only deliberate pairing creates a new private session and permissions remain owner-only.
- Identity switching controls are disabled while Telegram login/send or key-status checks are in progress. Real provider send submission may already be in flight; do not force scope changes through another process during a send.

## Verification and remaining gates

Offline tests exercise scope routing and the status formatter, session path separation, fake-Telethon explicit login and passive health, stale-result safeguards, no secret output and preservation of the legacy shared route. The tests do **not** authenticate a real Telegram account or execute Quickshell.

**Live acceptance required:** default shared account unchanged; private identity-1 unpaired shows no messages; pair a test identity deliberately; switch to identity-2 and back without cross-account contacts/drafts; try switching while login/send is in progress; confirm persistence within the running widget, no cross-account send acknowledgment and safe restart. Test on a controlled account or Saved Messages and never upload session files or QR codes.

**Rollback:** in Social Settings select **USE SHARED TELEGRAM**. This changes only current runtime routing, not session files. If a repository rollback is later approved, revert this bounded PR; do not remove or copy any Telegram private session as part of routine rollback.

**Open work:** finished provider account identity switching for Discord, Sessions and other desktop apps; Account Manager orchestration; restart-safe persistence (opt-in only); real Quickshell/Sway acceptance. This is a Hospital-compatible external report, not registration to a live Room or Session.
