# 🏥💜 DOC 5 // Dual-source read-only C5/native recovery return comparison

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections C5 ↔ TimeW Scope A  
**STAFF ROLE //** DOC 5, external Hospital-compatible, live registration not verified  
**ASSIGNMENT //** Original-operation C5 one-use SPENT / revocation / crash uncertainty recovery  
**STATE //** Additive source + CI reference, **not** a production wire, signed receipt, enrolled provider, trusted transport or authorized native command  
**PRODUCTION TIMEW RESTORE // HOLD**

## IMPLEMENTATION // From lookup intents to hostile return matching

[DOC 5 #2333](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2333) merged and independently reviewed a pair of **immutable, non-executable original-operation lookup intents**. [DOC 5 original test-only custodian probe #2228](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2228) separately exercises one caller-provided C5 result. Neither actually contacts a protected authority. The new `tests/connections/timew/TimeWC5DualRecoveryReturnReference.py` joins **neither service**: it compares two supplied fixture **return snapshots** against the already-created original-operation plan.

1. The **C5 candidate** uses the existing DOC 5 provider-response *test fixture schema*: its TimeW-only audience/action/grant/operation/issuer epoch and source/intent/selection hashes, seat/session, claimed ledger state, sequence/head and terminal hash. It compares only fields the old C5 response actually exposes. **Important gap:** that C5 snapshot does *not* attest original `issued_ms`/`expires_ms`; those remain in the original immutable plan only and must not be silently treated as independently current validity evidence.
2. The **native candidate** is a deliberately untrusted **new test fixture shape**, not a proposal to standardize a native packet. It echoes original grant/operation, selected XDG lifetime, seat/session/output/workspace/scale/transform and exact before/target binary64 bits. It includes synthetic `resize_observation`, `move_observation`, output PRESENT and claimed selected-frame booleans, plus its **own** sequence/head. Native and C5 heads are separate: equality between independent sources is not expected or required.
3. A **caller-provided previous head for each separate source** can reveal obvious rollback (sequence regresses), fork (same sequence different hash), or inconsistent advancement (sequence advances with unchanged hash). All prior head snapshots are themselves untrusted, so a match does **not** prove rollback resistance, independent enrollment or protected currentness.
4. Strict exact-key checks reject surplus positive authority fields, mis-scoped operation/seat/source, changed issuer, wrong XDG lifetime, output/topology drift, invalid source strings/types and one-ULP exact-binary64 changes. A syntactically correct response remains a **diagnostic snapshot** only.
5. Outcome classifications distinguish C5 ACTIVE with claimed native effect, revoked/unknown C5 history, contradictory READY+TIMEOUT, a claimed move following a timeout/unsettled resize, output PRESENT without selected-buffer attribution, and a caller's forged `selected_xdg_frame_claimed=True`. Even entirely matching `INDEPENDENT_CANDIDATE` + `PROTECTED_CANDIDATE` input is `MATCHED_BUT_UNENROLLED_C5_NATIVE_UNKNOWN_HOLD`.

**Every return is a frozen `Comparison` with false authority, C5 SPENT/current-head, operator, native signer/ACK/selected-frame/terminal, second-spend, MOVE, retry, undo, and production flags; `safe_actions=()`.** The function only consumes values; it does not call a provider, connect to a network or socket, read/write local SQLite, sign/enroll keys, operate the compositor, or execute a command.

## HOW TO USE

Disposable GitHub Actions only:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_dual_recovery_return_reference.py
```

The dedicated workflow also reruns 20 previously merged original-operation recovery-intent tests, 12 local custodian-boundary tests and 28 native-outcome negative checks. The tests do not read TimeW's actual local v3 data and do not modify the operator's workstation.

## VERIFY / WATCH OUT FOR

This milestone is a **two-return integration refusal** in source/CI, *not* the actual protected custodian. Caller inputs can all be forged, including seemingly legitimate sequences/heads, receipt hashes, `SPENT`, `READY_ONLY`, `output_present=True` and `selected_xdg_frame_claimed=True`. No packet is authenticated. SwayPX [#187](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/187) observes actual post-scene geometry; [#188](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/188) observes **output-level** PRESENT but not a selected-XDG final buffer. Both remain separately owned diagnostic drafts. This comparator cannot transform those observations into settled selected-view receipts.

A future **real** independently protected C5 issuer/custodian will require its own approved read-only status endpoint, fresh independent source/current-head enrollment, durable atomic pre-action SPENT and revocation precedence. A future installed SwayPX source needs independently enrolled receipt signing, actual selected view/seat and ACK+frame-specific settlement, with TimeW's separately reviewed fail-closed consumer. None of those external interfaces or their byte schema is selected by this test source. Original local TimeW layout data remains local-first and untrusted, with the operator-approved separate protected hardware migration deferred.

**No auto retry, regrant, second SPENT, subsequent MOVE from READY/CURRENT/SCENE/output PRESENT, undo or Restore.** TimeW operation identity must not change during recovery merely because a packet is absent, a provider times out or a local ledger rolls back.

## CHECKLIST / NEXT / DECISIONS

- [x] Preserve DOC 5 ownership; leave TimeW, SwayPX, DOC 1, DOC 2, Autoscroll and Hospital source untouched
- [x] Compare two independent purpose-labeled **untrusted** return snapshots against #2333's immutable original operation
- [ ] Exact-head CI and independent Nurse 2 review, operator merge disposition
- [ ] Cross-owner ACCEPT/REVISE/HOLD for *actual* separately administered C5 read-only recovery, custody/current-head, source authenticity and final native receipt
- [ ] Real hardware enrollment, genuine operator approval, rollback/crash native tests, separate operator production activation

**DECISION //** This reduces risk of accidentally accepting contradictory recovery data. It does **not** settle or authorize the historical operation. Production TimeW Restore remains HOLD.
