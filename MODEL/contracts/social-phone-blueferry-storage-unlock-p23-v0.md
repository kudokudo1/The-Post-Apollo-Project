# Social PHONE P23 // BlueFerry encrypted storage unlock in existing PHONE UI

> **STATUS:** GitHub-only source change, awaiting exact-head CI, review, separate approved deployment and real Fedora verification. NOT a live wallet change or production grant.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM:** Social PHONE // local data availability and UI control, P23 continuation. **ASSIGNMENT:** Read BlueFerry local storage state, surface an explicit one-click unlock within PHONE, retry permitted reads; do not alter pairing, media, contacts/chats sidebar or identity grants. **PROVIDER:** OPEN AI // CHATGPT, external Hospital-compatible; no verified live Hospital Room/Assignment/Staff registration. **BASE:** fresh main `e66a8c4b59dde64bd81502fd2fcff58e5c69ae71` at preflight on 2026-11-07. A separate open PR #1447 owned CPU++ ID Management and does not overlap PHONE files.

## IMPLEMENTATION

**Actual evidence:** User's native `blueferry-tui` screenshot showed `STORAGE LOCKED` despite iPhone connected and MAP/PBAP sessions reported ON, with an empty conversations list. User executed `blueferry storage-unlock` and received `{"storage_policy":"encrypted","storage_state":"ready","storage_detail":"Local data is encrypted with the desktop keyring"}`. That establishes the native BlueFerry local history cache **was locked and the unlock command returned READY**; it does **not yet prove** that conversation history or contacts then populated.

P23 reuses BlueFerry's **existing** `UnlockStorage` D-Bus operation without inventing a new encryption/keyring facility:

- `services/phone/PhoneBlueFerryStorageUi.py` provides only `--status` and **explicit** `--unlock` against an already-running BlueFerry daemon. It reuses the P18c unique-owner-bound D-Bus transport, checks API v2 and `storage_policy/storage_state`, and emits strictly bounded public enums (`READY`, `LOCKED`, `NO_RETENTION`, `UNAVAILABLE`, `PROVIDER_UNAVAILABLE`, `UNLOCK_FAILED`), not wallet secrets, stored messages, contacts, raw D-Bus error strings or device identities. It never calls `SetStoragePolicy`, `ResetStorage`, `ClearHistory`, pairs, sends, installs, or changes audio. The only mutating call is BlueFerry's provider-owned, user-requested `UnlockStorage`; it may present the normal desktop wallet prompt. `--status` never unlocks.
- `widgets/messanger/PhonePane.qml` displays **BLUEFERRY LOCAL DATA // LOCKED/READY** under existing DEVICE details; `UNLOCK LOCAL DATA` button only appears for locked/failed local data. In existing MESSAGES/CONTACTS toolbar, the regular REFRESH button becomes **UNLOCK DATA** while storage is locked; no new menu window or sidebar/contact-label change. The status strip explains that notifications can still arrive while saved history is locked. After successful explicit unlock, the existing P21 saved Personal read permission is reused to request a fresh snapshot in the current approved tab. A successful wallet unlock does **not** grant Social permission, enable sends, or grant LLC/nonprofit access.
- PHONE checks BlueFerry storage metadata on open and every 12.5 seconds while visible, **without an unlock side effect**. It avoids executing unlock twice and checks the pinned daemon owner both before and after the operation. If storage becomes locked or unavailable, the UI invalidates in-flight Personal reads and clears the displayed adapter snapshot, rather than letting stale replies repopulate the view. It does not change the window size, existing Social Contacts label, current Bluetooth pairing, iPhone media route or oFono/HFP calling setup.
- READY is separate from populated data. BlueFerry may still return **zero threads**, and contacts may still report an unavailable cache epoch/card count. P23 does not fabricate history or silently invoke `contacts-sync` because that is a separate device operation and has its own permission/side effects.

**Why not auto-unlock at every PHONE open?** BlueFerry already supports passive keyring retry when the desktop keyring is unlocked. Automatically presenting a wallet password prompt on every Social open is surprising and crosses the user's consent boundary. P23 auto-checks, and when the wallet is still locked supplies a visible **one-click** unlock inside PHONE. For truly prompt-free sessions, the desktop wallet needs to be unlocked via the user's approved desktop login mechanism; no local OS configuration was altered in this PR.

## HOW TO USE

**Now on the user's machine:** `blueferry storage-unlock` has already reported storage READY. Check `blueferry-tui` again; the storage pill should read READY/UNLOCKED. Inspect whether any conversations appear, then press Shift+C for contacts. Do not re-pair or reset history.

