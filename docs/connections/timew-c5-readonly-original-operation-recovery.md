# 🏥💜 DOC 5 // Immutable original-operation recovery lookup INTENTS (CI only)

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · TimeW C5 Scope A  
**STAFF ROLE //** DOC 5, external Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT //** Protected TimeW C5 one-use SPENT, revocation and uncertainty recovery  
**STATE //** Strict non-authorizing lookup **plan** for future independently enrolled services. **NOT** an accepted packet, socket, endpoint, current-head verification or native restore implementation.  
**PRODUCTION TIMEW RESTORE // HOLD**

## IMPLEMENTATION

The additive `tests/connections/timew/TimeWC5ReadOnlyRecoveryPlanReference.py` consumes the **existing** DOC 5 `TimeWC5ReviewShadowReference._validate_original` without changing it. It accepts one immutable caller-supplied original TimeW Scope A claim containing the exact selected window/source/intent digests, original C5 grant and operation UUIDs, issuer epoch and seat/session, checkpoint/window, SwayPX diagnostic boot/lifetime/output/workspace/scale/transform and strict original binary64 before CURRENT / target PENDING.

For precisely defined *uncertainty circumstances* (lost C5 SPENT reply; crash after possible spend; TimeW still PREPARED; native resize/move reply lost; native timeout; native host restart; revoke after possible spend), it returns two frozen **read-only lookup descriptions**, never commands:

1. A **C5 protected history lookup INTENT** asking about the **original** TimeW-only grant, operation, issuer epoch, binding hashes, seat/session and historical validity interval. **An actual independently enrolled antirollback custodian and current-head/revocation proof are missing.**
2. A **native selected-XDG terminal lookup INTENT** concerning the **same original operation**, original selected object/lifetime/seat/output and exact before/target binary64 bits. **An actual independently enrolled SwayPX terminal receipt source, per-step outcome and final selected-view frame are missing.**

These are **local in-memory immutable dataclasses**, not a wire format or an approved API. No keys, secrets, public enrollment root, Unix socket, network request, database, process command, TimeW QML, compositor callback, native machine address or authority are created. There are **no provider callbacks** and no send/execute/retry method. The reference only describes what must later be looked up by a separate, independently reviewed reader.

Every result, including a perfectly valid original claim, is `UNTRUSTED_DUAL_READ_ONLY_LOOKUP_INTENTS_UNKNOWN_HOLD`. Invalid original/cause yields no lookup descriptions. Every output has hard-false protected-SPENT/current-head/human/producer/settlement/native/second-spend/move/retry/undo/production flags and `safe_actions=()`. There is **no** positive consent, native command or ready-to-retry state.

## HOW TO USE

In disposable CI only:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_readonly_recovery_plan_reference.py
```

The dedicated workflow reruns the existing DOC 5 exact review, provider-neutral untrusted custodian probe and native UNKNOWN/HOLD trace cases. This is **not** a user-facing recovery button and requires no local workstation changes.

## VERIFY

Hostile checks require:

- Exactly two separate conceptual lookup roles, both keyed to the **original** operation/grant, never a new grant/command nonce.
- C5 lookup bound to original issuer/source/selection/intent hashes, seat/session and history interval; native lookup bound to original checkpoint/window/boot/lifetime/output/scale/transform and bit-exact before/target values. It does not invent a signed serial byte encoding.
- One-ULP changes remain distinct, no decimal rounding; different original operation cannot inherit prior lookup.
- Strict rejection of corrupted/missing/extra fields, cross-domain C3e Identity/Hospital claims, changed seat, malformed source, invalid geometry phase, out-of-order resize/move steps and invented execution causes.
- Caller mutating the original dict after construction cannot alter the frozen lookup descriptions; repeated read-only planning is deterministic, but **does not re-spend or issue a command**.
- Expiry does **not** destroy historical SPENT/UNKNOWN evidence. Read-only reconciliation after expiry may still be necessary, but it is never permission to retry, regrant, undo or move.

## WATCH OUT FOR // Explicitly unfulfilled protected admission

The only real source so far is caller-controlled development state. A local C5 `SPENT` SQLite row, future NAS path, source claims, string names like `PROTECTED`, an old signed hash or matching binary64 cannot prove independent current history. A SwayPX diagnostic `READY`, configure serial, `CURRENT`, `SCENE`, or synthetic `PRESENT` cannot prove real selected-view settled terminal movement.

**No production packet fields, key roles, signer, expiry policy, challenge protocol, persisted outbox/receipt retention or read-only endpoint are accepted by this new source.** Query intent tuples are purposely not passed to any provider; cross-owner current trust and real native receipt contracts still require ACCEPT/REVISE/HOLD. Do not treat the two intents as an instruction to perform network calls on the current desktop.

The owner disposition responding to [SwayPX #185](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/185) is recorded in [TimeW #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7108697529). SwayPX owns authentic selected XDG/native receipt; TimeW owns immutable checkpoint/geometry and any native consumer; DOC1/2 own independently enrolled source/host trust; DOC5 owns genuine TimeW operator approval and independently protected one-use SPENT/recovery. The operator's local-first ordinary data / future separately protected hardware decision remains settled, not a current root/custodian choice.

## CHECKLIST / NEXT / DECISIONS

- [x] Preserve original operation identity across recovery and prevent automatic second spend/resize/move.
- [x] Separate C5 current-history and SwayPX terminal-producer *lookup purposes* without choosing a wire.
- [ ] Exact-head CI + independent Nurse 2 **pre-merge** scoped source review.
- [ ] Operator merge disposition.
- [ ] Independently enrolled C5 antirollback current-head/one-use SPENT keeper and genuine H0 operator approval.
- [ ] Signed SwayPX actual selected-frame resize/move terminal proof, read-only recovery transport, exact TimeW fail-closed consumer, native acceptance and operator production permission.

**No production TimeW Restore, C5 grant issuance, signed native event, automatic retry, undo or regrant is permitted.**  
