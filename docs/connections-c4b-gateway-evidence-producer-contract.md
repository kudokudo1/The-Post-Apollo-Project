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
| Authoritative outcome | Native guest emits signed **UNAVAILABLE** diagnostic responses. DOC 1 #2273 refuses to treat local IPC diagnostics as terminal settlement | Independent custodian signed terminal receipt, atomic challenge spend and rollback/fork-resistant history, unknown-outcome recovery |
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

## NEXT / DECISIONS

- DOC 1 and the protected-custodian owner review the proposed semantic envelope, especially challenge encoding, exact target host/release/seat, authenticated measurement origin and no-local-fallback boundary.
- Nurse 2 verifies exact-head CI, tamper/refusal behavior and that all authority flags remain false.
- Operator decides whether to merge this source-only development milestone separately. Future hardware provisioning, native installation, root enrollment, production Sign-In and protected grant activation are **not authorized**.
