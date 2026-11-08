# 🏥💜 Connections C5a // TASKS Three-Scope Host Enforcement

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Connections protected host integration ↔ TASKS encrypted draft recovery  
**STAFF ROLE //** DOC / external Hospital-compatible OPEN AI // CHATGPT, not verified as live Hospital-registered  
**ASSIGNMENT //** Operator handoff on Nov 8, 2026 to take over TASKS ↔ Connections host integration; advance real, independently running permission enforcement without activating real credentials  
**SOURCE //** `main` `e0544dffa8f899097dd5e9174433403917096db2`; M15e #1509 merged at `12cf532ed150cc4502b17c21f110bc77c800a244`  
**AUTHORITY //** Operator authorized cross-boundary development and GitHub merges after clean verification. No Fedora desktop writes, production installation, service activation, Secret Service access, credentials, real draft text, saved TASKS source mutation or permission activation. No live Hospital assignment/lease verified.

## IMPLEMENTATION

M15e now proves a one-editor capture transaction with synthetic host approval, rechecked saved-source and editor identity, one-use approval consumption, and source-bound AES-GCM. Its HMAC grant is **in-process fake authority**. Production Connections `ConnectionsBroker.qml` still has `credentialActionsEnabled:false` and no protected consent or key-release host; the existing C4b/C3e mechanisms secure **read-only fake status-service** origin and test release floors, not credential or TASKS authorization.

C5a adds a real **separate-process, Linux descriptor-isolated scope broker** without pretending this integration is already a deployable trusted service. It reuses the precise C2c private-host pattern rather than inventing a new generic process or altering C2r/C3d/C4b service owners.

- `services/connections/experiments/C5aTasksScopeHost.py`: one independently spawned Python broker with two **different inherited SOCK_SEQPACKET Unix-domain descriptors**. A disposable harness holds the separate reviewer descriptor. A separate TASKS client process receives **only** the client request descriptor. The client cannot send `approve`, `revoke`, `shutdown`, raw keys, a source path, a draft, an editor ID, or a source hash. There is no named socket, network, service install, permission prompt, file write, keyring or API call. The host maintains a bounded in-memory pending-request ledger and never hands a credential or capability secret to QML.
- Each request binds one fixed operation scope, target and strict numeric edit/source revisions. Capture permits `entry` or `details` and a positive edit epoch; preview and clear permit only `checkpoint` and editor epoch zero. Operator review on the **other descriptor** requires a matching pending request, scope and target, exact `confirmed:true`, and 1–30,000 ms expiry. Approval happens only on that test-reviewer descriptor. An execution consumes the reviewed request **before** any subsequent stage, rejects expiry, mismatches, revocation and replay. The only permitted response is `SYNTHETIC_SCOPED_STEP_ACCEPTED_NO_REAL_GRANT`: all actual consent, credential, key-release, source-write, draft capture, preview, clear, checkpoint and caller-authentication flags remain **false**.
- The executable refuses use unless `GITHUB_ACTIONS=true`, `POST_APOLLO_C5A_DISPOSABLE=1`, a nonroot Linux CI runner, and a newly created, same-owner, 0700 `/tmp/postapollo-c5a-scope-*` directory containing a private 0600 exact test marker. This is a **CI misuse guard, not a production trust root**; users cannot obtain a real grant by setting these variables.
- `tests/connections/test_connections_c5a_tasks_scope_broker.py` tests both direct rejection/one-use policy and actual separate operating-system processes using only the preassigned descriptors. It checks all three scopes, wrong-target/cross-scope, first-use, replay, revocation, TTL expiry, duplicate JSON fields, forged approval over client FD, malformed/injected input, no stdout/stderr leakage, no mounted host and sole writer. The GitHub workflow reruns C2c/C2l, M15e/M15d/M15c, M13m/M13p/M13t, M11d and C2a safeguards.

**Critical boundary:** A Unix FD is a kernel object, but a disposable harness handing one endpoint to a process is **not** proof that a production Post-Apollo binary or human operator was authenticated. Same-UID processes with an inherited/leaked FD may impersonate the intended client. C3b/C4b signed/confined identity evidence cannot be promoted from a fake status host to a new scope host by assertion. This implementation is genuine separate-process permission **mechanics**, not a deployed identity or consent authority.

## HOW TO USE