**After operator-approved merge and separately approved Post-Apollo Fedora update:** In Social → PHONE → MESSAGES/CONTACTS, a locked BlueFerry wallet displays `UNLOCK DATA` in place of the REFRESH control. Click it. If the desktop keyring asks to unlock, approve its own password prompt; Post-Apollo does not capture or store that password. PHONE then retries the current data read *only if previously approved* under P21 Personal read permission. The DEVICE tab also has **UNLOCK LOCAL DATA** and an independent storage-state display. On later visits when the desktop wallet is already open, normal refresh proceeds without an extra prompt.

## VERIFY

- `tests/phone/test_phone_blueferry_storage_ui.py` tests the exact source with synthetic D-Bus interfaces, `dbus.String`-compatible replies, status-only no-unlock, explicit locked-to-ready transition, no repeated unlocking when ready, distinct plaintext/no-retention behavior, no active daemon, invalid API/status, unique-owner change, malformed payloads and failure text scrubbing.
- `tests/messaging/test_social_phone_storage_unlock_ui.py` checks the existing PHONE widget controls, storage-specific status, QML on-click binding, refresh-after-success, no automatic unlock at menu open, no send or destructive storage calls, and preserving Social's existing message/contact UI.
- Existing full PHONE workflow tracks the new source/test/handoff and runs both suites plus previous P18–P22, Social contact/messaging UI and audio/call setup regressions.
- **No physical Fedora wallet, iPhone, Quickshell render or real private contacts/messages were read by these tests.** Successful CI must not be presented as live user acceptance.

## WATCH OUT FOR

1. `storage_state=READY` means the encrypted BlueFerry local database can be opened, **not** that it contains old iPhone messages/contacts. Existing notifications do not prove historical MAP/PBAP cache population. After unlock, observe the native client first and keep Social read/error diagnosis separate.
2. The desktop login/Keyring/Wallet mechanism is OS-owned. Post-Apollo must not silently set persistent keyrings, change storage modes to plaintext, reset history, clear data or cache wallet passwords. A keyring prompt initiated by a deliberate user click is BlueFerry's responsibility.
3. The Personal approval record under P21 is only an owner-scoped local preference and does not authenticate another same-UID application, business account, verified device line, or production Identity Center grant. Unlocking shared BlueFerry retained data could make it accessible to other same-UID clients; the widget explains the scope and does not assert enterprise security.
4. If the installed BlueFerry daemon does not expose `UnlockStorage`, the action returns `UNLOCK_FAILED` safely; no guessed replacement, service restart or re-pair operation is attempted.

## CHECKLIST

- [x] Verify user's actual `STORAGE LOCKED` TUI screenshot and exact successful `storage-unlock` response.
- [x] Recheck main, active owners/PRs, Syntagma AGENTS/Hospital/working rules and current PHONE/BlueFerry source.
- [x] Reuse upstream `GetStatus` and explicit `UnlockStorage` in a bounded metadata-only service helper.
- [x] Integrate DEVICE status and one-click conditional unlock into existing PHONE bar; do not alter Contacts label or window layout.
- [x] Keep wallet password in the desktop keyring, no auto prompt, no pairing or audio change.
- [x] Add synthetic backend/GUI contract tests and PHONE CI routing.
- [ ] Exact-head CI passes and owner/operator source review.
- [ ] Operator-approved merge and separate Fedora deployment.
- [ ] Native `blueferry-tui` READY + messages/contacts validation and current PHONE unlock/refresh/exit/revoke interaction.
- [ ] Independently resolve missing history/contact cache, audio-route direction labeling and oFono calling after provider facts are confirmed.
- [ ] Production app/organization-specific Identity Center/Account Broker permission service.

## NEXT

Validate the specific native state now: **in `blueferry-tui`, check if `STORAGE READY` appears and whether any conversations exist; then Shift+C for contacts.** If native lists remain empty, investigate non-destructively the BlueFerry backend's history policy/catch-up and explicit contact sync only after separate user approval; do not claim this widget unlock patch fixed the missing datasets.

Once the patch is merged and locally installed with authorization, test its user-visible error states, wallet unlock prompt and retry against the actual Fedora keyring, and verify no disruption to iPhone Bluetooth audio, Messages MAP, Contacts PBAP or Calls HFP paths.

## DECISIONS

Bounded GitHub-only implementation for an **in-widget, one-click explicit unlock** fallback, not a new desktop autostart/background keyring service. No local filesystem writes, wallet mutation, PR merge, Bluetooth changes or production activation in this browser session. Operator retains acceptance and deployment authority. Rollback: close the draft PR or revert its single bounded commit if merged.
