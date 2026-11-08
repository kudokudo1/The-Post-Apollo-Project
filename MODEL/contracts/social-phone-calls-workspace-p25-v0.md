# Social PHONE P25 // Real CALLS workspace and provider-owned HFP actions

> **STATE:** GitHub-only draft source implementation; exact-head CI, operator review, separate desktop deployment and real non-emergency test remain. Not live HFP activation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM:** Social PHONE CALLS, P25. **ASSIGNMENT:** Replace blank CALLS placeholder with a real provider-backed Personal call workspace and visible setup readiness, without installing/enabling system HFP or expanding into FaceTime/group services. **WORKER:** OPEN AI // CHATGPT, external Hospital-compatible developer, no verified active Hospital Staff Role/Room/Assignment/Session. **BASE:** `main` `bf53212b93f6a178f14be971b6d6d50384dc1028` (2026-11-08). Concurrent open #1486 owns `DiscordGeometry.py` and its lifecycle test; verified **no file overlap**. Operator final authority remains.

## IMPLEMENTATION

### Present evidence and actual provider
- Contacts now work on operator's deployed BlueFerry **0.9.1** via previous legacy ListContacts compatibility. Seven recently received message conversations exist in Social. BlueFerry does **not** download complete historical/sent iPhone messages over Bluetooth.
- PHONE has a CALLS tab but only a `ChatFeed` placeholder labelled `PHONE CALLS NOT LINKED`; active CALLS1 never appears, and its oFono installer and preference toggles are buried in DEVICE.
- Upstream BlueFerry `Calls1` **does** expose `ListCalls`, `Dial`, `Answer`, `Hangup`, `SwapCalls`, `HoldAndAnswer`, `SendTones`. Its opt-in HFP requires oFono running, a permitted system D-Bus user, WirePlumber's oFono HFP backend, and BlueZ's HFP server plugin not competing. Messages/PBAP/desktop-audio readiness do **not** establish HFP readiness. Calls require explicit enable and a real phone/microphone/speaker test.

### P25 scope
- New `services/phone/PhoneCallWorkspace.py` is an allowlisted, one-shot Personal CALLS bridge. `--status` is read-only and polls only while CALLS is visible. It binds to the **already-running unique BlueFerry D-Bus owner**, validates its exact active version-2 phone profile against a currently connected BlueZ device, checks `calls_enabled/calls_state`, then uses `Calls1.ListCalls` with an exact bounded JSON envelope. The returned in-memory UI model has a bounded list (max 8) of live call IDs, states, directions, contact name where reported or masked last four digits, and a conference **status indicator only**. It does **not** store a call database.
- Explicit `--action` supports `dial`, `answer`, `decline` (one ringing call `Hangup`), `hangup` (one active/held/dialing/alerting call), `tones` for one active call, `swap` only with one active/one held, and `hold-answer` when active+waiting. Call IDs and state are revalidated against the current provider snapshot before action, with owner/profile rechecked after action. No HangupAll, call forward, carrier service codes or automatic answer/dial. **Dialing requires explicit on-screen confirmation** and input validation; the backend retains its stronger emergency-number and per-action rate limits. Post-Apollo doesn't silently change audio, call preference, device, pairing, system services or the phone's line.
- The existing `widgets/messanger/PhonePane.qml` now presents a **CALLS workspace in place**, not a new window: clear readiness/errors, **REFRESH CALLS** and **DEVICE / HFP SETUP**, live call cards with Answer/Decline/Hang Up, explicit dial confirmation, swap/hold-and-answer when available, and active-call tones. Only actual backend-ready actions can run. Call status is refreshed periodically (2.5s) **only while that tab is visible**. A Social identity switch clears personal call data and requires a manual refresh; navigating away also clears the list. No call action is automatically invoked on showing a pane.
- Current MESSAGES sidebar remains **Contacts**, its separate CONTACTS tab remains the phone address book, and the existing QML `ChatFeed` continues to serve messaging. The CALLS workspace replaces the empty message-feed placeholder only in CALLS. Existing DEVICE/oFono installer and audio controls remain unchanged.
- BlueFerry's provider D-Bus sender authorization, not a caller-supplied name or UI identity selector, remains the call-control gate. This is a **local same-UID Personal experience**, NOT an authenticated Identity Center/Account Broker corporate phone grant, secure interprocess session, or proof of complete phone ownership. Any process under the same Linux user may invoke BlueFerry's existing APIs subject to its policy. A dialed number appears briefly in a local process argv during the explicit action and is not otherwise persisted; this still needs protected IPC before production multi-tenant use.

## HOW TO USE

**No local changes have been made. After reviewed merge and separately approved Fedora deployment:**
1. Social → PHONE → **CALLS**. Observe **DISABLED**, **UNAVAILABLE**, **SEARCHING**, **CONNECTING**, **BLUEZ_CONFLICT**, or **READY**. The screen is never blank. **DEVICE / HFP SETUP** opens the existing DEVICE diagnosis and call opt-in flow without automatically installing, starting or restarting a service.
2. Only after the user's oFono + D-Bus permission + WirePlumber HFP setup is separately approved and `Calls1` reports READY: real incoming calls show cards. Use **ANSWER** or **DECLINE**; active calls show **HANG UP**. Place a non-emergency call with a plain number, click **REVIEW OUTGOING CALL**, review the displayed number and click **CONFIRM CALL**. Use **SWAP ACTIVE / HELD**, **HOLD AND ANSWER** or **SEND TONES** only while BlueFerry reports their specific preconditions.
3. A submitted action means BlueFerry accepted the request, **not** that a call connected or the PC microphone/speaker route was independently verified. Verify with a safe real non-emergency call to a consenting participant. Keep the iPhone available to end a call if the Bluetooth channel misbehaves.
4. **Right now, before any local change**, the operator can run `blueferry calls` on Fedora as a read-only diagnosis. It should show `disabled`, `unavailable`, `searching`, `connecting`, `bluez_conflict`, or `ready`; do not run `blueferry calls enable` or modify system audio until the user approves the exact host changes.

