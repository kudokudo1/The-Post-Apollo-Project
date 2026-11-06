# Social PHONE P18d // In-process phone read release / revoke model

> **STATE:** Isolated GitHub source and synthetic tests only. **Not** authenticated host code, approved Identity Center grants, private IPC, content authorization, live UI integration, or production activation.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`
> **ROOM:** Social PHONE / P18d host-release model, Hospital-compatible continuity only; no registered live Room or Assignment verified.
> **WORKER:** OPEN AI // CHATGPT (external DOC-compatible). No Identity Center, Account Broker, or shared Social router ownership claimed.
> **BASE:** Fresh `main` at `32c889a49203ee7c890e888bbcbd02b32735d670` on 2026-11-06. Prior P18c PR #1376 merged and no active PHONE/Identity integration PR collision was found.

## IMPLEMENTATION

The already-merged **P18c BlueFerryHostReadPort** accepts a `host_guard` and `host_release` callback after a bounded provider read. P18d adds a host-only **in-process ordering model**, `services/phone/HostReadReleaseGateModel.py`. It provides a concrete integration contract for these callbacks, without claiming that arbitrary Python callback instances are security authority.

- `HostAssertedPhoneScope` is a frozen, validated bundle of **host-asserted**, *not independently authenticated*, principal, session, device binding, line binding, BlueFerry profile, unique provider owner, Personal/Organization scope, operation, grant generation and active context generation. Personal scope cannot carry an organization and organizational scope requires a nonempty identifier. No display nickname, contact name, number, Bluetooth MAC or local organization label becomes a permission.
- `HostReadReleaseGateModel.begin(scope)` refuses an unverified/syntactically malformed scope and does not silently replace an already-active one. It returns **transient** `BoundReadCallbacks(guard, release)` for **one epoch** only. It never issues credentials, consent receipts or a production grant.
- `guard(operation, profile, owner)` checks the exact pinned operation/profile/provider owner and calls a **host-supplied** evaluator. The P18c read port calls this guard before and after its provider read.
- `release(operation, profile, owner, projection)` acquires the *same model lock* used for cancel/revoke, rechecks the host-supplied evaluator, validates that the P18a projection belongs to that exact profile and read capability, then invokes the **host-supplied** delivery callback *under the lock*. No private content is returned by the gate's result envelope or retained by the gate.
- `cancel()` invalidates the epoch and invokes a **host-supplied** purge callback while holding that lock. Old callbacks cannot be revived, even when the same phone/profile is reselected. A rejected or partially failed delivery also requires a purge; if purge acknowledgement fails, the gate **seals** and blocks further release/activation until an external owner recovers state.
- Distinct `messages.read` and `contacts.read` capabilities are enforced. `messages.send`, marking read, audio, contacts modification, BlueFerry D-Bus calls, network access and file persistence do not exist in this module.

**Critical authority limitation:** `evaluator=True` is not a signed Identity Center session, provider permission, authoritative consent, protected host IPC, or organization membership proof. A caller may fabricate `HostAssertedPhoneScope` or the callbacks. The model only orders code paths using **this instance**. A real grant-revocation transaction must be serialized with the actual grant authority **and** an acknowledged purge of any data previously displayed or retained by the UI. A delayed call into the model is not proof of protected delivery to a separate app/process. No production security claim should be made from synthetic tests.

The model deliberately has **no CLI**, process auto-start, D-Bus connection, QML binding or invocation from existing CONNECT PHONE. The actual Social PHONE ContactList/ChatFeed remain `conversations: []`, `messages: []`, `sendEnabled: false`.

## HOW TO USE

**Future approved host implementation only:** construct the release gate *inside* the approved privileged session/device broker with a trusted session + consent evaluator, a scoped data-delivery sink and a **revocation-acknowledged** purge hook. Under an approved host, supply callbacks from `begin` to P18c `read_for_trusted_host`; on sign-out, permission revoke, device/line/profile change, organization switch, or provider change, atomically commit cancellation and purge before re-arming. Never expose the gate, scope constructors or callback methods over an untrusted QML command/subprocess.

**Current user:** no new PHONE control or login requirement. The live iPhone inbox is **not** enabled by this PR.

## VERIFY

- `tests/phone/test_host_read_release_gate_model.py` composes P18c+P18a with **invented** thread and contact data and fake provider/host callbacks. It checks reads released to a test sink, cleanup on revoke, operation separation, same/different context switching, stale callback rejection, permission change after the provider read, failure/partial-send purge, cross-profile spoofed data rejection, and fail-closed invalid scopes.
- A deterministic threading test holds a synthetic delivery sink while a cancel is requested; once delivery commits, cancel purges it under the same instance lock. Another test revokes during the provider fetch and proves that no snapshot reaches the sink.
- `tests/messaging/test_social_phone_release_gate_boundary.py` verifies that shared QML remains disabled, no live private data read path is added to PHONE, and the existing Messaging shared-router ownership is preserved.
- Existing PHONE CI runs both suites. All test content is synthetic. No user's SMS, contact card, phone number, iPhone device, or Fedora host is inspected by this code.

## WATCH OUT FOR

**Cross-owner blocker remains:** `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` is still proposed; it has no verified assigned Identity/security or Account Broker trusted-host implementation owner. An in-process `RLock` is a **simulation**, not cross-process credential protection. A same-UID D-Bus caller may still read BlueFerry outside this model; real process isolation, session authentication, exact user/device/phone-line binding, operation-specific provider consent, authoritative grant generation, revoke notification and UI wipe need an approved architecture and owner.

Do not claim working message synchronization from successful CI, MAP/PBAP status, an opaque profile UUID, local nickname, synthetic scope or successful callback. Existing A2DP/FaceTime audio, oFono installer and independent CALLS ON PC settings are outside this PR.

## CHECKLIST

- [x] Confirm merged P18c, fresh main/PR ownership and current Syntagma AGENTS/Hospital protocols.
- [x] Reuse P18c host callback API, P18a normalized snapshots and existing synthetic grant fixture semantics instead of inventing another messaging router.
- [x] Implement read-only operation/context/epoch bound host callback model.
- [x] Model one-instance release vs cancel ordering and mandatory sink purge.
- [x] Reject stale callbacks and a failed purge; preserve Personal/Organization separation at the selector level.
- [x] Add synthetic integration/concurrency tests and shared-Social safety tests.
- [ ] Exact-head GitHub CI.
- [ ] Operator review/merge and final acceptance.
- [ ] Identity/security and Account Broker owners explicitly accept process/grant/revocation design.
- [ ] Implement genuine authenticated, separately permissioned iPhone data reader and safe host-to-UI content transport.
- [ ] Live Fedora/BlueFerry/Quickshell acceptance without disrupting audio.
- [ ] Separate oFono/HFP and multi-phone profile-lifecycle work.

## NEXT

**P18e (owner-controlled):** Actual host/auth decision and a minimal, read-only **PERSONAL iPhone** pilot: approve threat model, host-owned verified session identity, device/profile/line binding, separate `messages.read` and `contacts.read` consents, signed/durable grant authority, secure IPC or an explicitly documented same-UID trust boundary, atomic grant/release/revoke ordering, and reliable UI purge on permission/context changes. Only then call P18c's provider reader and release its P18a projections into the single existing Social PHONE router. Historical iMessage completeness is provider/iOS-dependent and must be verified on the actual device; real sends are a separate grant.

**Other lanes:** Verify actual BlueFerry multi-device profile support before promising concurrent iPhones; continue oFono/WirePlumber HFP verification separately, preserving working media audio.

## DECISIONS

Keep one Social PHONE surface and primary CONNECT PHONE flow. No new OS service, phone login ceremony, direct QML content reader, code in `services/identity` or shared Social router, local machine mutation, merge or production activation. Test-only model return values always say `IN_PROCESS_MODEL_ONLY`, `authorization=NOT_IMPLEMENTED`, `routeEligible=false`, `contentAccessEnabled=false`. Operator retains authority, with rollback by closing the draft PR or reverting only this commit after a later authorized merge.
