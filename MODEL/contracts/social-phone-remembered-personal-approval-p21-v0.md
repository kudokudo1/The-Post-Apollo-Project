# Social PHONE P21 // Remembered Personal permission and visible read outcomes

> **STATUS:** GitHub-only **draft source change**, awaiting CI/operator review and separately authorized Fedora rollout. Not yet running on the user's desktop.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM:** Social PHONE read-only Personal experience, P21. **ASSIGNMENT:** Replace ten-minute terminal approval dependency with a remembered Personal-device read preference, fix LOAD PERSONAL silent failures, retain existing Social components and safety boundaries. **PROVIDER:** OPEN AI // CHATGPT, Hospital-compatible external DOC-like worker, no verified registered Room/Session/Staff Role. **BASE:** freshly verified `main` `6bad4d8038ebce755ba02a1e9fc9ced67d6b800a`; PR #1401 merged, no open conflicting PHONE/Identity PR at preflight (2026-11-06).

## IMPLEMENTATION

**Why this was broken:** Merged P19 `PhonePane.qml` ran `PhonePersonalReadPilot.py --client messages.read|contacts.read` when LOAD PERSONAL was pressed. That script required an actively running `--serve` terminal with explicit typed approval and ended the session after 600 seconds. Without the temporary socket, the command returned `NOT_ACTIVE`. The UI showed little/no immediately visible status and expected a separate terminal every time. This was a source-level UX fault, not evidence the user's notifications were broken. PR #1401's D-Bus `dbus.String` read fix is already merged. The user's screenshots show BlueFerry notification events and MAP/PBAP sessions reported active, **not** an authorized or populated historical message/contact snapshot.

