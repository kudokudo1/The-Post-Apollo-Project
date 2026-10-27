# Telegram // universal application keys and isolated identity sessions

**Phase:** Backend foundation only, pending operator approval and UI integration. No Telegram account has been migrated, logged in, activated or switched.

## Key distinction

A Telegram `apiId` and `apiHash` identify an application, not a Telegram account. The existing Post-Apollo **Telegram Connect** wizard already supports one private local universal configuration:

- `$XDG_CONFIG_HOME/post-apollo/telegram/client.json` (legacy universal application keys)

The existing single shared authorization session remains:

- `$XDG_DATA_HOME/post-apollo/telegram/personal.session`

Those existing paths and default Telegram adapter commands remain unchanged.

## Optional isolated identity namespace

This PR adds an opt-in CLI/backend `--identity identity-N` scope to both `bridge.py` and `login_ui.py`. Each explicitly selected saved-style identity has:

- Session: `$XDG_DATA_HOME/post-apollo/telegram/identities/identity-N/personal.session`
- Optional full API credential override: `$XDG_CONFIG_HOME/post-apollo/telegram/identities/identity-N/client.json`

An identity **without** an override inherits the universal API ID/hash (the existing environment/config preference). A valid identity override takes precedence as a complete pair; invalid or unsafe overrides fail closed and cannot fall back into another application's credentials. The API hash is never printed, included in process arguments, written to identity layout metadata or inferred from the account nickname.

The new config/session locations are created **only** when an explicit scoped command needs them. Newly created identity dirs must be owner-only (0700), existing files private (0600) and symlinks are refused. The existing `personal.session` and any Telegram credentials are never copied, migrated or deleted.

## Example private commands (future approved deployment only)

- Shared health: `python3 services/messaging/bridges/telegram/bridge.py health`
- Scoped health: `python3 services/messaging/bridges/telegram/bridge.py health --identity identity-2`
- Scoped phone pairing: `python3 services/messaging/bridges/telegram/login_ui.py phone --identity identity-2` (interactive stdin events handled by a future identity-aware UI)
- Per-identity override: `python3 services/messaging/bridges/telegram/login_ui.py configure --identity identity-2` (stdin JSON secret fields only, never place keys in shell argv).

These are a backend contract, **not** a recommendation to run live login commands or paste secrets into a terminal. The current Quickshell Telegram adapter intentionally continues using the shared session until a separate change wires a confirmed saved identity, pairing UI, conversation cache isolation, and all async result guards together.

## Verification and safety gates

The new synthetic tests exercise distinct session paths with a fake Telethon provider, universal fallback, override precedence, private files, profile-specific sign-in, no secret output, invalid IDs, refusal of symlinked or insecure files, and preservation of default shared QML commands. Existing Telegram bridge/QR/login/adapter suites continue running.

The next PR should add an explicit **Shared / Per-Identity Telegram** choice to the Settings and login wizard, and pass the confirmed saved identity to every Telegram health/list/messages/send/login call while resetting old conversations and rejecting delayed results on switch. The mode must default to the existing shared session, without assigning its ownership to identity-1. Only after live Quickshell/provider tests and operator acceptance should it be enabled.

**Rollback:** ignore or revert this PR. Existing shared session and universal credentials stay in their original paths. This branch contains no local deployment and no live Hospital assignment/room.
