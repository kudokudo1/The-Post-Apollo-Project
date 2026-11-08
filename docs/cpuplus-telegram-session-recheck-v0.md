# CPU++ // Telegram native session status and explicit recheck

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // CPU++ Connected Accounts / Telegram  
ASSIGNMENT // Display the actual Social-owned Telegram native adapter status and recheck that same adapter from CPU++, without credentials or session writes  
STAFF ROLE // unassigned, external Hospital-compatible worker, live registration unverified  
PROVIDER // OPEN AI // CHATGPT  
BASE // 41d47a7d6775389d3908efa74842807c02abfdb9  
PERMISSIONS // Bounded GitHub review branch: CPU++ read-only status, fixed relay, Social owner recheck, tests/workflow/docs. No local workstation, provider login/logout, session deletion, keyring, production trusted-host changes, automatic merge, or permission activation.

## IMPLEMENTATION

The operator confirmed that the existing **OPEN TELEGRAM** navigation in CPU++ works on Fedora. PR #1522 is merged. Local account-name editing remains in **both** CPU++ ID MANAGEMENT and SETTINGS → CONNECTIONS → SOCIAL // IDENTITIES, with exactly one existing Social store.

This follow-up adds **real read-only native provider health presentation** to CPU++ and an explicit **RECHECK SESSION** action when Social already has Telegram as the selected active native adapter.

- `MessagingW.qml` exposes a tightly bounded read-only `telegramConnectionObservation` containing only the real Social adapter's selected/active booleans, limited backend status enum, shared/private scope mode and matching boolean, and in-progress flags. It never passes raw backend details, identity labels/IDs, codes, passwords, API keys, tokens or SQLite paths into CPU++.
- `ConnectionsTelegramStatusPolicy.js` projects only exact `READY` from the selected active adapter with **correct scope** as `PROVIDER AUTHORIZED AT LAST CHECK`. A stored label, stale adapter selection, unknown error string, previous private ID after a switch, old private READY shown as shared, pairing, or in-flight operation never becomes current authority. This is **last-check UI evidence, not a real-time grant**.
- `CpuPlusSettingsConnectionsDetailsPane.qml` shows this read-only status and current scope under **TELEGRAM // NATIVE** in the existing right bay. **OPEN TELEGRAM** remains. **RECHECK SESSION** appears only while the native adapter is selected, active, in the correct scope, not pairing, not sending/configuring and not already probing.
- CPU++ signals a fixed recheck intent through existing `shell.qml` to `MessagingW.recheckTelegramFromConnections()`. The Social owner **revalidates the same guards** at invocation and calls its existing `TelegramAdapter.probe()`. The adapter launches its original health command which uses Telethon `is_user_authorized()`. No second Telegram client, new status process, login, logout, session migration, cross-ID switch, credential action, or General Connections broker permission is added.

## HOW TO USE

After authorized merge and separate deployment: CPU++ → SETTINGS → CONNECTIONS → middle TELEGRAM // NATIVE.

The right bay displays **NATIVE SESSION // SHARED SESSION** or **PRIVATE SESSION**, plus actual Social adapter last-check status. When the native Telegram adapter is not active, it reads **NOT CHECKED IN SOCIAL** and presents OPEN TELEGRAM. Select **OPEN TELEGRAM** to open the existing Social Telegram panel and its authorization check/QR-phone pairing tools. Once Telegram is already the active native adapter and not busy, **RECHECK SESSION** becomes available directly in CPU++ and triggers the same provider-owned health probe. A READY state does not guarantee the session remains valid in the future.

This does **not** perform provider logout or account switching. Shared/private selection continues to live in Social Settings; switching scope invalidates mismatched status before any recheck.

## VERIFY

Tests in `tests/cpuplus/test_cpuplus_telegram_status_projection.cjs` cover all success/refusal transitions: null or inactive source, malformed/unknown backend mode, forged READY from inactive view, wrong private identity, private→shared scope mismatch, pairing, sending/key-status busy, probing, valid native shared/private READY, no untrusted raw detail and exact owner relay. The updated dedicated CI reuses original native Telegram login, identity-scope, account-label, C1 Connections, C2a broker denial and QML syntax checks. Exact-head CI status to be recorded on the PR. Native Fedora read-only display/recheck acceptance is **not** proven by GitHub tests.

## WATCH OUT FOR

This is **status + explicit health recheck**, not real host-backed Disconnect/Reconnect. Existing Social can deliberately start QR/phone sign-in, but no protected production Connections host currently attests callers/consent and authorizes a scoped remote Telegram `log_out()` or local session revocation. Calling Telethon `disconnect()` merely closes a network connection; it is *not* a reliable sign-out. Deleting a session database may lose local access without revoking Telegram authorization. Neither operation should be exposed as a misleading action in CPU++.

The separate Connections C4b PR #1521 owns the Silverblue protected *fake status host* CI and is not changed. A green C4b test would still not authorize production credential revocation.

## CHECKLIST

- [x] Confirm PR #1522 merged and user-verified navigation, account editing preserved in both menus
- [x] Inspect current GitHub head, Social adapter/bridge and competing Connections PR ownership
- [x] Add true selected-native-adapter status projection with scope mismatch/unknown-state refusal
- [x] Add explicit recheck through sole Telegram owner with invocation-time checks
- [x] Keep all login/logout/provider credential and shared broker trust flags unchanged
- [x] Add focused regression and extend existing Telegram CI workflow
- [ ] Verify exact-head CI and resolve failures
- [ ] Operator merge/deploy and native Fedora UX verification
- [ ] Coordinate separate protected host, real identity/consent, revocable provider-specific logout, renewal, and restart evidence
- [ ] Consent-queued CONNECT ALL, only after trusted individual provider actions exist

## NEXT

**Secure Telegram Disconnect/Reconnect contract:** coordinate with Connections C4b/C5a owner to define an independently verified production host, scoped session owner, consent receipt, fresh authorization observation and a separate distinction between (a) ending the current API connection, (b) revoking the Telegram device authorization, and (c) removing a local session. Before implementing an irreversible provider action, require two-stage explicit confirmation, correct shared/private identity scope, in-flight send/login exclusion, post-operation Telegram confirmation, refusal/recovery paths, and native acceptance. Keep the real provider-side mutation in the service-owned host rather than generic QML.

## DECISIONS

Keep both account-name editor locations. No auto-sign-in, automatic reconnection, forced logout, token/session copying, fabricated READY, account deletion, new writer, production credential grant, host deployment, local machine mutation or PR merge. GitHub is technical source truth; operator retains final acceptance. Recovery: this report, the PR, and `tests/cpuplus/test_cpuplus_telegram_status_projection.cjs`.