**P21** replaces the active PHONE code path with `services/phone/PhoneRememberedRead.py`:
- First **APPROVE READ** opens an **in-PHONE overlay**, not a terminal, with explicit choices to **ALLOW BOTH / REMEMBER**, **MESSAGES ONLY / REMEMBER**, **CONTACTS ONLY / REMEMBER** or **NOT NOW**. None of these are preapproved. Consent is requested by clicking a visible button. The UI labels the trust model explicitly.
- The user-private, owner-only JSON preference at `$XDG_STATE_HOME/post-apollo/social-phone-personal-read.json` (default `~/.local/state/post-apollo/...`) stores only one **exact opaque BlueFerry profile UUID**, allowed read operations, random correlation token, monotonic epoch and monotonic per-operation sequence; no message bodies, contacts, phone numbers, service passwords or signing credentials. The directory is checked as 0700, file/lock as 0600, no symlink reads, and atomic replace + exclusive lock are used for writes.
- **A one-time saved Personal preference remains until explicitly revoked**, including after closing/reopening PHONE and desktop restarts. The temporary `foot` terminal and ten-minute Unix socket are not needed for the new UI. The previous P19 terminal pilot remains in source as an uncalled compatibility fixture, not auto-started.
- On subsequent PHONE opens or when changing between MESSAGES and CONTACTS, **only if the saved preference exists**, the app checks the current connected BlueFerry profile and makes a one-shot read without asking again. **REFRESH** manually repeats a read. **LOAD PERSONAL** without approval checks if one is already saved; if not, it opens the permission prompt. The button never silently acts like a broken no-op.
- Every read calls the existing bounded P18c `BlueFerryHostReadPort.read_for_trusted_host`, with the real BlueFerry unique owner, matching connected saved BlueZ profile, operation-specific consent, and unchanged P18a projection validation. No unapproved app/organization selectors, send, mark-read, call/FaceTime route, remote contacts write, Bluetooth pairing or direct QML D-Bus access.
- Each successful read advances the persistent epoch and operation sequence **before publishing the snapshot**; after UI close/reopen, earlier callbacks cannot be reused and a fresh read is accepted by P18e `BlueFerryAdapter.qml`. A failed/pinned device/owner/epoch check refuses to publish. A read and **STOP ACCESS** are mutually ordered by the same OS file lock within cooperating code; the UI immediately hides current data and invalidates outstanding process output before revocation completes.
- The existing PHONE list/feed and contact cards remain the only user workspace; `sendEnabled: false` is unchanged. A compact **always-visible** status line above the feed explicitly reports `READING`, `APPROVAL_REQUIRED`, `APPROVED`, `DEVICE_UNAVAILABLE`, `PROVIDER_UNAVAILABLE`, `READ_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `BRIDGE_UNAVAILABLE`, **zero actual records**, or `REVOKE_FAILED` without leaking private content/error strings. An in-panel response appears even if a process fails before printing JSON. A metadata-only preference status check every eight seconds clears the view if the approval or exact connected profile disappears.

**IMPORTANT SECURITY LANGUAGE:** This is a persistent **single-user local preference**, not a browser-origin-specific camera permission, sandboxed application identity, signed account grant, or protection against other Linux programs running with the same UID. A local same-UID program could manipulate the owner-only file or read the already-running BlueFerry D-Bus independently. The action is explicitly one-time user approval for this *Personal Linux account*, not production enterprise access. The old trusted-host architecture contract still needs operator and Identity Center/Account Broker acceptance before claiming organization/customer isolation, durable cross-process grant revocation and renderer-wide purge.

## HOW TO USE

**After operator-approved PR merge and separate Fedora deployment:**
1. Open Social → PHONE → MESSAGES or CONTACTS. If this is the first use, click **APPROVE READ** or **LOAD PERSONAL**. Both lead to the **in-PHONE** choice; **ALLOW BOTH / REMEMBER** saves Messages+Contacts. There is **no separate terminal** and no repeated ten-minute reapproval.
2. On future visits, PHONE recognizes the remembered choice and automatically loads the permitted Personal snapshot for the selected tab. Click **REFRESH** for another one-shot snapshot. No background message monitoring, streaming sync or sending is turned on.
3. **STOP ACCESS** immediately clears the local view and requests deletion of the saved authorization *state* (it records an unapproved tombstone so stale correlation epochs cannot revive). If saving that revoke fails, PHONE must report **REVOKE_FAILED** rather than falsely claim revocation.
4. If PHONE reports a provider error, inspect DEVICE's read-only MAP/PBAP diagnostics. Bluetooth media and notification delivery working does not imply BlueFerry has cached thread history or contact cards. The screenshot's contact cache count was **not reported**.

## VERIFY

- `tests/phone/test_phone_remembered_read.py` uses invented BlueFerry data, temporary owner-only files, actual P18c read port calls and faked device/owner. It tests first approval, persistence/reopen, both/one capability, exact device switch and reconnect, no prior approval, no content persistence, forged org/device/send requests, invalid owner-only file/symlink/shape, revoked tombstone, regrant monotonic epoch, concurrent read/revoke ordering and storage write failure. No physical iPhone or private data accessed.
- `tests/messaging/test_social_phone_personal_read_pilot_ui.py` updated to test the current in-PHONE permission overlay, explicit first approval, automatically reloading **only after saved approval**, visible reason for each read failure, read-only Social list/feed, no standalone terminal or implicit pairing, context invalidation, and full permission revoke warning.
- Existing PHONE CI also tests legacy P19, all BlueFerry adapters, shared Social routing boundary, native pairing, WirePlumber/audio, and oFono call setup. Exact-head CI required before claiming source verified.
- **Not verified:** actual Fedora Quickshell rendered UI, installed BlueFerry API contact-card cache, real iPhone MAP historical SMS, full QML permission lifecycle across desktop restart, and process isolation against same-UID apps.

## WATCH OUT FOR

The user wants a **one-time website/app style approval**. This delivers the visible user experience and remembers their Personal preference but **cannot honestly claim** browser-like OS per-app permission isolation. A real protected Identity Center/Account Broker phone permission service must authenticate the caller/session, store signed capability-scoped grants in an authority inaccessible to untrusted same-UID clients, manage phone/device/line ownership, coordinate revocation across all UI/IPC caches and verify iPhone-side consent. This cross-owner trust boundary remains unassigned, so **do not** silently promote P21 to production organization permission.

Messages are not streamed from notifications. Notification events, MAP cache snapshot and PBAP cards are independent BlueFerry channels. The `READ_UNAVAILABLE` state may still be returned for missing/unsupported provider versions; in screenshot PBAP session is active but the contact count is not reported. Do not fake conversation history or infer that count is zero. Calls, working A2DP, FaceTime, oFono/HFP, and wireless pairing remain untouched.

The Personal read file is a permission **preference**, and deleting it does not revoke iOS system Bluetooth pairing, BlueFerry's own direct D-Bus access or any other same-UID app access. UI clears its own arrays but cannot prove clipboard/screenshot/third-party caches are wiped.

## CHECKLIST

- [x] Verify merged PR #1401, main, no active ownership collision, Syntagma AGENTS/Hospital/working rules.
- [x] Diagnose silent LOAD as ten-minute terminal/socket dependency and poor status display.
- [x] Add bounded remembered per-profile operation preference and one-shot read, no private data persistence.
- [x] Add in-PHONE first approval choices, auto-load for **already saved** permission only, REFRESH, immediate stop and persistent revoke.
- [x] Add explicit visible status/errors, revoke failure disclosure, old context and switched identity cleanup.
- [x] Add synthetic backend concurrency/security tests, UI source regressions and workflow paths.
- [ ] Exact-head GitHub CI and follow-up fixes.
- [ ] Operator review/merge and separately approved Fedora update.
- [ ] Live iPhone read, contacts, no-data, stale history, disconnect, restart, revoke and Quickshell UI acceptance.
- [ ] Production signed and protected Identity Center/Account Broker grants with actual per-app and organizational boundaries.
- [ ] Separate message sending, notification-driven sync, multiple-device selection and oFono/HFP calling.

## NEXT

Review CI and open bounded draft PR. Once merged and deployed with operator authorization, check PHOTO: click first approval once, return to PHONE several times/restart desktop, confirm saved reads no longer request terminal, verify actual BlueFerry historic thread/contact snapshots and all visible error states. If read remains empty, investigate live iPhone/provider MAP history/PBAP cached count independently of notifications. After that, the production Identity/security owner must settle authenticated cross-process grants before expanding from Personal to LLC/nonprofit identities.

## DECISIONS

Operator's user-experience change authorizes a **repository source implementation** of remembered Personal read and feedback only. No local Fedora write, production activation, merger, system service restart, Bluetooth audio change or silent live permission grant. The operator remains final authority. Rollback by closing draft PR, reverting bounded commit after authorized merge, or selecting **STOP ACCESS** on the deployed app to remove the Personal preference.
