# Social PHONE P19 // Opt-in Personal iPhone read-only pilot

> **STATE:** GitHub draft integration. **NOT MERGED**, not deployed, not production Identity Center authorization, not a verified live iPhone inbox.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
> **ROOM / ASSIGNMENT:** Social PHONE end-to-end Personal read-only pilot; external Hospital-compatible continuation under operator's explicit "you do it all" implementation direction. No verified live Hospital Room/Assignment registration or staff role.
> **WORKER / PROVIDER:** OPEN AI // CHATGPT.
> **BASE:** fresh `main` `eeaad9ea2788eb48eb0b898ea0c17f7a1b054cbb` on 2026-11-06; merged P18e #1386. No open PHONE/Social-router/Identity collision found at preflight.
> **EXISTING AUTHORITY:** operator final; no production merge/host activation, local Fedora writes, trust-model acceptance, or verified organizational permission implied.

## IMPLEMENTATION

This PR is the **first connected source path** from a real BlueFerry D-Bus provider-read method to the existing Social PHONE conversation area. The prior P18a–e work comprised normalization, provider reading, synthetic revocation and a dormant QML adapter. P19 composes those in an **explicitly opt-in, bounded Personal-only local desktop pilot** with an honest Linux session-user threat model.

`services/phone/PhonePersonalReadPilot.py`:
- **Explicit terminal consent.** The PHONE **APPROVE READ** button requests a native `foot` terminal (does not grant access by itself). Its `--serve` command refuses a non-TTY; the operator must type the exact consent phrase `ALLOW PERSONAL IPHONE READ` and then select separate **messages**, **contacts**, **both** or **neither** read capabilities. The screen states that any same-UID desktop app can access this local pilot and that LLC/nonprofit identities are **not** authorized.
- **Short-lived memory-only host.** Session ends after at most 600 seconds, Ctrl+C, or explicit `revoke`. No durable credentials/grants, messages database, auto-approval, auto-start service, login automation or background message polling. The temporary socket is created only after consent in an owner-owned `XDG_RUNTIME_DIR/post-apollo-phone` directory (0700), socket mode 0600. Existing socket names are refused rather than replaced, and the socket is removed only if its inode still matches on shutdown.
- **Local peer verification.** Linux Unix socket `SO_PEERCRED` checks the same user ID on both ends. This is a **single-user convenience boundary** only: another process running under the same user, including a malicious program or companion app, is **not** excluded; the runtime socket path is not an authenticated application-specific boundary. An actual Identity Center/OIDC host has not been implemented or accepted.
- **Live provider call, protected from accidental scope mismatch.** The host pins a running BlueFerry unique owner and an exact matching saved profile + connected BlueZ device via the existing `PhoneDeviceObservation.observe` (P16). For a consented `messages.read` or `contacts.read` request it invokes the merged `BlueFerryHostReadPort.read_for_trusted_host`, which calls BlueFerry's `GetStatus` and `ListThreads` or `ListContactCards`, and P18a normalization. The host rechecks exact profile, provider owner, capability and connected state during the request, blocks on mismatches, and never directly calls `SendToThread`, `MarkThreadRead` or contacts/photo modifications.
- **Transport.** Client requests on the Unix socket contain only a fixed operation, never principal, organization, line, grant ID, phone number, recipient or arbitrary provider key. All other fields/operations are rejected. Responses are bounded (3 MiB), returned over this local socket and captured by one-shot `--client` commands for the existing Quickshell QML Process. No stdout logging or persistence is added. Host context keys are ephemeral correlation selectors **not secrets, proofs or grants**; monotonic read sequences prevent old snapshots from overwriting current content.
- **Revocation realism.** Host single-threaded processing orders read/revoke commands *within the same process*. An in-flight read accepted before revoke can finish before the revoke command is acknowledged. The QML **STOP ACCESS** action immediately clears its local adapter before requesting host revoke. When the host expires, disappears or changes context, a **metadata-only** check every 3 seconds clears the local view. This is **not a cross-process atomic delivery/purge acknowledgment** or a confidentiality guarantee against other same-UID apps. Retained OS/app/clipboard copies outside the adapter cannot be proven wiped.

