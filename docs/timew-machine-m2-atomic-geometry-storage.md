# MACHINE // M2 geometry persistence // atomic checkpoint contract

**Patient:** The-Post-Apollo-Project  
**Room:** TimeW / MACHINE desktop recovery  
**Owner:** TimeW MACHINE / DOC succession, GitHub only  
**State:** Dormant storage candidate, not installed or connected to live UI  
**Dependencies:** M2 geometry model PR #1621 and native two-monitor Sway test / floating window correction PR #1625

## Requirement

A normal **SAVE DESKTOP** operation should eventually read the desktop itself,
include the selected monitors, workspaces and windows, then commit a complete
restorable description. It must not require manually clicking CAPTURE PREVIEW.

This milestone establishes the storage portion of that future single action.
It does **not** implement capture or change any user-facing buttons.

The existing `MachineCheckpointStore.py` database and version-1 metadata
reader remain the owners of legacy checkpoints, including the seven operator
checkpoints previously reported. The current writer is not modified.

## Database relationship

The dormant `services/time/MachineGeometryStoreV2.py` uses the existing
private SQLite `machine.db`, `legacy.connect(writable=True)`, WAL and FULL
synchronous settings. Its `save_pair(v1_document, geometry_document)` first
validates an allowlisted strict v1-compatible checkpoint and a complete v2
geometry tree. It rejects any discrepancy in monitor rectangles, workspace
output mapping, or application/workspace/floating counts, including duplicate
Brave windows.

Only after both records validate does the writer:

1. Open the existing owner-only database.
2. Begin one SQLite transaction, adding an **additive** table named
   `machine_checkpoint_geometry_v2` when absent.
3. Insert the v1 compatibility row into the existing `checkpoints` table.
4. Insert the v2 geometry row referencing the exact same UUID, with a SHA-256
   accidental-corruption checksum.
5. Commit both or roll back both. No partially saved checkpoint is advertised.

Legacy `PRAGMA user_version` remains `1`. Other existing checkpoint rows
and their exact serialized JSON remain unchanged. The new data uses no
separate competing database or file writer. It does not migrate or fill in
missing geometry for historical v1 rows.

The checksum is a **corruption detector**, not an authenticity signature.

## Read-only behavior

`load_geometry(checkpoint_id)` uses an existing **read-only** connection. A
legacy checkpoint without a geometry row returns `legacy_only` with
`geometry_available=false`. It never creates a sidecar, table or migration.

An actual geometry record is strictly revalidated against its legacy row
before it can be returned. The result does not assert a stable Brave/Kitty
identity or exact recoverable browser session.

## Safety and limitations

- `MachineGeometryStoreV2` is dormant. No CLI, Quickshell import, background
  timer, Sway IPC, browser session read, terminal inspect, process launch,
  compositor move or local user data access is included.
- Geometry accepts only output geometry and scale, workspaces, nested
  container hierarchy, split proportions, and keyed window rectangles.
  Titles, URLs, PIDs, terminal commands, arbitrary source fields, cookies,
  passwords and full raw Sway JSON are rejected. Stored UUIDs are local
  per-checkpoint keys, not trusted identities across browser restarts.
- This milestone stores **geometry only**, not Brave tabs, page contents,
  terminal sessions, unsaved documents, application RAM or filesystem
  snapshots. The existing v2 application identity model remains schema-only.
- A caller must supply the v1 and v2 projections from the SAME compositor
  capture. Exact atomic Sway observation is a later integration task;
  this writer verifies structural consistency, not capture timing provenance.
- Transaction rollback tests simulate interruptions in disposable storage,
  not real SIGKILL power failure. SQLite durability still needs an isolated
  process-crash and power-loss acceptance gate before live activation.
- Long-term names, notes, timeline branching and combined checkpoints are
  separate additive schema/UI work. They remain requirements, not silently
  discarded features.

## Verify

Dedicated GitHub CI:

```bash
python3 -B -I tests/timew/test_machine_geometry_store_v2_contract.py
python3 -B -I tests/timew/test_machine_geometry_store_v2.py
python3 -B -I tests/timew/test_machine_checkpoint_store.py
python3 -B -I tests/timew/test_machine_geometry_v2.py
python3 -B -I tests/timew/test_machine_session_identity_v2.py
```

Tests use a private `TemporaryDirectory` and synthetic two-monitor geometry,
including two separate Brave windows and a floating Kitty window. They assert:

- no file creation on invalid input;
- original v1 records remain byte-for-byte identical;
- v1 listing/loading still works after v2 insertion;
- complete geometry round-trips through the additive table;
- injected errors after each of the two INSERT statements leave no
  half-completed checkpoint;
- corrupted geometry payloads are refused;
- private folder/database modes remain owner-only.

## NEXT

1. Independent review and exact-head CI of this draft.
2. Construct a bounded, same-frame v1/v2 capture coordinator, originally
   tested against synthetic and isolated headless Sway.
3. Extend future combined transaction with verified, permissioned app
   session records and checkpoint names/notes.
4. Only after those foundations are stable, implement the one-click
   `SAVE DESKTOP` UI with optional custom monitor/workspace/window selection.
5. Test the live Fedora/SwayPX UI under separately approved local-write and
   compositor permissions, followed by user final acceptance.

**No merge or local activation is implied by this design.**
