# 🏥💜 DOC 5 // TimeW Scope A exact-value consent-review shadow

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections C5 ↔ TimeW Scope A  
**STAFF ROLE:** DOC 5, external Hospital-compatible; live registration unverified  
**PHASE:** CI-only review mismatch reference  
**AUTHORIZATION:** NONE · Production TimeW Restore HOLD

## IMPLEMENTATION

The isolated `tests/connections/timew/TimeWC5ReviewShadowReference.py` models the **minimum information a future trusted operator review must convey, without pretending that the review is actually displayed or trusted**. It imports, without altering, TimeW's merged `services/time/MachineV2ExactLogicalGeometry.py` value-only candidate (#2207). It reuses DOC 5's TimeW-specific grant claim grammar from #2196.

An **original fixture** records the exact grant/operation IDs, audience/action, selected-surface/source/intent hashes, original session, seat and issuer epoch, checkpoint ID, saved window key, compositor boot/lifetime generation, workspace, output, output scale and transform, issue/expiry, before and target exact logical rectangles and the named operation `resize → observe-after-resize → move → verify-final`. All inputs are caller-supplied fixtures, **not independently authenticated compositor/operator claims**.

A deterministic **shadow review transcript** includes:
- Entire source/selection/intent and operator seat context, no title or PID shortcut.
- The selected checkpoint/window, lifetime/output/workspace/scale and transform.
- Each finite logical coordinate in both readable decimal and lossless hexadecimal float notation, preserving real y=92.5 and target h=700.5.
- Clear `CURRENT` / `PENDING` **untrusted value phase labels**, not trusted transaction/settled evidence.
- Full reviewed action order and expiry.

The evaluator requires identical original/presented fields including all four binary64 bit patterns, rejects omitted/extra data, rounded/one-ULP-substituted values, stale lifetime or output, mismatched seat/issuer/grant, and missing/inexact shadow transcript. A simulated locked seat or absent selected surface holds. Even exact agreement returns **MATCHED_BUT_UNTRUSTED_SHADOW_HOLD**.

**Crucial limitation:** the person, UI, seat and native geometry source have not been authenticated. Both objects, including the claim that the seat is unlocked, are created by the caller. This shadow is a **negative test fixture**, not interactive user consent, a verified display, a protected grant, or a native approval.

## NOT A WIRE, STORE OR TRUST ROOT

`postapollo.connections.c5.timew.review-shadow-fixture.v1` is a private test label only. The comparison operates on in-process `ExactLogicalRect` values. Its use of Python float hexadecimal display strings and canonical numeric comparison **does not choose native message byte order, field serialization, signing schema, trusted UI layout, C5 audience key or production proof representation**. SwayPX [#173](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/173) and [#174](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/174) still need joint owner decisions about source, queued/ready/timeout/current/scene/present stages, real settled receipt and coordinate space. In particular, SwayPX can copy target into CURRENT on a configure timeout; CURRENT alone is not proof of successful client or scene placement. Old TimeW integer checkpoint/journal formats remain untouched.

Every result unconditionally sets these to false: `production_authorized, native_action_allowed, human_consent_verified, trusted_display_verified, selected_surface_authenticated, external_custody_verified, spent_grant_verified, native_terminal_receipt_verified, retry_allowed, undo_allowed`. It returns empty `safe_actions` and has no socket, DB, signer, Polkit, QML, SwayPX command or callback to actuate a window.

## HOW TO USE / VERIFY

From a disposable checkout, ordinary user only:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_review_shadow_reference.py
```

The dedicated GitHub workflow also re-runs inherited C5 storage-independent recovery tests and TimeW's existing exact-value suite. The new adversarial tests cover 17 cases with substitutions of fractional/one-ULP geometry, displayed strings, grant/seat/source, checkpoint/window/output/scale/transform, stale epoch, invalid phase/bits, forged approval, expired clock and fake unlocked flags.

## WATCH OUT FOR

- Actual future operator review must be drawn by a **trusted display path**, with an independently established active unlocked seat and genuine affirmative input. Merely making a QML screen that looks identical to this reference cannot certify consent.
- The reviewed target must bind a *specific* checkpoint/window key and exact geometry and output/workspace semantics. The target's PENDING value label is **test-only conceptual**, not a claim that SwayPX queued or accepted a command.
- Real C5 must spend a separately protected one-use grant **before native side effects**; SPENT with TimeW PREPARED, lost resize ACK, timeout/current copy or lost move ACK remains UNKNOWN/HOLD. The future protected custodian must hold the independently current head and evidence. DOC 1's local C3e history #2224 and DOC 5's own SQLite #2196 are rollbackable development fixtures.
- Shared physical custodian infrastructure may be proposed, but **Identity, TimeW, Hospital and Forest must not share authorization grants/audiences/keys/roles** by accident.
- DOC 1 owns C3e, DOC 2 owns C4b, TimeW owns native value/consumer, SwayPX owns compositor selection/transaction/command, DOC 5 owns TimeW C5 exact consent and SPENT contract. No cross-owner edits in this milestone.

## CHECKLIST / NEXT / DECISIONS

- [x] C5 TimeW consent boundary remains owner **REVISE** at [#2163](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2163).
- [x] Isolated exact-value/readable-transcript negative fixture, strict same-operation comparison.
- [ ] Exact-head CI and independent Nurse 2 pre-merge security review.
- [ ] Operator merge acceptance, separate from future installation.
- [ ] Joint C3e/C4b/TimeW/SwayPX owner acceptance of exact native selection/geometry source and proof wire.
- [ ] Independently enrolled current-head custodian, actual trustworthy human consent UI/gesture and protected one-use SPENT, native per-step receipts, crash/rollback/revocation acceptance.

**No code in production runtime changed, no desktop/host or signing-key writes, no live Hospital attachment, no window action or production release.**
