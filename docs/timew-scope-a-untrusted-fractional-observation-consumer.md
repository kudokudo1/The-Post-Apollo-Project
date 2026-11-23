# TimeW Scope A // Untrusted fractional observation consumer

**PATIENT:** The-Post-Apollo-Project
**ROOM / ROLE:** TimeW MACHINE · Scope A / owner DOC (external Hospital-compatible, live registration unverified)
**STATUS:** SOURCE/CI ONLY, denial-only, candidate values. **PRODUCTION RESTORE HOLD.**
**BASE:** TimeW [#2207](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2207) (merged, Nurse 2 retrospective scoped PASS), SwayPX [#174](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/174) and [#176](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/176) (draft, reviewed source/native diagnostic PASS).

## Purpose and mechanism

The existing \`MachineV2ExactLogicalGeometry.py\` provides an immutable untrusted versioned Python value with four exact binary64 logical-coordinate bit patterns and two distinct phases: PENDING and CURRENT.

The additive \`MachineV2FractionalObservationReview.py\` reads those values *in memory* and compares a provisional four-step observation: before CURRENT, target PENDING, observed CURRENT after resize, and a later CURRENT after an independently proposed move. It checks exact dimensions at the resize point and exact complete target values at the final point. No rounding and no assumption that resize preserved original x/y are allowed. A center-adjusting resize can move x/y, so a new post-resize reading is required for even a value-only comparison.

The supplied diagnostic stage labels \`READY_REPORTED\`, \`TIMEOUT_FORCED\`, and \`UNKNOWN\` are **caller-created** and intentionally NOT a canonical native wire, configure receipt, or signed transaction state. If either stage is timeout/unknown or any intermediate observation is missing, the status is \`UNKNOWN_HOLD\`. Mismatched values yield \`GEOMETRY_MISMATCH_HOLD\`. Even perfectly matching values with both ready-reported labels yield \`MATCHED_VALUES_UNTRUSTED_HOLD\`. Every result hard-denies Restore, native actions, source/selection/ACK/settlement/C5 authority and returns no safe actions.

Why: SwayPX #176 observed that the actual timeout handler can lead to copying CURRENT and arranging the scene without successful configure ACK. Neither a CURRENT match nor scene arrangement proves frame presentation, authorized target, or permission to issue a move.

## Compatibility and ownership

- **TimeW:** New pure, import-only value consumer and regression suite. No V1/V2 checkpoint, SQLite, journal, restore QML, or existing command runner changed. Fractional input to those older stores still refuses.
- **SwayPX owner:** Real protected selected-window identity and native configure/timeout/frame/settlement observations plus per-step receipts. Its CI-only callback trace is not a signed receipt contract.
- **DOC 1 / DOC 2 Connections:** Installed source/release/host/seat producer trust and independently enrolled signing history.
- **DOC 5 C5:** Exact reviewed intent, authentic interactive consent, protected spent-before-effect one-use grant and independent rollback protection.
- **Nurse 2:** Independent source and CI review at the exact branch head.
- **Operator:** Separate decisions on merge, installation, native trial, and eventual production authorization.

There is deliberately **no serialized receipt schema, byte order, native IPC transport, key, network listener, persistent fractional checkpoint schema, runtime importer, trust promotion, retry or undo** in this source. The in-memory value revision is not a canonical protocol version. Joint owner approval must precede an actual authenticated receipt parser and a new versioned durable checkpoint format. Do not retrofit these values into the historical integer-only V1/V2 rows.

## Verification

On an isolated repository checkout:

\`\`\`sh
python3 -B -I tests/timew/test_machine_v2_fractional_observation_review.py
python3 -B -I tests/timew/test_machine_v2_exact_logical_geometry.py
python3 -B -I tests/timew/test_machine_geometry_store_v2.py
python3 -B -I tests/timew/test_machine_v2_geometry_journal.py
\`\`\`

The new workflow is source/CI-only and cannot move a window. **Native Restore remains HOLD.**
