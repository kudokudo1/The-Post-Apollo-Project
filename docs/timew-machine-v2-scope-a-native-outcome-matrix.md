# 🏥💜 TimeW MACHINE // Scope A native outcome uncertainty matrix (CI-only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE · Desktop & Brave Recovery  
**ROLE:** External Hospital-compatible DOC; live Hospital registration unverified  
**SCOPE:** Operator-selected one currently live floating nonfullscreen surface, same compositor session, **geometry only**. Browser-instance identity and tab restoration are separate Scope B.  
**STATE:** Source-only TimeW test fixture, no installed issuer, C5 authority, compositor command or production Restore

## IMPLEMENTATION // Actual bytes, process and storage boundaries

Existing TimeW `services/time/MachineV2GeometryJournal.py` writes `prepared`, `dispatching`, `uncertain_requires_review` and `verified_fixture_placement` state to a private SQLite database. A local journal entry tells us which state **TimeW recorded**. It does not independently prove that C5 authorized or spent the exact action, or that a specific Wayland surface moved. A crash may leave one system knowing more than the other.

Existing SwayPX [`sway/commands/resize.c`](https://github.com/kudokudo1/Post-Apollo-SwayPx/blob/fb064cf3c82aa7b9e8d2375bb631773d5eb5a12f/sway/commands/resize.c#L341-L400) updates floating container `pending.x -= grow_width/2` and `pending.y -= grow_height/2` when resizing. C integer division truncates toward zero. SwayPX owner [draft #166](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/166) flagged this as a correction to earlier TimeW synthetic fixtures that held x/y fixed.

The new **test-only helper** `tests/timew/TimeWScopeAOutcomeHoldPreflight.py` does two things:
1. Computes a **source-linked centered-resize arithmetic hint** with correct C signed-integer rounding. This hint is *not* a native accepted after-resize rectangle: actual constraints, arrangement, configure and committed compositor state may differ. TimeW must use the real protected observed rectangle before a future guarded move.
2. Compares a **real isolated TimeW SQLite journal view** with caller-supplied **simulated** C5 spend status (`absent / refused / unknown / spent`), claimed resize/move receipts, selected object lifetime/session/seat, and claimed after-resize/final rectangles. The result is always diagnostic and **never** authorizing.

The `COMPLETE_UNTRUSTED_FIXTURE_ONLY` status says *only* that the simulated C5, journal, claimed receipts and geometry are internally consistent. Even this status returns `restore_allowed=false`, `production_authorized=false`, `native_geometry_dispatch_allowed=false`, `automatic_retry_allowed=false`, `automatic_undo_allowed=false`, `safe_actions=[]`, with **all protected source/C5/receipt verification flags FALSE** and manual review required.

No TimeW production service, SwayPX code, Connections/C3e/C4b implementation, C5 service, Hospital source, installed key, journal schema, UI or live computer is changed. The new files exist under `tests/timew/`, a dedicated CI workflow and this document. There is no command runner, socket, listener, signer, native grant or active one-use spend.

## VERIFY // Required fixture matrix

`tests/timew/test_timew_scope_a_native_outcome_hold.py` exercises:
- **128 combinations** of local SQLite journal phase (`prepared` vs `dispatching`), simulated C5 spend, resize-ack and move-ack statuses; every combination preserves no-authority/no-retry.
- A real isolated SQLite `prepared` row reopened after simulated process restart: if C5 claims **SPENT**, the result is `UNKNOWN_HOLD`, never silently `unspent`.
- A real `dispatching` row with a lost move acknowledgment, mismatched final rectangle, missing post-resize observation, revoked/stale object lifetime or seat/session drift: **`UNKNOWN_HOLD`**.
- A local `verified_fixture_placement` terminal marker that **cannot** substitute for native C5/source receipts.
- A simulated correctly matching final state that is still **`COMPLETE_UNTRUSTED_FIXTURE_ONLY`**, never real Restore.
- Positive/negative odd-number resize deltas (C truncation toward zero), unchanged dimensions, and a post-resize x/y different from the mathematical hint. The latter is **not** silently refused merely because an unauthenticated predicted center differs.
- Malformed local journal and surface identity, injected native permission flags, and absence of an executable entrypoint.

## HOW TO USE

Run the dedicated CI test only in GitHub Actions:

`python3 -B -I tests/timew/test_timew_scope_a_native_outcome_hold.py`

The workflow also runs the already merged real SQLite journal regression and selected-surface continuity regression. CI variables are required; no test writes to the operator's workstation or XDG storage.

## WATCH OUT FOR

The independent **C5 TimeW-specific grant spender is not implemented or approved**. All C5 statuses in this matrix are caller-provided claims; there is no protected antirollback or grant history. Likewise, a claimed compositor observation does not attest to a real selected Wayland object. A C3e Linux packet sender with valid kernel credentials is not by itself a protected SwayPX selection, installed issuer or approved release.

The resulting native design still requires the SwayPX owner to implement and test protected surface selection, epoch/lifetime revocation, guarded commands and post-resize receipts; Connections C3e/C4b owner to authenticate installed source/release/process/host/seat and challenge; C5 owner to durably spend the one-use exact intent before any side effect and reconcile uncertain crash outcomes. No one may promote this fixture's `COMPLETE` string into a native authorization.

## CHECKLIST

- [x] Source-only TimeW test of current journal and provisional C5/receipt states
- [x] Correct SwayPX floating centered-resize arithmetic isolated from protected observation
- [x] No retry/undo or native side effect regardless of synthetic result
- [ ] Exact-head GitHub Actions and independent Nurse 2 review
- [ ] SwayPX/C3e/C4b/C5 explicit owner ACCEPT/REVISE/HOLD and native interface acceptance
- [ ] Real Fedora compositor tests, protected spend/reconcile acceptance and operator production release

## NEXT // DECISIONS

Review under canonical [TimeW trust issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067) and [owner ledger #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119). **Scope A first, Scope B separately later. Production Restore HOLD.**