`widgets/messanger/PhonePane.qml`:
- Integrates the **existing** `BlueFerryAdapter.qml` into the existing PHONE ContactList and ChatFeed. A new narrow command bar on MESSAGES and CONTACTS offers **APPROVE READ** (magenta), **LOAD PERSONAL** and **STOP ACCESS** (red/destructive). The terminal is explicit user consent; selecting CONNECT PHONE alone still performs data-free checks only.
- **MESSAGES:** only after explicit Personal host consent and one LOAD request, render actual P18a normalized conversation rows and oldest-first messages via the shared ContactList/ChatFeed, with **sendEnabled: false**. No automatic polling, sending, read marking, attachments or calls.
- **CONTACTS:** display bounded read-only BlueFerry contact-card rows, separate from chat conversations. They do not become SMS conversation targets. Contact photo bytes are never requested.
- Parser rejects wrong profile/schema, malformed content, old context epoch or stale per-operation sequence. The pane invalidates pending responses and clears local arrays when closed, another Social identity is selected, access is stopped or the host status check fails. The PhonePane itself is labeled **PERSONAL PHONE**; selected Social organization labels are not accepted as permission.
- `widgets/messanger/MessagingW.qml` supplies the current local Social identity ID **only as a change detector** so that changing identity clears any Personal cached data. It is explicitly not an authenticated identity principal or organization grant. No modifications to the shared SocialMessageRouter, SessionAdapter, ConversationFeed, BlueFerry, Bluetooth audio, Wi-Fi transports or oFono.

**Scope boundaries:** Personal-only Linux desktop convenience pilot, not a production enterprise trust boundary. The user may manage two LLCs and a nonprofit, but this pilot does **not** attach those organizational identities to an iPhone or permit automatic business-directory sharing.

## HOW TO USE

**After operator review/merge and separately approved local Fedora update:**
1. Open **Social → PHONE → CONNECT PHONE** and inspect whether the current BlueFerry iPhone has MAP (messages) and PBAP (contacts) active. A2DP/FaceTime audio alone does not verify either channel.
2. On **MESSAGES** or **CONTACTS**, choose **APPROVE READ**. This launches a `foot` consent terminal. The terminal is the only place a grant is created: read the privacy warning, type `ALLOW PERSONAL IPHONE READ`, and choose **m**, **c**, **b** or **n**. Leave this terminal running for the short Personal session; Ctrl+C stops it.
3. Back in PHONE, choose **LOAD PERSONAL** in the intended tab. Supported BlueFerry cached messages and contacts appear in the existing Social pane **only while this optional pilot is active and the matching phone data exists**. No one is sent a text.
4. Choose **STOP ACCESS** to clear the current local view and request revocation of the pilot session. Closing PHONE clears its view; host status checks clear view when the short-lived session expires/stops.

If the terminal/host, DBus, MAP/PBAP or profile is unavailable, PHONE reports not active/unavailable, with no fake data. A live host must be tested before claiming actual iPhone success. No extra installation is performed by this PR.

## VERIFY

- `tests/phone/test_phone_personal_read_pilot.py`: synthetic P18c reads over a local fake owner/device, separate capabilities, mismatched device/owner/capability, no permission escalation, timeout and revoke, strict Unix socket peer/mode/runtime directory, exact request shape, non-TTY refusal, terminal launch without automatic approval.
- `tests/messaging/test_social_phone_personal_read_pilot_ui.py`: explicit approval/read/revoke controls, existing Social list/feed reuse, inactive QML adapter, no send, no provider D-Bus calls inside QML, selected-identity-change wipe, generation/host-context status rechecks, no automatic phone-content fetch during menu opening.
- Existing P18a–e tests updated to expect the new **explicit opt-in Personal** PHONE connection instead of permanently empty content, retaining `sendEnabled:false` and no direct QML provider read.
- Existing PHONE CI compiles Python, runs unit suite and existing UI tests. This is NOT a real iPhone, Quickshell visual, Identity Center signed session or Fedora host test.