No workstation action. GitHub Actions executes the new test automatically in a disposable runner. A production user continuing **TASKS → SYNC → RECOVERY → CAPTURE → CHOOSE UNSAVED EDITOR** will still see **SAVE ENCRYPTED DRAFT disabled**. C5a is deliberately not imported into `shell.qml`, `ConnectionsBroker.qml`, `ApolloHubTodoStore.qml`, CPU++ or TASKS QML. Existing Settings++ Connections diagnostics remain read-only.

## VERIFY

Exact-head CI must demonstrate:
- A real broker subprocess and a separate client subprocess, with only **client** FD passed to the client and the separate reviewer FD withheld.
- All three operations independently scoped; reviewer and requester channels cannot be exchanged.
- No execution before a distinct reviewer decision; wrong scope/target, revoked, expired and replayed requests refused.
- Bounded, exact-field, duplicate-key-rejecting input; raw draft text/paths/keys rejected.
- CI marker failure outside isolated test root; no real user session or credential dependence.
- All results, including synthetic accepted-stage results, keep `hostAuthenticated`, `operatorConsentAuthenticated`, `credentialActionsEnabled`, `keyReleaseAuthorized`, `realDraftCaptureAuthorized`, `realPreviewAuthorized`, `realClearAuthorized`, and `sourceWriteAuthorized` false.
- Original production TASKS one `FileView` and one `todoFile.setText` only, and Connections still `credentialActionsEnabled:false`.
- M15e/M15d/M15c and C2c/C2l compatibility.

**This does not run real Fedora Wayland, system D-Bus, SELinux policy for this broker, or Secret Service.** Those are separate mandatory native gates for production integration.

## WATCH OUT FOR

This host has no real operator identity, no verified Connections caller identity, no independent source-owner evidence, no protected release root, no approved read-only source digest, and no credential lifecycle. The `confirmed:true` reviewer field is simulated operator input on an isolated FD, **not consent**. It never receives or encrypts a real draft and does not authorize QML key reads, checkpoint deletion, a saved-TASKS write or automatic replay.

C3e's authority-owned release floors, C4b's protected fake status-service and C5a's three-scope descriptor broker currently have **different test owners and release surfaces**. Before production use, the protected host must be built, independently signed/pinned and deployed through an approved trust chain, run under suitable SELinux/UID isolation, authenticate the requesting TASKS process via an independently verifiable channel, enforce revocable operator consent, and keep encryption keys and plaintext confined to the host. Root/same-UID compromise, FD transfer, and private authorization channel theft are outside this test's security proof.

Do not reinterpret the synthetic accepted-stage marker as permission for M15e editor snapshot capture.

## CHECKLIST

- [x] Verify current main, M15e merge, no competing open Connections PR, Syntagma and owner handoff
- [x] Reuse C2c descriptor separation model instead of using caller-supplied identity labels
- [x] Implement real separate-process three-scope broker with bounded request lifecycle and distinct reviewer channel
- [x] Ensure no production QML import, saved-source write, credential, key release or draft plaintext path
- [x] Add full adversarial separate-process tests, security regressions and workflow
- [ ] Exact-head CI verification and any necessary fixes
- [ ] Operator merge under standing approval, conditional on green CI
- [ ] Trusted release/SELinux/verified TASKS caller transport, consent persistence/revocation
- [ ] Real secret host encryption, restart unlock/preview and explicit clear, after acceptance
- [ ] Fedora native verification and operator UI acceptance

## NEXT // C5b / M15f

Advance the real host toward a **separately protected, authenticated client entrypoint**, not a same-UID named socket. Build an isolated authoritative host-owned consent ledger and signed process-release binding, then prove three scopes and revocation across actual host restarts under protected OS identity. M15e's actual editor capture adapter may be implemented only after the host can verify fresh source-owner and editor identity and has a real, explicitly approved capture grant. Avoid adding another status screen or another saved TASKS JSON writer.

## DECISIONS

Follow operator's Nov 8 handoff for cross-boundary development and standing merge approval, without claiming live Hospital registration or superseding prior C2y/C4b ownership decisions. This C5a PR touches only additive, unmounted Connections experimental host code, its targeted tests, CI, and this report. No Nurse 2 review requested by operator. No local machine edits, installations, production service enablement, real secrets or TASKS plaintext. Operator retains final acceptance of deployed recovery.
