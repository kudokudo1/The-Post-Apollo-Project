# 🏥💜 DOC 6 // Original attempted native command fingerprint (process-local)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center V5 original-command recovery  
**STAFF ROLE //** DOC 6, external Hospital-compatible, live Hospital registration unverified  
**BASE //** `ebd5e740f6042b366cb39487b453fe9deb6592ac`  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

Before this change, the signed native client retained the `UNKNOWN_HOLD`/signed-frame observation after ambiguous transmission, but it exposed no durable or read-only fingerprint tying the attempted bytes to the original client challenge and command. This made it hard even to **describe** which exact command future independently protected history would need to reconcile.

`SignedIdentityCommandClient.last_attempted_wire` now exposes an immutable **process-local** `AttemptedWireFingerprint` containing:
- The verb `BEGIN`, `STATUS`, `CANCEL` or `RECOVER`.
- `request_id_sha256`: SHA-256 of the original host-issued request ID, or `None` for an initial BEGIN.
- `client_nonce_sha256`: SHA-256 of the 43-character original client challenge.
- `frame_sha256`: SHA-256 of the exact newline-terminated native command request frame built by the existing canonical serializer.

These hashes are recorded **after socket/connected-peer/seat preflight, immediately before the existing `conn.sendall(wire)`**. A failed/partial send or lost response therefore leaves a correlation fingerprint even after `_fault()` clears the mutable host request/phase. No raw nonce, request ID, frame, credential, OAuth token or login URL is exported in this new object.

`last_attempted_wire` means **the most recent attempted transport**, *not necessarily the latest method call*: if a later command is rejected by local preconditions, `last_wire_outcome` becomes `NO_SEND_ATTEMPT` for that call, while the fingerprint of an earlier actual attempted send remains available. If an ambiguous attempted send has faulted the client, all subsequent requests are refused and `UNKNOWN_HOLD` plus the prior fingerprint remain unchanged. A newly constructed client always starts with `last_attempted_wire=None`.

**No new send, query, callback, local storage, issuer, C5 consent, socket, signature, trusted history or production admission path is introduced.** This is a diagnostic correlation input for future reviewed *read-only* original-command recovery, NOT a recovery command itself.

## HOW TO USE

CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS remains **read-only**. Sign In, Cancel and Retry remain disabled.

A local non-production test client can inspect `last_attempted_wire` after an attempted native request to compare the frame, nonce and request hashes. This should never be presented to the UI as authenticated login state or proof the host executed anything.

## VERIFY

Eight new real disposable AF_UNIX gateway/client tests cover:
1. Fresh client with no prior attempted send.
2. BEGIN hash equality against the exact `build_request()` frame and captured nonce.
3. STATUS hash equality against the actual host-issued request ID and fresh nonce.
4. Duplicate BEGIN local refusal retaining the last attempted fingerprint while setting `NO_SEND_ATTEMPT`.
5. Connected-host trust refusal before send with no fingerprint.
6. Simulated broken/partial `sendall`: original frame digest retained with `UNKNOWN_HOLD`.
7. Actual disposable host BEGIN side-effect with deliberately lost signed receipt: hash remains unchanged through refused BEGIN/STATUS/CANCEL/RECOVER; a new client has no fingerprint.
8. Frozen read-only observation with no authority/settlement/retry fields.

The existing signed-client workflow includes these plus Linux process-origin, gateway lifecycle and CPU++ offline checks. Exact-head GitHub workflow evidence, independent Nurse 2 review and operator-controlled merge require separate verification.

## WATCH OUT FOR

- **Hash equality is not original-command authenticity.** A same-UID process can fabricate an arbitrary fingerprint or present a cloned process memory snapshot. Independent C3e current history, independently enrolled C4b original host/process/seat, C5 one-use intent, actual command terminal receipt and rollback-resistant custody are NOT established here.
- A hash recorded before `sendall` does **not** prove the kernel received bytes, nor does a completed `sendall` prove a host side effect.
- The fingerprint remains *in this Python object only*. It vanishes on process death and cannot close the cross-process crash/restart gap; no write to untrusted SQLite is added.
- A nonce hash is not an authorization credential; this object must never be used to permit a new BEGIN/CANCEL/RECOVER or clear `UNKNOWN_HOLD`.
- DOC 1's real Linux per-packet observations and DOC 2's current C4b signed-denial work remain CI/nonadmission, and the Identity-specific C5 owner remains unresolved. This change does not adopt their authority.

## CHECKLIST

- [x] Re-read current Syntagma entry/Hospital protocol, main, signed client/adapter, and neighboring DOC 1/2/C5 work.
- [x] Add narrow process-local original request digest data to DOC 6 signed client.
- [x] Add eight adversarial native-client tests without changing gateway/adapter/UI.
- [ ] Exact-head signed client/synthetic-boundary/Grammar workflows and raw tests PASS.
- [ ] Independent Nurse 2 **pre-merge** scoped review.
- [ ] Operator merge decision.
- [ ] Independently protected original-command history, gateway sender/seat proof, Identity-specific C5 signed SPENT and protected terminal outcome reconciliation.

## NEXT

Verify exact-head GitHub CI, request Nurse 2 review before merging. Once an owner-approved independently authenticated read-only original-command lookup exists, DOC 6 can map the **original** request digest into that contract without trusting this process-local observation as the authority itself. Production Sign-In remains HOLD.

## DECISIONS

Three-file DOC 6-only source/test/docs development milestone. No real credentials, operator workstation writes, installed gateway or root changes, other owner edits, live Hospital registration, production activation, automatic merge, or permission to retry.
