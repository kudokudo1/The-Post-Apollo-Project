# MACHINE // Verified SAVE receipt

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** TimeW MACHINE / desktop checkpoints  
**STAFF ROLE:** DOC external, Hospital-compatible; not live Hospital registration  
**STATE:** Draft, pending GitHub CI/independent review; no local activation  
**Predecessor:** PR #1654, isolated Python launcher repair, merged into main

## Problem

The SAVE UI previously displayed `SAVED // DESKTOP GEOMETRY STORED` as
soon as the atomic geometry writer returned its summary. The writer did
confirm the compatibility row existed after commit, but the user could not
distinguish a durable **v2 geometry** record that successfully reloaded
from a partial/failed read-back. If an output response was lost, blindly
retrying SAVE could create another checkpoint.

The actual desktop SAVE and CUSTOMIZE still need operator runtime tests.
A headless stock Sway CI pass is not the operator's Fedora/SwayPX acceptance.

## Implementation

`MachineSaveBridgeV2.save_request` now performs an explicit *read-only*
verification after the existing atomic save completes:

1. Reopen the exact UUID with `MachineGeometryStoreV2.load_geometry`,
   which validates stored SHA-256, strict geometry, and its matching v1 row.
2. Independently reopen the same UUID through
   `MachineCheckpointStore.load`, without altering existing rows.
3. Compare the checkpoint UUID, stored v1 summary, and all three v2
   geometry counts against the just-committed save result.
4. Only if **both** reads and counts match return `status=saved` with
   `verification.status=readback_verified` and exact counts.
5. If a *post-commit* read or consistency check fails, return
   `status=saved_unverified`, preserving the checkpoint UUID. It is
   explicitly **not** a clean pre-save rejection. The UI must not
   encourage immediately saving again, because that could duplicate a
   committed checkpoint.

No additional database writer, table, schema migration, app session
capture, GUI worker, or background operation was added.

The actual TimeW widget shows:

- **SAVED + VERIFIED // N MON // N WS // N WINDOWS** on confirmed read-back;
- **SAVE MAY BE STORED // OPEN STORED TO CHECK** for a committed record
  whose v2 read-back was not verified;
- **SAVE OUTCOME UNKNOWN // CHECK STORED BEFORE RETRY** if the save
  process exits without a usable response.

These states do not imply Brave tabs, unsaved application buffers,
restorable window identity or exact window placement on RESTORE.
The existing RESTORE implementation remains unchanged.

## Verification

- Synthetic two-monitor test saves both one-window custom scope and whole
  desktop, then checks independent v1/v2 read-back receipts.
- Tests inject a failing read-only geometry lookup and an inconsistent
  window count **after** a real temporary SQLite commit. Both must return
  `saved_unverified`; the checkpoint must remain persisted and
  loadable, with no destructive cleanup or retry.
- Actual standalone `python3 -B -I` CLI under private headless stock Sway
  must return `readback_verified` with two monitors, two workspaces and
  three windows.
- Source contract checks the actual TimeW UI requires a verified
  receipt before showing successful save and handles unknown outcomes
  separately.
- Existing selection, legacy v1 and atomic storage checks remain.

## WATCH OUT FOR

The receipt establishes *stored record consistency* at read-back time.
It is not evidence that a future desktop restore will achieve pixel
fidelity, recover Brave tabs, or preserve app RAM.

A SHA-256 checksum inside the same local database is a corruption
check, not a cryptographic authenticity seal. No permission or
authorization claim is derived from the checksum.

**No live desktop writes, Git worktree changes, merges, or Quickshell
reloads are part of this PR.**

## NEXT

1. CI and independent review of the exact draft head.
2. Operator's separately authorized local sync, if needed.
3. Click `CUSTOMIZE` to test live read-only capture; click SAVE once,
   observe `SAVED + VERIFIED`, then open STORED and inspect the same row.
4. Only after this real SAVE gate, build checkpoint metadata/notes and
   restorable named MARK, then Brave sessions and geometry RESTORE.
