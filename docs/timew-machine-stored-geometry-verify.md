# MACHINE // STORED read-only geometry verification

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE desktop recovery  
**ROLE:** External DOC succession, Hospital-compatible (not live-registered)  
**STATE:** Draft source + CI, no local desktop activation  
**PREDECESSOR:** merged PR #1658 (verified SAVE receipt)

## Goal

The operator needs to confirm that a real geometry checkpoint exists and can
be reopened in **STORED**. The existing STORED collection was backed by the
v1 legacy reader, so listing a checkpoint alone did not prove its newer v2
per-window rectangles and tiling hierarchy were available or sound.

## Implementation

The existing `MachineSaveBridgeV2.py` gains an explicit read-only action:

`python3 -B -I services/time/MachineSaveBridgeV2.py verify <UUID>`

It validates a canonical checkpoint UUID and opens that UUID with both
`MachineCheckpointStore.load` and `MachineGeometryStoreV2.load_geometry`.
It returns only the allowlisted record status and counts, without exposing
raw Sway trees, titles, window keys, browser tabs or stored private data.

Possible results are:

- `geometry_verified`: the sidecar geometry loaded, passed its checksum and
  strict v1 compatibility validation, and matches the saved checkpoint's
  monitor/workspace/window counts
- `legacy_only`: a valid historical v1 checkpoint, but no exact v2 geometry
  record. This must not appear as a fully verified geometry checkpoint
- `geometry_mismatch`: read-back records did not agree. Do not claim a
  successful geometry verification
- `error`: missing/corrupt/unsupported stored record; error message is
  bounded and doesn't expose SQLite internals or user paths

Every response is marked `read_only=true`,
`exact_restore_verified=false` and
`session_identity_verified=false`. The bridge never sends Sway IPC for
this operation.

## UI

TIME → MACHINE → STORED, choose a checkpoint with the existing arrows,
then press **VERIFY SAVED GEOMETRY**. The result appears directly above
RESTORE and reports actual monitor/workspace/window counts or identifies a
legacy/mismatched record.

The new action reuses the **existing SAVE bridge Process**, avoiding a
sixteenth QML Process or competing writer. Its in-memory selected-checkpoint
ID is checked before accepting asynchronous results, so stepping to another
row cannot attribute a verification response to the wrong checkpoint.

It clears stale verification when the list or selection changes, does not
invoke RESTORE, and doesn't rewrite the existing v1 checkpoint table. An
explicit warning reminds the operator that exact layout restoration and
Brave tab recovery are still unfinished.

## Evidence and boundaries

Tests cover:
- v1-only stored rows, which must not report geometry
- v2 geometry rows, verified by the real read-only storage APIs
- mismatched counts and a corrupted stored geometry checksum
- invalid checkpoint IDs, and no database creation on an absent record
- the actual `python3 -B -I ... verify <UUID>` CLI on a disposable
  two-output stock headless Sway session, following a real isolated SAVE
- UI source contract and retained SAVE/RESTORE paths

Do not mistake success on stock headless Sway for successful Fedora/SwayPX
desktop capture or visual acceptance. An installed machine must be tested
separately by its operator.

No local desktop writes, data migration, merge, Quickshell reload,
application launch or compositor movement is part of this proposed PR.

## Next

After exact-head CI and operator review, inspect CUSTOMIZE on the real
desktop, SAVE once, and press VERIFY SAVED GEOMETRY in STORED for the same
checkpoint. Only after this gate should MARK/notes and Brave session
capture advance toward an actual full restore implementation.
