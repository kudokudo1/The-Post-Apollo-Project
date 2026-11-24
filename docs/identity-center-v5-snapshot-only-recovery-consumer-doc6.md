# 🏥💜 DOC 6 // Snapshot-only Identity native recovery consumer boundary

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Identity Center V5 original-operation recovery  
**STAFF //** DOC 6, external Hospital-compatible; live Hospital attachment unverified  
**BASE //** `ef8e42375bb133ef0fba8c3b980c8c3c4da46a72`  
**PRODUCTION SIGN-IN //** HOLD

## IMPLEMENTATION

The merged, independently reviewed [DOC 6 #2381](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2381) implements a deny-only original native command/recovery comparison. Its original `inspect_original_attempt_once(candidate_provider=...)` accepts an **arbitrary Python callback**. Even if called only once, that callback could write a file, send a network request or invoke a command before the comparison returns `UNKNOWN_HOLD`. A label of *read-only* cannot constrain callable behavior. This concern was identified explicitly in [Connections Nurse 2's handoff](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1662#issuecomment-7132486530).

This milestone adds a **callback-free, data-only comparison path** while keeping the legacy API for disposable CI compatibility. It is not an authenticated custodian endpoint.

- `native_outcome_candidate_shadow_v0.inspect_supplied_candidate(original=..., candidate=...)` accepts a previously obtained plain candidate **value**, invokes no provider and reports `lookup_count=0`. A callable, dict subclass, missing or malformed claim cannot execute as an injected recovery provider. The legacy `inspect_candidate_once()` remains test-only and is explicitly documented as unsafe for privileged recovery because it can execute caller-supplied code.
- `native_original_attempt_recovery_join_v0.inspect_original_attempt_snapshot(..., candidate_snapshot=...)` validates the original action/request/nonce/exact canonical wire-frame SHA-256 **first**, then compares the already-supplied candidate, then verifies the recorded signed Ed25519 host receipt using a verifier constructed locally from the caller-supplied **exactly 32 plain public-key bytes** (`pinned_receipt_key`). A key object, byte subclass or mutable buffer is refused without invoking its methods. The original nonce and request ID are also hashed independently and must match the fingerprint's component commitments before either evidence source is inspected. It never invokes a candidate provider, opens a socket, performs an issuer lookup, sends a command, reads a database or acquires permission.
- The legacy and snapshot paths share the same original-frame validation and output classification, so a compatible candidate and signed frame remain `UNKNOWN_HOLD` with `safe_actions=()` and **all** retry, BEGIN, CANCEL, RECOVER, consent, enrolled issuer, protected current history, terminal settlement and production authority flags FALSE.
- A snapshot is **not automatically authentic** because it is a Python dict. Neither it nor an old signed receipt can establish a protected antirollback history head, original issuer, original gateway process/seat, human authorization or actual effect/no-effect. There is no frozen C3e/C4b/C5 wire format, capability token, trust-on-first-use public key, or privileged native attachment in this milestone.

## HOW TO USE

No CPU++ changes. `CPU++ → SETTINGS → CONNECTIONS → VIEW SIGN-IN STATUS` remains read-only, with native Sign-In, Cancel, Recover and Retry disabled.

Run only in disposable developer/CI setup:

```sh
python3 -m unittest discover -s tests/identity -p 'test_native_original_attempt_recovery_join_v0.py' -v
```

The native caller must not use the legacy callable API for real protected recovery. The snapshot fixture API now expects `pinned_receipt_key` as raw 32-byte public-key material rather than an executable Python key object; the separate legacy CI API retains its original object signature. Future separately authorized DOC 1 / DOC 2 / Identity C5 owners must provide an independently authenticated, bounded, query-only producer and a validated receipt/current-history contract **before** any external snapshot is taken as authoritative. Nothing in this PR enables that connection.

## VERIFY

The extended suite (51 original-attempt tests: 45 inherited plus six new) covers genuine synthetic Ed25519 signed BEGIN, STATUS, CANCEL and RECOVER fixture values; actual signed `AUTHENTICATED` and `UNAVAILABLE` status; missing/malformed/sideloaded candidate values; executable Python callable and active dict subclass and hostile plain-dict key/str-subclass key refusal **before hash/equality dispatch**; changed original command/nonce/frame/seat/history/epoch; wrong receipt key; malicious verifier-object dispatch, invalid key byte lengths/types, valid raw Ed25519 pins, and false component commitments even when the overall frame digest matches; stale sequence; replay; no raw secret data; legacy output compatibility; and a static assertion that the new snapshot entrypoint never references the callback-based comparator.

The workflow also reruns the inherited 16 candidate, 19 recorded signed-receipt, 16 local HOLD, 54 signed native-client and 2 mandatory adapter-only tests, plus CPU++ offline protection. Exact-head logs and all required checks must be verified after PR creation. **No CI PASS is asserted before inspection.**

## WATCH OUT FOR

A Python object supplied by an untrusted caller is not a verified protected custodian response. The pure consumer does not itself establish remote process trust, network egress policies, provenance or cryptographic enrollment, and cannot make an arbitrary upstream collector read-only. In particular, the user-provided public key and historical signed command receipt are not a fresh protected terminal settlement. The original process-local fingerprint disappears after crash/restart.

The legacy `inspect_original_attempt_once()` and `inspect_candidate_once()` remain for **CI compatibility only**. Because they accept and invoke injected functions, they are explicitly inappropriate for native production wiring. The new snapshot path has no callback parameter or caller-supplied verifier execution. Its plain-byte pin is still caller-controlled and not proof of independent enrollment. This is an input boundary, not a sandbox against an attacker already executing code inside the process. Do not use it as a substitute for an independently approved query-only adapter.

DOC 1's [#2432 Forest F1–F6](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2432) is an architecture RFC, **not** an enrolled Identity custodian. DOC 2's C4b Silverblue observations do not establish the original Identity command effect. Forest C5/B6 and Hospital C5 do not confer Identity BEGIN/CANCEL/RECOVER consent. Production Sign-In / Forest private access / native authorization remain HOLD.

## CHECKLIST

- [x] Recheck current Syntagma, shared source, main, reviews, DOC 1/2 ownership and Identity C5 gap.
- [x] Add callback-free candidate validation, reject executable dictionary keys before hashing, pure original-attempt snapshot join and adversarial regressions.
- [x] Preserve legacy fixture and mandatory native adapter boundaries.
- [x] Construct the snapshot verifier from plain public-key bytes and reject false raw component commitments before evidence inspection.
- [ ] Exact-head GitHub CI and raw result verification.
- [ ] Independent Nurse 2 **pre-merge** source/security review.
- [ ] Operator merge decision.
- [ ] Actual independently enrolled protected Identity issuer, current history, original gateway/seat, one-use C5 intent and terminal result.

## NEXT

Nurse 2 reviews exact-head differences for callback execution, original correlation before comparing snapshots, non-authority output, and unchanged adapter/CPU++ gates. Next protected development work belongs at the owner-approved C3e/C4b/Identity C5 trust boundary, not by promoting more untrusted claims.

## DECISIONS

GitHub-only DOC 6 development. No workstation/NAS writes, credentials, keys, socket/transport integration, provider login, other worker source, live Hospital registration, runtime activation or automatic merge. **PRODUCTION SIGN-IN HOLD.**