## WATCH OUT FOR

**Important:** This pilot does **not** fulfill the unassigned `MODEL/contracts/social-phone-identity-host-integration-handoff-p1-v0.md` production plan. Linux same-user socket credentials cannot isolate a different same-UID app from the session D-Bus or Personal data. Explicit terminal consent and a 10-minute expiry are user-safety measures, **not** proof of signed principal/session, verified line ownership, organizational membership or durable grant generation. Other same-UID applications might read the pilot while the session is approved. The local view's 3-second status check is best-effort invalidation, **not** a privileged acknowledgment that every display/clipboard copy was destroyed.

**Security acceptance requirement before production:** Identity Center/security and Account Broker owners must approve the actual host/IPC identity, per-capability consent, verified device/line binding, encrypted/durable grant and revocation authority if needed, and a trusted UI purge protocol. The current test-only P18d lock is not a substitute. True organization scope must be resolved from independently verified memberships, never labels or local identity IDs. The Personal pilot should not be promoted to company use or be silently auto-started.

The installed BlueFerry version and actual iOS permissions may not match upstream; MAP/PBAP availability and iMessage completeness remain unverified. The `foot` terminal is required for consent; if unavailable, it fails closed. Phone calls/oFono/HFP and working media/FaceTime audio are separate and untouched.

## CHECKLIST

- [x] Inspect merged P18e, current main/PR ownership, Syntagma Hospital/working rules and shared Social adapter interface.
- [x] Implement bounded, explicitly consented Personal-only local Linux socket host with real BlueFerry read port calls.
- [x] Reuse existing Social PHONE ContactList, ChatFeed and BlueFerryAdapter for real displayed read-only snapshots.
- [x] Bind phone content to matching connected BlueZ profile; refuse account/organization/line selectors.
- [x] Preserve no-send; separate contact cards; reject mismatched data and stale generations.
- [x] Clear adapter view on close, identity switch, explicit STOP ACCESS and failed host heartbeat.
- [x] Add fake-device/host/IPC tests, UI source checks and existing test compatibility.
- [ ] Exact-head GitHub CI.
- [ ] Operator PR review/merge.
- [ ] Authorized local Fedora update and interactive Personal consent.
- [ ] Real Quickshell rendering, BlueFerry read and iPhone MAP/PBAP acceptance.
- [ ] Production Identity Center/Account Broker ownership and secure cross-process grant/purge design.
- [ ] Organization-safe phone/account separation, sending, multi-device, oFono calling independently.

## NEXT

**If the operator chooses to test the Personal read-only pilot:** merge only with approval, update Fedora via the normal Post-Apollo mechanism, open PHONE, approve in the terminal, and load once. Verify actual texts are supported and contacts cache works; verify revoke/identity-switch/host restart clears data and existing audio continues uninterrupted. If the threat model demands protection against same-UID programs, do **not** activate this pilot: instead implement the separately approved privileged host and credential isolation first.

**For production:** assign the actual Identity Center and Account Broker authorization ownership, choose a sandboxed/privileged process trust boundary, per-user/device/line/account grants, provider permission evidence, durable revocation generation, and authenticated UI release/acknowledgment. Only after that can a company/nonprofit phone be integrated with trustworthy isolation. Expand read-only pilot to sends, multi-phone and calling only under separate operation grants and real device tests.

## DECISIONS

The operator's directive authorizes broad **implementation** on this scoped repo seam, not unreviewed production activation or an assertion that an external chat is registered in live Hospital. Source changes are GitHub-only and prepared as a **draft PR**. No local machine file modification, package install, service activation, Bluetooth/audio routing or oFono change. Operator final acceptance is separate. Rollback: close PR or revert the bounded commit if merged, stop the terminal host with Ctrl+C, and use STOP ACCESS to clear the view.
