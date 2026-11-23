# 🏥💜 DOC 5 // TimeW Scope A C5 SPENT ↔ native outcome HOLD

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Connections C5 ↔ TimeW Scope A · DOC 5  
**PHASE:** Synthetic native-outcome and one-spend recovery reference  
**AUTHORITY:** NONE · Production Restore HOLD  
**HOSPITAL:** External compatible; live Session/Assignment registration unverified

## IMPLEMENTATION // C5 consent is not window completion

`tests/connections/timew/TimeWC5NativeOutcomeHoldReference.py` interprets an in-memory diagnostic sequence. It reuses the original C5 grant and TimeW selected-window exact-geometry **fixture grammar**, while adding **no native command executor or trusted receipt**. It tests C5's ownership boundary when a purported one-use SPENT grant and the compositor's actual normal or timeout callback semantics are considered together.

The tests encode the SwayPX [#176](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/176) real native discovery: a *normal* transaction can record READY → CURRENT copy → SCENE arrangement, but the **forced timeout** also records TIMER_TIMEOUT → CURRENT copy → SCENE arrangement with client acknowledgement and settled presentation **unproven**. Native diagnostic callback names and order here are **synthetic test labels**, not selected, authenticated cross-process event IDs or a frozen signed wire.

The test snapshot binds one original grant/operation, exact source/selection/intent, original session/seat/issuer epoch, checkpoint/window, compositor boot and surface generation, workspace/output/scale/transform and TimeW's exact in-process fractional before/target geometry. Every fake callback must carry that same untrusted context; a changed grant, window, seat, epoch, monitor, y=92.5, target h=700.5, or other field fails closed. The code never treats matching caller-controlled context as true native provenance.

## Outcome matrix // The difference that matters

| Fixture observation | Result |
| --- | --- |
| SPENT but TimeW still PREPARED | `SPENT_BUT_LOCAL_PREPARED_UNKNOWN_HOLD` |
| SPENT + PREPARED yet resize reportedly dispatched | `SPENT_WITH_PREPARED_AND_EFFECT_UNKNOWN_HOLD` |
| Resize reported before SPENT | `RESIZE_BEFORE_SPENT_REPORT_HOLD` |
| Normal READY + CURRENT + SCENE | `CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD` |
| Normal READY + CURRENT + SCENE + reported PRESENT | `PRESENT_REPORTED_BUT_UNAUTHENTICATED_HOLD` |
| Timeout followed by CURRENT/SCENE | `TIMEOUT_CURRENT_OR_SCENE_NOT_SETTLED_UNKNOWN_HOLD` |
| Follow-on MOVE reported after timeout | `FOLLOWON_MOVE_AFTER_TIMEOUT_UNKNOWN_HOLD` |
| Follow-on MOVE reported after seemingly normal presentation | `MOVE_REPORTED_WITHOUT_TRUSTED_TERMINAL_UNKNOWN_HOLD` |
| Lost ACK, host exit, revocation after SPENT | `UNKNOWN/HOLD`, no automatic retry/undo/regrant |
| Conflicting ledger state or changed selected-surface lifetime | `UNKNOWN/HOLD` or hard refusal |

The diagnostic reasons only explain why an untrusted trace cannot establish permission. No case returns a safe native action, a completed Restore, a revocation ACK, a move-continuation capability, a replayable SPENT, or an automatic retry. A *completely consistent* fake SPENT + resize + move + PRESENT trace is still non-authorizing.

The code deliberately does **not** use the real TimeW operation journal as an independent SPENT proof. Its `PREPARED/DISPATCHING/UNCERTAIN/FIXTURE_COMPLETE` values are caller-supplied labels. The actual legacy TimeW V2 SQLite journal remains integer-only and is not read or modified.

## HOW TO USE

GitHub Actions runs the new suite in a disposable Linux runner using:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_native_outcome_hold_reference.py
```

It also runs the prior DOC 5 exact-review shadow and custodian recovery tests. No local Fedora command, root execution, signer, actual Wayland seat, SwayPX resize/move, installed service or QML UI is involved.

## WATCH OUT FOR // Where a real protected integration must differ

1. **Authenticity:** A real trusted SwayPX selected-object, transaction and per-step receipt must be rooted in DOC 1/DOC 2 approved installed producer/seat/source proof, not a caller-supplied internal pointer, app_id, serial, forged signed JSON or CI log.
2. **Human approval:** The actual operator must see the original selected window, before+target exact geometry, output/workspace and action at an independently trusted unlocked seat, and approve once. The C5 review shadow is string consistency only.
3. **Independent SPENT:** A separately administered C5 authority must durably SPEND exactly once before the *first* side effect, protect the current history against local snapshot rollback and handle revocation/rotations. Guest-local SQLite #2196 and the DOC 1 C3e local-development ledger cannot provide production authority.
4. **Two-phase native operation:** Resize → observe actual source state → move → verify final must be one bounded grant; a move can continue only under a jointly approved authenticated native receipt showing a safe prior step, unchanged original object/output/seat/lifetime and no timeout/unknown. Even CURRENT and SCENE after timeout are insufficient. Never use a second grant or blind replay.
5. **Crash:** If C5 says SPENT while TimeW is PREPARED, the resize ACK is lost, the compositor restarts or the move finality is unverified, the result is **UNKNOWN/HOLD**. After incident, only authenticated independent outcome lookup can reconcile; no automatic retry or invented rollback.
6. **Future native agreement:** SwayPX #173/#174/#176 and TimeW #2207 remain value/diagnostic candidates. Their output coordinates, signed representation, transaction generation, configure receipts, presentation and finality semantics have not been accepted as a C5 production wire.

**Ownership:** DOC 5 only changes new `tests/connections/timew/`, related doc and workflow. DOC 1/C3e owns independently enrolled provenance/custody interface; DOC 2/C4b owns installed gateway; SwayPX owns real compositor instrumentation and native selection; TimeW owns exact geometry consumer/checkpoint and command planner. Do not borrow Hospital, Forest, TASKS, Brave or Identity keys/grants for TimeW.

## VERIFY / NEXT / DECISIONS

- [ ] Dedicated exact-head GitHub CI and inherited regressions pass
- [ ] Independent Nurse 2 review **before merge**
- [ ] Separate operator merge approval
- [ ] Approved real custodian and source/seat/display/receipt wire, with native failure and recovery tests
- [ ] Final operator installation and production acceptance

No test fixture or doc here can turn on native Restore. **Production TimeW Restore HOLD.**
