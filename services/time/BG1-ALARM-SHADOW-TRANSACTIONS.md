# CLOCK // BG1-B2A Atomic Shadow Transactions

**Status: Synthetic CI only. No live Quickshell / systemd deployment. No audio or notifications.**

## What changes in actual files and processes

The previous BG1-B1 test broker knows the Linux peer process and can reserve a due event,
but it does not control Quickshell's alarm file. A crash between writing an
occurrence receipt and recording its `ringing` state would leave two unrelated
files disagreeing.

BG1-B2A tests a solution **without replacing your live alarm store yet**.
The broker owns a disposable sidecar named
`<explicit Quickshell.dataDir>/alarm-ownership-v1/shadow-alarms-v1.json`.
It contains a **copy** of V2 alarm data together with owner epoch, revision and
occurrence receipts in ONE document. The real `time-alarms-v2.json` remains
unchanged. All shadow changes are locked by `flock`, written to one temporary
file, synced, atomically replaced and directory-synced.

Before each shadow read or mutation, the broker rechecks the SHA-256
of the **real** saved V2 file against the digest captured when the shadow
was initialized. If another writer changes that file, all shadow
operations refuse with `SOURCE_CHANGED_OUTSIDE_SHADOW` rather than using
a stale schedule. The broker also checks source bytes after each transition,
but that is still only a diagnostic fence, not a cross-file transaction.

Only the existing synthetic socket owner may request:
- `shadow_begin`: initialize a copy of an exact verified saved-alarm revision
- `shadow_view`: read revision/owner epoch/counts, not private note content
- `shadow_tick`: validate the exact due time and atomically start a synthetic
  ring with an occurrence receipt
- `shadow_stop`: require the current ringing timestamp, then stop and record
  its receipt
- `shadow_snooze`: same exact occurrence check, then record the five-minute
  snooze state with its receipt
- `shadow_edit`: update a restricted field set, validating values and
  requiring the current expected revision

The broker checks its BG1-A lease before each operation, and every transition
requires its current owner epoch plus the last shadow revision. The stored
receipt is retained after STOP/SNOOZE and after a different owner acquires
a later epoch. A duplicate tick cannot start a second synthetic ring.

## Why it is still not production BG1

These are **shadow transactions**, not real alarms. The synthetic broker
uses a role string supplied by same-UID Python clients and is **not** an
approved native process-identity authority. Quickshell and B0 are unchanged,
are not connected to this broker, and still own their normal files.

A correct implementation of a shadow atomic file does **not** magically
make an unrelated FileView write atomic with it. This prototype deliberately
avoids modifying `time-alarms-v2.json`; the two stores are not synchronized
and there is no production migration or conflict resolution.

A further deployment phase must:
1. Establish trusted role/process identity, source-version installation,
   correct per-shell data directory, and verified owner/worker sessions.
2. Move Quickshell and background operations onto **one canonical writer**,
   with migration and rollback semantics for the saved V2 store.
3. Route actual UI edits, timer checks, STOP/SNOOZE and notification
   actions through that same writer and reject stale owner epochs.
4. Prove sound and notification delivery with auditable acknowledgements.
   Reservation alone is not proof the user heard anything.
5. Verify process crashes, disk failures, timezone and suspend behavior
   on the native target before allowing independent background actuation.

The existing BG1-B1 workflow's changed-file guard was corrected on this
stacked branch: it now forbids edits to live Clock, sound and observer
surfaces instead of assuming that later milestones must contain exactly
B1's original four files. BG1-B2A's own CI still requires the exact
six-file change set and reruns all BG1-A and B1 regression tests.

The current source code exposes no command that plays sound or sends
notifications. All IPC responses retain `actuationEnabled:false`,
`ownsAlarmFile:false` and indicate `shadowOnly:true` for shadow operations.

## Hospital continuity

PATIENT // The-Post-Apollo-Project
ROOM // Clock BG1 ownership and reliable background scheduling
STAFF // Hospital-compatible external DOC, no verified live registration
ASSIGNMENT // BG1-B2A atomic shadow state and occurrence transitions
PREDECESSORS // BG1-A #1890 on main; BG1-B1 #1892 merged to feature branch,
main reconciliation PR #1893
RECOVERY // This branch stacks on #1893 and changes B1 broker source plus
new shadow module, tests, CI and documentation. The current Clock QML,
Notifications, audio, B0 and systemd unit remain untouched.

Operator approval is required for merges and any local-machine writes,
service installation, Quickshell reload, or production activation.
