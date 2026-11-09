# MACHINE // Persistent checkpoint names and notes (dormant M3 foundation)

**Patient:** The-Post-Apollo-Project  
**Room:** TimeW MACHINE / checkpoint management  
**Role:** External Hospital-compatible DOC, not live Hospital-registered  
**Previous checkpoint:** PR #1661 merged; STORED read-only v2 verification is present on main  
**State:** GitHub draft, pending exact-head CI and operator approval

## Purpose

Allow personal persistent display names and notes on an existing MACHINE
checkpoint without changing its original captured desktop. The first stage
introduces the storage contract and an explicit isolated Python CLI, *not*
new Quickshell controls. The actual user's Fedora/SwayPX SAVE and STORED
acceptance test is still pending.

## Mechanism

`services/time/MachineCheckpointAnnotations.py` uses the original
owner-restricted `post-apollo/machine/machine.db` and adds one optional
`machine_checkpoint_annotations` table keyed to `checkpoints.id`.
No second SQLite database, `PRAGMA user_version` change, import-time
write or in-place edit of existing rows.

- **display_name:** user-visible name, 1..48 characters, independent of
  the immutable original label in the old checkpoint.
- **note:** optional personal text, up to 1024 Unicode code points / 4096
  UTF-8 bytes; newline allowed. It is not passed to browser processes,
  the compositor or a remote service.
- **revision:** monotone optimistic concurrency number. An update supplies
  the revision last read; stale edits refuse rather than overwriting each
  other. Both complete fields are provided together.
- **updated_at_utc:** absolute UTC timestamp, not a new Clock setting.
  Future display should use the shared Post-Apollo Clock location/time.
- **original_label:** retained from the old read-only checkpoint row,
  available as a display/rollback reference.

Reads use the original read-only `MachineCheckpointStore.connect` and
never create a table or database. A checkpoint without an annotation
returns its original name, empty note and revision zero. An unknown UUID
does not silently create a checkpoint.

An explicit update validates all fields before accessing writable storage,
checks that the original UUID exists, obtains a SQLite write transaction
(`BEGIN IMMEDIATE`), rechecks its revision, and updates **only** its
annotation sidecar. Both the optional table creation and row update
roll back if a simulated interruption occurs.

`MachineCheckpointNotesCLI.py` supports `read <UUID>` and `update`.
The UPDATE request is one bounded JSON line on stdin, never arguments:

```json
{"checkpoint_id":"<canonical checkpoint UUID>","display_name":"Work layout","note":"Notes about this checkpoint","expected_revision":0}
```

The response reports a new revision. The CLI runs under Python `-I`
with its trusted service directory explicitly added to `sys.path`.
It is *not* called by TimeW yet.

## Safety and semantics

- No mutation of `checkpoints.label`, original `document_json`,
  saved/captured timestamps, geometry-v2 JSON, or geometry checksum.
  The v1 STORAGE and exact geometry APIs remain the only capture owners.
- A **display name** does not automatically change the old STORED list,
  which currently uses the legacy label. A follow-up read-only overlay
  adapter and operator-visible editing UI must apply it.
- These notes do not claim to preserve Brave tabs, terminal contents,
  application memory or actual post-reboot session identity.
- A legacy v1-only checkpoint may receive a display name/note but is still
  explicitly **legacy-only** when VERIFIED in STORED. Names/notes do not
  upgrade it into a recoverable geometry checkpoint.
- MARK stays the old session-local timestamp operation. Converting MARK
  into a restorable checkpoint is a separate explicit UI/transaction
  design after the live SAVE acceptance gate.
- No local machine files, current Quickshell, browser or operator's real
  database were accessed or changed by this PR.

## VERIFY

`test_machine_checkpoint_annotations.py` uses a private temporary XDG
directory to exercise old metadata-only and geometry-v2 checkpoints:

- First read returns original name/revision zero without table creation
- New and existing notes round-trip through SQLite
- Explicit UPDATE via the real `python3 -B -I` entrypoint
- Wrong/stale revisions and invalid/private control characters refused
- Injected interrupts before/after INSERT and UPDATE roll back cleanly
- Original v1 rows, original capture labels/times/JSON and v2 geometry
  payload/checksum are byte-for-byte unchanged
- Existing v1 LIST/LOAD and v2 geometry LOAD continue to pass

## NEXT

1. Complete CI, independent review and operator decision on the draft.
2. Verify a real Fedora/SwayPX SAVE in the current installed TimeW and
   inspect the same UUID with STORED's VERIFY SAVED GEOMETRY.
3. Build the read-only STORED annotation overlay and explicit edit controls
   with conflict/rollback behavior.
4. Replace MARK with actual named, restorable checkpoint semantics only
   once the SAVE and verification pipeline is accepted by the operator.
5. Continue Brave session reconciliation and exact geometry RESTORE as
   separate milestones.

No merge, local deployment, or production activation implied.