## VERIFY

- Synthetic source tests: `tests/phone/test_phone_call_workspace.py` verifies connected profile, unique owner, state and action validation, bounded and masked callers, no API invocation for disabled/unavailable, explicit dial, one-call decline/hangup, DTMF, swap, hold-answer, unsafe phone numbers/IDs, emergency refusal, malformed payloads and same-owner/device rechecks, no private backend error output.
- Source/UI contracts: `tests/messaging/test_social_phone_call_workspace_ui.py` confirms existing PHONE tab/Contacts sidebar, real provider-backed click handlers, confirmation, colors and visible setup diagnostics, privacy clearing and tab-scoped polling, no standalone window, no implicit calls, no FaceTime/SMS authorizations.
- Existing PHONE workflow compiles both and runs the older messaging/contacts/audio/call readiness and setup tests. Exact-head checks pending.
- **Not verified:** physical Fedora HFP system ownership, oFono policy, WirePlumber backend, Quickshell rendered call cards, real dial/incoming/hangup, microphone/speaker routing, call waiting/DTMF, call audio handoff or actual installed BlueFerry 0.9.1 Calls1 compatibility.

## WATCH OUT FOR

- **Call state READY is not equivalent to audio ready**. oFono/BlueZ/WirePlumber can still route audio incorrectly or race to claim HFP. No audio fix, HFP plugin toggle, policy change or service restart is implicit in P25, and BlueFerry upstream documents the HFP path as experimental.
- **FaceTime is not Bluetooth HFP cellular calling.** BlueFerry documents FaceTime unsupported. A browser may join an *invited FaceTime link* on supported browsers, but not implement an Apple-authenticated native FaceTime client or place a FaceTime call to an arbitrary contact over this Calls1 API. Group FaceTime, real app-originated FaceTime, call forwarding/transfer, decline-and-SMS are different protocols/assignments. This release reports them as unsupported rather than presenting placebo buttons. A `multiparty` flag can identify a carrier conference when backend reports one; it is not proof that adding/merging participants is implemented.
- User request includes **calling from synced contacts**. P25 first brings up the real call-control workspace and manual dialing. Selecting a stored number directly from full address book requires careful selection/confirmation with ephemeral legacy card IDs and a separate owner-approved integration; don't treat ephemeral IDs as stable phone targets.
- **Data security:** Same-UID BlueFerry D-Bus and a short-lived process argument aren't production app-isolated grants. A protected Identity Center/Account Broker call-control host and private IPC would be needed before organizational profiles, enterprise caller identity, app-level confidentiality and revocation are claimed. Never log raw caller data, call arguments or service exception payloads. The UI attempts in-memory purge on tab/identity change; it is not a guarantee about other local apps.

## CHECKLIST

- [x] Re-read Syntagma AGENTS/Hospital/working policy; check exact main and PR owners, see non-overlapping PR #1486.
- [x] Verify BlueFerry upstream Calls1 methods and oFono/HFP prerequisites, Apple FaceTime limitations.
- [x] Implement bounded active calls + explicit call actions gated on real backend/device readiness.
- [x] Add CALLS tab status/call cards/dial confirmation instead of blank ChatFeed, preserving Contacts sidebar and audio setup.
- [x] Add synthetic tests, PHONE CI routing and durable handoff.
- [ ] Exact-head CI, repair any failures.
- [ ] Operator review/merge and separately approved local desktop update.
- [ ] Read-only `blueferry calls` and `PhoneCallPrerequisites.py --check` live status; obtain specific approval for any local HFP/oFono policy/WirePlumber/BlueZ change.
- [ ] Real non-emergency cellular call, caller ID, decline/hangup, optional wait/swap/DTMF and mic/speaker acceptance.
- [ ] Separate authenticated organization call grant/IPC and phonebook dial selection.
- [ ] Later SMS quick reply, FaceTime link support or alternative legitimate FaceTime integration, group chats/conferences.

## NEXT

If source CI passes, open draft PR, keep it unmerged and undeployed. On the operator's real Fedora host inspect `blueferry calls` (read-only) to discover the exact remaining HFP gate: disabled vs unavailable vs BlueZ conflict vs searching. Reuse the native DEVICE setup diagnostics, then request approval for **each necessary local modification** if the call path needs an oFono system D-Bus rule, WirePlumber HFP setting, BlueZ plugin change or service activation. Do not assume a package-install button completes the entire call setup.

**Recovery pointers:** current `main` base, P25 branch/PR and CI, plus P18–P24 read-only provider work; existing open #1486 touches only Social geometry service/test. Rollback by closing draft PR or reverting its bounded commit after an approved merge; no local rollback required.

## DECISIONS

Calls before message-sending/full-history and group workflows per operator priority. Limit scope to **real cellular HFP calling** and an honest CALLS UI. Do not invent FaceTime, group-call origination, SMS quick reply or call forwarding APIs. Do not change Fedora services/audio/pairing or activate production. Keep manual outgoing confirmation, emergency warning, provider authority and operator final acceptance. Preserve the user's existing Contacts label and UI layout outside CALLS.
