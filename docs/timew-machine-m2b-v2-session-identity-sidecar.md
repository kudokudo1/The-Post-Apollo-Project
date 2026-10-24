# MACHINE M2b // Versioned session identity sidecar proposal

**State:** Bounded schema/parser + synthetic CI only. NOT an approved on-disk
format, live capture implementation, browser extension, Kitty controller,
trusted identity assertion, v1 migration, or executable recovery operation.

## Why

M2a proves the *number and placement* of windows can be compared even when
there are 17 Brave and four Kitty instances. But v1 saves just `app_id`,
`workspace` and `floating` per window. Nothing in that data distinguishes
Brave browser windows, browser profiles or individual tabs, or the internal
Kitty layouts and working directories.

M2b sketches an *additional* explicit window/session identity record that a
future consented adapter could populate. It does not alter the operator's
seven existing checkpoints.

## Separation of concerns

**v1 stays authoritative** for the existing `machine.db` checkpoint schema.
This PR does NOT change `MachineCheckpointStore.py`, add write APIs, migrate
rows or update TimeW.qml. Existing v1 records remain loadable.

The proposed v2 identity sidecar has:

- `schema_version: 2` and `kind: machine-session-identity-sidecar`;
- `checkpoint_id`: canonical UUID linking to an existing saved record;
- `windows[]` with a distinct **checkpoint-local** `window_key`, app ID,
  workspace, floating flag, `identity`, `capabilities`, and `items`.
- `identity`: adapter (`none`, `brave`, `kitty`), claimed state
  (`not_requested`, `denied`, `unsupported`, `partial`, `reported`),
  optional **opaque UUID** namespace/profile and instance references. This
  is a *proposal for adapter-reported identifiers*, not a proof that those
  UUIDs are stable or currently exist.
- `capabilities`: independently status-report window identification,
  inner-item enumeration and reopening support. A capability marked
  `reported` means a future adapter claimed it, **not** a permission or
  proof to launch anything.
- `items[]`: checkpoint-local opaque item key, type (browser tab,
  Kitty tab or Kitty split), position and optional opaque adapter item
  reference. **No actual URL, page title, path, command or content** is
  represented by this first milestone.

No saved compositor `con_id`, PID, window title, browser URL, terminal
buffer, shell command, profile path, password, cookies, auth token or
clipboard text is permitted. This protects synthetic future test records
from acquiring private user data during schema experimentation.

`validate_sidecar(proposal, v1_checkpoint=...)` accepts a supplied,
already-loaded v1 document and verifies the **exact multiset** of app IDs,
workspaces and floating state before declaring the *proposal shape*
compatible. It never queries disk. Distinct opaque IDs are checked for
uniqueness, including duplicates within one profile/adapter namespace.
Bounded arrays and strict allowlists fail closed on unknown data. It does
not assert that the correct *individual* window was matched.

`describe_coverage(proposal)` returns counts and explicit
`exact_session_match=false`, `per_window_identity_verified=false` and
`safe_actions=[]`. Even 21 distinct valid UUIDs are not evidence of
real-world identity. Such claims require separate adapter attestations,
revalidation and app-specific consent gates.

## Planned storage, not implemented

A future separate, owner-only v2 sidecar catalog **may** live alongside
`machine.db` in `$XDG_DATA_HOME/post-apollo/machine/`, indexed by the
original checkpoint UUID. Do not create it until M2d authorization.
Potential migration is **additive only**:

1. Read existing v1 checkpoint, never rewrite or discard it.
2. Request separate consent for Brave or Kitty session inspection and
   retention of needed metadata.
3. Construct a versioned sidecar in isolation and validate against the
   exact v1 window multiset, including repeated app IDs.
4. Commit the sidecar transactionally only after user consent, with
   owner-only permissions and rollback. On errors, discard the new sidecar,
   leave v1 untouched, and report `session_identity_unavailable`.
5. If the sidecar is absent, unsupported, revoked or corrupt, **fall back
   to v1 layout-only comparison** with `session_identity_verified=false`.
6. Never silently backfill seven existing saves with guessed browser tabs,
   launch commands or Kitty processes. v2 does not turn old screenshots/
   metadata into recoverable app memory.

Storage format, encryption, opt-in scope, provider trust, TTL and browser
private-mode policy remain *decisions pending operator review*. The code
does not read, persist or launch anything.

## Two separate consumers, later

- **REVIVE** will favor continuity of the presently running session and
  minimally repair confirmed differences, without replacing current work.
- **RESTORE** will reconstruct toward a selected saved checkpoint *after*
  protecting the current live timeline and reviewing conflicts.

Both may consume **independently verified** app identity information.
Neither may treat a parser-accepted reported UUID as authorization, trust
the age of a Sway container ID, assume tab URLs are harmless, rerun terminal
programs, or claim exact equality without confirming inside-app state.

## Next gate M2c

Audit actual Brave and Kitty adapter capabilities and ownership with the
relevant workers. Verify supported versioned APIs, session/window/tab
correlation, persistence across process restart, incognito safety,
profile permission boundaries and encrypted/private state exclusions.
Use fictional test fixtures first; no new browser debugging port,
native host, local package install, app launch or background collector
without separate approval. Existing notification/Brave components must be
inspected to avoid duplicate integrations.

The operator also wants friendly names for saved checkpoints later.
That's a separate metadata/UI task, not an excuse to migrate v1 now.

## Verified by

`tests/timew/test_machine_session_identity_v2.py` and
`tests/timew/test_machine_session_identity_v2_contract.py`, along with
all existing TimeW foundation tests. All tests use fabricated UUIDs and
invented app/window layouts, never the operator's private sessions.
