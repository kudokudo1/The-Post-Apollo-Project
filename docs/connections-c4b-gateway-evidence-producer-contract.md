# 🏥💜 DOC 2 // C4b Silverblue gateway evidence producer contract proposal

**PATIENT:** The-Post-Apollo-Project  
**ROOM / OWNER:** Universal Connections · C4b Silverblue Gateway · DOC 2  
**STATUS:** PROPOSED owner-to-owner evidence semantics, source-only CI adapter; **PRODUCTION SIGN-IN HOLD**.  
**RELATED:** Original C4b native #2211; DOC 2/C3e compatibility #2231; DOC 1 local trust boundary #2229; DOC 1 protected custody RFC #2209 and handoff issue #2018.

## IMPLEMENTATION // Already demonstrated vs still missing

A future custodian needs to verify **who measured the real gateway**, not just accept a signed claim made by the gateway itself. The existing C4b official Silverblue CI already performs actual OS checks while the installed service runs, but it is an isolated test and its signed release root is minted within the disposable guest.

| Evidence family | Existing original C4b source / what it verifies | Missing protected-production input |
| --- | --- | --- |
| Signed installed release and package | Original \`guest_identity_service_probe.sh\` and \`runtime_receipt_binding_ci.py\` verify signed RPM and installed file digests; original C3e-AH combined verifier executes on the running guest | Operator-enrolled release root, independently current release epoch/sequence and revocations |
| Running process origin | Original probe and C3e-AG read real systemd MainPID, kernel /proc PID startTicks, UID/GID, cgroup, SELinux, interpreter/script hashes; lifetime is rechecked around four signed denials and observation | A protected and authenticated measurement source; current boot/session/seat lineage and a guaranteed unchanged process across handoff |
| Actual receipt signer | Original native gateway signs UNAVAILABLE for BEGIN/STATUS/CANCEL/RECOVER. Controller verifies the exact signed BEGIN denial and pre-boot challenge, and the guest checks runtime key against its guest-local signed release | Independently enrolled receipt role and operator-approved key/release association |
| Challenge encoding | DOC 1 \`issue_challenge\` in local-test mode returns **exactly 32 raw bytes**. Original C4b BEGIN command nonce is **43-character unpadded base64url text**. This new test adapter proves deterministic lossless encoding and exact signature verification | A true independent issuer, purpose/host/release/head binding, external one-use spend, expiry, revocation and current trust state. The encoding does **not** issue or spend a protected challenge |
| Native seat and boot | No accepted protected native source currently binds a specific active unlocked session and compositor seat to this observer | Authenticated boot ID, login session, unlocked seat and continuous origin recheck by the appropriate owner |
| Authoritative outcome | Native guest emits signed **UNAVAILABLE** diagnostic responses. DOC 1 #2273 refuses to treat local IPC diagnostics as terminal settlement | Independently current custody/spend and separately authenticated original effect-owner terminal evidence; rollback/fork-resistant history and unknown-outcome recovery (see proposed recovery clarification below) |
| C5 consent and Identity command | Not produced by C4b. Broker still has \`credentialActionsEnabled: false\` | Separate C5 protected one-use human consent and Identity Center native action approvals |

## Proposed future read-only evidence envelope (NOT a frozen wire format)

DOC 2 would supply a bounded, canonical challenge-bound observation **only after** an independently issued challenge is delivered through a separately approved source. Required semantic families:

1. **Scope:** fixed Identity-only audience and service/unit; host identity from independent enrollment, not guest-authored JSON; approved signed release policy and receipt-key role.
2. **Challenge:** exactly 32 raw challenge bytes interpreted by the original gateway as unpadded base64url nonce text; bind exact purpose, external nonce ID, issued/expiry times, current history head and monotonic sequence. Hash the **raw bytes** and the **command nonce string** in distinct fields. Neither digest independently proves issuance or spend.
3. **Measurements:** immutable package/script/unit/policy digests and inode identities; live systemd MainPID/startTicks/UID/GID/cgroup/SELinux, interpreter, boot ID, active seat/session; recheck before and after the signed denial and final observation.
4. **Receipt:** actual signed UNAVAILABLE response frame, pinned runtime receipt key and authenticated release-role binding. A denial is not permission to begin Sign-In.
5. **Uncertainty:** reject stale process, swapped key, missing origin, missing seat, changed boot, revoked release/root or unavailable custodian. Never automatically retry an ambiguous protected commit. Return explicit HOLD/UNKNOWN with no credential action.
6. **Separation:** DOC 2 owns the measured Silverblue gateway producer. DOC 1 and the appointed custodian own current root/challenge/history verification. C5 owns human consent. Identity Center owns native BEGIN/CANCEL/RECOVER admission and provider actions.

The eventual remote request/response syntax, key hierarchy, transport endpoint and exact native evidence format must be agreed with DOC 1 and the appointed custodian. **Do not use this conceptual envelope as an already approved protocol.**

## VERIFY // This bounded milestone

\`c4b_raw_challenge_evidence_candidate_ci.py\` simply takes an existing 32-byte candidate challenge, encodes it as an existing C4b command nonce, calls **unchanged** \`verify_controller_challenge_ci.inspect_ci_only\`, requires exact signed-denial proof fields and negative flags, and outputs clearly marked **CI-only** raw/encoded challenge hashes, signed-frame hash and public-key hash. It does not generate a signer or independently authorize the candidate nonce.

Adversarial CI cases cover nonce length/type, modified raw nonce, replaced guest key/frame, duplicate/malformed serial markers, wrong signed command, forged positive grant, extra backend claim and tampered digest. The workflow reruns the original C4b denial security suite. Existing repository workflows may also trigger the full disposable official Silverblue VM due to broad C4b test-directory path filters; results must be checked separately.

This is NOT a real installed gateway evidence transport. A valid test result means only that existing C4b command-nonce encoding and signed-denial verification remain consistent for the raw bytes provided. **No independent custodian, host, physical active seat, consent, real external history or production Sign-In is authenticated.**

## WATCH OUT FOR // Integration gate

An independent custodian could send raw bytes to the guest, but merely presenting those bytes through guest-controlled storage cannot prove independent issuer custody. A guest-root actor can replay local bytes and restore local state. A local public key is not an enrolled host or receipt-signing key. Do not promote signed UNAVAILABLE to a terminal protected COMMITTED receipt. Never ship disposable CI test code in the installed Silverblue RPM.

## DOC 2 real-guest boot continuity extension (new separate CI milestone)

The official **disposable Fedora Silverblue guest** now also pins the
kernel's \`/proc/sys/kernel/random/boot_id\` while the installed gateway is
running. It reads and validates a 36-character UUID directly from procfs,
rechecks the same observed boot before and after **all four** actual
signed-denial actions and through the existing release/kernel observations,
and refuses a deliberately substituted expected boot pin. The host-side KVM
runner requires the new unique PASS marker before accepting the full
two-reboot rollback cycle. Fast source-contract tests check that guard's
placement and exact marker; real GitHub KVM must independently pass.

**Limit:** This is guest-local boot-lifetime continuity, not an
operator-enrolled host fingerprint, trusted remote witness, approved release,
active unlocked human seat, independently issued/spent challenge, signed
terminal outcome or production Sign-In. The boot UUID is neither a secret nor
a trust anchor; no UUID is exported to GitHub logs. The existing guest
signing root remains disposable, all authorization flags stay false, and no
production package or native service source is modified.

## NEXT / DECISIONS

- DOC 1 and the protected-custodian owner review the proposed semantic envelope, especially challenge encoding, exact target host/release/seat, authenticated measurement origin and no-local-fallback boundary.
- Nurse 2 verifies exact-head CI, tamper/refusal behavior and that all authority flags remain false.
- Operator decides whether to merge this source-only development milestone separately. Future hardware provisioning, native installation, root enrollment, production Sign-In and protected grant activation are **not authorized**.

## Proposed recovery clarification // Original execution versus current lookup

DOC 2 owner response to DOC 1's [cross-purpose recovery proposal #2581](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2581) (reviewed source `13fc31491492abb86e15903a1c5f074785085ae1`). **ACCEPT** independent currentness, stable original effect correlation and durable uncertainty fences as semantics; **REVISE** the source/recovery join below before any wire freeze; **HOLD** authority-bearing implementation. This does not approve the still-draft DOC 1 PR, choose a production recovery policy or change any runtime.

| Evidence family | Original execution (preserved record) | Current separately authorized read-only recovery (fresh observation) |
| --- | --- | --- |
| Purpose and correlation | Independent authority namespace and original action/operation, original request/nonce and exact submitted-frame commitment; for Forest the original attempt, context and affected output unit/recipient | New lookup identity/challenge bound to that same original operation and requested minimum recovery fields, never a new execution request or replacement original attempt |
| Installed origin | Enrolled original release, receipt role, host, boot, process/start/lifetime and original active-seat/channel binding measured at execution; immutable authenticated historical commitment, not a live PID lookup after restart | Current enrolled query-only responder/release/receipt role, boot/process and actual lookup channel; purpose-specific current operator/session authorization under separately accepted recovery policy |
| Custody | Original one-use spend and unresolved effect fence, independently protected against rollback/fork | Current independent history/root/revocation/fence state, reconciled to the preserved original record; fresh challenge proves lookup freshness, not original execution freshness |
| Terminal result | Authentic effect-owner evidence for exact original effect, or exact no-effect plus durable prevention of delayed original submission | Return only independently authenticated authorized minimum evidence about the original result; no new effect, private credential/content fetch, repeat command or original output retransmission |

The original execution's release, PID/start, boot, key, seat and recipient may legitimately be historical by the time a lookup is needed. Do not require the original process to remain alive forever to reconcile an already attempted operation; equally, do not replace historical measurements with the currently running process, new boot, newly enrolled key, new seat or newly attached recipient. A current authenticated responder is not automatically the original effect owner. Historical signature validity, current responder authority and independent current custody are separate checks. Recovery after logout, revocation, restart or key rotation requires its own operator-approved purpose and recipient/seat policy; it does not carry forward the original consent or permit execution. Never interpret a changed epoch as a fresh execution allowance.

The existing native Identity probe emits signed UNAVAILABLE, not authoritative provider effect/no-effect. DOC 6's [snapshot-only comparator](./identity-center-v5-snapshot-only-recovery-consumer-doc6.md) also remains diagnostic: no authenticated query-only collector or durable original attempt fingerprint yet exists there. For Forest, [the First-Tree C5 contract](./connections-forest-c5-b6-protected-permission-consumption-rfc.md) separates internal event/commit, actual serialized delivery and withdrawal. Local R4b callback return, STOP/close, public status, and current view correlation cannot attest protected delivery or no-effect. Do not use current-source observations, signed denial, a missing row, process exit or socket close as proof that future original submission is impossible.

### Proposed C4b acceptance cases (not implemented or approved)

- Original operation unresolved across reboot/process replacement/key rotation: fresh authorized recovery may reference the preserved original record; substituting current boot/PID/release/recipient for original evidence, cross-purpose or changed original commitment refuses. No replay.
- Stale or unavailable current enrollment/history, missing historical authenticated binding, or unverified original effect owner: UNKNOWN/HOLD; no new overlapping execution or budget reclaim. Missing original live process alone does not settle no-effect.
- A separately authorized query-only recovery route uses bounded data, no injected caller callback or native execution adapter, no provider action, and no private original output. Fresh request/nonce is lookup-only and cannot be promoted to BEGIN/CANCEL/RECOVER execution, Forest SEND or another purpose.
- Authenticated terminal evidence must match original scope and independent custody; prove durable prevention of delayed original submission before claiming no-effect. Current evidence cannot establish historical facts that were never recorded. If unresolvable, preserve affected original fence, not a global lock.
- Forest actual sender/recipient/seat measurements remain pending approved Core/Runtime final-send handles; current R4b public-only fixture correlation stays nonauthorizing and unblocked. Keep C4b production observation privilege separate from CI-only SYS_PTRACE.

DOC 1 owns independent history, original fence and lookup currentness; DOC 6/Identity C5 and relevant effect owners own command outcome, consent and query authorization; Forest Runtime/Mind/C5 own actual protected serialization, context and permission. DOC 2 supplies approved native installed origin and recipient/seat observations, not custody or settlement. Existing test-only release roots, raw challenge encodings and signed denial tests stay nonauthorizing. Exact historical evidence retention, lookup authorization, schema, release/observer privileges, transport, host selection and independent enrollment await owner/operator decisions. NAS and second-PC setup remain deferred. No workstation, key, service, protected action or production activation authorized.


## Native service versus human login-session observation (CI-only)

The existing C4b gateway is an inert, separately supervised system service in
`/system.slice/post-apollo-identity-silverblue-ci.service` with a dedicated
nonhuman UID. Identity's existing
[LogindSeatGuard](../MODEL/contracts/identity-center-logind-seat-guard-v0.md)
instead resolves the actual host process's login session and its owner, activity
and lock hint. A service's UID/cgroup, package signature or signed command denial
cannot establish the human session required by that guard.

The disposable official Silverblue guest now queries the actual gateway through
the installed libsystemd `sd_pidfd_get_unit` and `sd_pidfd_get_session` APIs
([upstream contract](https://www.freedesktop.org/software/systemd/man/latest/sd_pid_get_session.html)).
Within each existing origin check, use a live process handle, check the expected
unit and require precisely negative ENODATA for absence of login-session
membership; any other error or actual session association fails the diagnostic.
Recheck process lifetime and start ticks and close the descriptor. No session
identifier is emitted, no login1 state is changed, no desktop environment value
is adopted, and no new package dependency is installed. The host runner requires
the new exact marker after all four existing signed UNAVAILABLE commands, alongside
existing native boot/SELinux/rollback checks. Two source-contract tests check
placement and marker requirements; actual KVM evidence remains necessary.

This is a native system-service membership/absence diagnostic, not a D-Bus
LogindSeatGuard execution, positive seat observation, compositor lock witness,
continuous authentication or admission decision. DOC6/Identity and the Sway
owner must agree a separately authenticated session-bound desktop endpoint and
its actual lock/currentness lifecycle, rather than substitute the daemon's UID,
an environment ID, the first active session or an unlocked logind hint. Preserve
the original service identity, original operation/recipient and current seat
as distinct evidence. DOC1 independently enrolls/verifies source and current
custody; C5 independently owns human consent. No new production privileges,
wire, signer, model, service, hardware provisioning or protected action.
NAS and second PC remain deferred. Production HOLD.
