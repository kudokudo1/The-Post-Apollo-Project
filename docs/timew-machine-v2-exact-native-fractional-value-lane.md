# TimeW Scope A // Exact fractional logical geometry value lane

**Patient:** The-Post-Apollo-Project  
**Room / staff:** TimeW MACHINE · Desktop & Brave Recovery / TimeW owner DOC (external Hospital-compatible, no verified live registration)  
**Status:** Source-only, import-only, untrusted value reference; no production native authorization or command path.  
**Origin:** [SwayPX draft #172](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/172) observed a *real mapped XDG window* with **pending logical geometry** `x=259, y=92.5, width=1402, height=872`. [SwayPX #173](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/173) proposes a binary64 exact-geometry reference. Its value/phase approach is useful; its wire format and trust are NOT accepted.  
**Owner decision:** [TimeW #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067#issuecomment-7085803105), preserve V1/V2 and add a separate non-authorizing exact-value lane. Scope A first, Scope B Brave identity later.

## What this implementation actually does

New TimeW-owned files:

- `services/time/MachineV2ExactLogicalGeometry.py`: pure immutable `ExactLogicalRect` with **version=1**, `phase=PENDING|CURRENT`, four native in-memory IEEE754 binary64 bit patterns. `capture_value` validates finite logical coordinates in signed 32-bit layout bounds and finite widths/heights in [1, INT32_MAX]; canonicalizes negative zero to positive zero. `read_value` revalidates every raw bit pattern and refuses NaN, Infinity, wrong version/phase, negative-zero aliases and forged types. `exact_value_equal` checks both values and all phase/version/four-bit fields, never tolerance matches.
- `tests/timew/test_machine_v2_exact_logical_geometry.py`: real observed fractional example, 256 deterministic fractional samples and one-ULP differences, phase distinction, invalid/forged inputs, canonical zero, strict value-only surface and **existing V2 projection/store/journal fractional refusal**.
- Isolated GitHub Actions and this design/status document.

The model is a **Python in-process value object**, not a native socket message or chosen serialization. The internal bit-pattern integer fields are NOT independently trusted receipts or a signed database representation. No JSON field names, wire endianness, signature transcript, protected sender, or geometry execution endpoint are selected by this implementation.

## Existing TimeW behavior intentionally preserved

The following remain unchanged and **integer-only**:

- `MachineGeometryV2.py` projection, `MachineGeometryStoreV2.py` paired V1/V2 SQLite snapshot.
- `MachineV2GeometryJournal.py` local crash/operation journal, including `prepared/dispatching/uncertain_requires_review` and one-use local refusal.
- `MachineV2SelectedSurfaceReview.py` deny-only fixture, `MachineV2FloatingPilot.py` disposable runner.
- All TimeW QML, checkpoint/restore controls, C5 and Connections components.

In particular, do **not** silently widen the legacy serializer to floats, rewrite user checkpoint data, or treat this value model as a native `CURRENT` witness. The old pilot's keep-x/y-after-resize assumption is not real SwayPX behavior. A native resize can center and change both x and y.

## What this DOES NOT establish

Even a bit-exact `CURRENT` record cannot prove a compositor transaction actually settled. `PENDING` is a proposed compositor layout state, not a final receipt. Neither phase authenticates a physical operator-selected XDG surface, seat/session/epoch, output/workspace/scale, C3e/C4b installed producer, protected source signature, C5 one-use SPENT, resize or move result, nor suitability of a saved target across monitors.

Production native Restore remains completely unwired. There is no CLI, daemon, key, socket, filesystem mutation or Sway command in the new module.

## Required integration decisions and gates

1. **SwayPX owner:** Source-protected operator gesture/selection with exact object lifetime and revocation, independently observed and transaction-bound post-resize `CURRENT` geometry and native command receipts. Agree on canonical protected numeric wire before binding signature/consent.
2. **C3e/C4b owner:** Independently retained installed compositor release/source/host/seat/challenge enrollment and source-receipt verification; Linux peer process/executable facts alone are insufficient.
3. **C5 owner:** [TimeW #2163](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2163) is REVISE: exact reviewed versioned source values in visible consent, independently custodied durable one-use SPENT before first side effect, and no retry/undo on uncertainty.
4. **TimeW owner:** After these accepted contracts, build a separately reviewed native receipt consumer and fractional checkpoint/target persistence version. Do not migrate historical records in place; preserve the existing journal as untrusted local evidence, not a C5 ledger. A crash gap or lost outcome stays `UNKNOWN/HOLD`.
5. **Nurse 2/operator:** Exact-head review and CI, then separate owner merge/installed-host/production decisions. This draft does not authorize any of them.

## Verification

Run from the repository root in an isolated test environment:

```sh
python3 -B -I tests/timew/test_machine_v2_exact_logical_geometry.py
python3 -B -I tests/timew/test_machine_geometry_store_v2.py
python3 -B -I tests/timew/test_machine_v2_geometry_journal.py
```

**Production Restore: HOLD.** No local workstation, installed SwayPX or user window was modified.
