# MACHINE // M2 geometry capture contract

**Owner:** TimeW / MACHINE desktop recovery, The-Post-Apollo-Project  
**Status:** Proposed implementation contract + synthetic, read-only prototype. Not activated.  
**Operator direction:** 2026-11-09 clarification in the Time Machine recovery conversation.  
**Relationship:** Extends the existing v1 layout store and the `MachineSessionIdentityV2` proposal. Does not replace either.  
**Scope:** Desktop geometry capture foundation. Browser and Kitty session capture, local activation, restoration and UI redesign are separate phases.

## Why this is necessary

MACHINE must be capable of restoring the user's **exact desktop**, not merely
reopening a set of application names. Exact position, width, height, monitor
assignment, workspace, tiled/floating state, Sway tree structure and split
proportions are core checkpoint information. The existing v1 `machine.db`
does not contain individual window geometry or nested tiling.

The operator's desired daily operation is a single `SAVE DESKTOP` action that
reads, validates **and persists** a checkpoint. `CAPTURE PREVIEW` remains an
optional inspection path, not a required pre-save action. Monitor/workspace/window
selection remains available when customizing a save, with all applicable items
included by default. The separate temporary-memory MARK breadcrumb is **not** a
restorable checkpoint; the desired future interaction is a named checkpoint
or a note on a restorable checkpoint. Historical checkpoints and timelines
should eventually support creating a combined saved state.

Internally, use an unambiguous instant (UTC storage is fine); externally,
display the user's actual local time through the existing shared Clock/Time
service. Do not create a separate MACHINE time-zone setting.

## Source audit (current main, November 9, 2026)

| Component | Present behavior | Missing requirement |
| --- | --- | --- |
| `MachineSwayRead.py` | Captures active outputs (connector + rect), workspace-output mapping, and windows (app ID, workspace, floating) | Per-window rect, nested layout tree, output scale/transform, capture-linked window keys |
| `MachineCheckpointModel.py` | Allowlisted v1 metadata-only projection | Full restore geometry and related session metadata |
| `MachineCheckpointStore.py` | Version-1 SQLite `save/list/load` and UUID records | Additive v2 storage, names/notes updates, atomic capture transaction |
| `MachineWindowMultiplicity.py` | Counts 17 Brave / 4 Kitty arrangements without claiming identity | Per-window matching |
| `MachineSessionIdentityV2.py` | Validates synthetic opaque per-window keys and inner-item identity claims | Real native identity/contents and authorized capture |
| `MachineKittyRead.py` | Dormant read-only ephemeral window/tab/pane ID inventory | Persistent session reconstruction |
| `MachineRestoreCheckpoint.py` | Explicit one-click, existing unique-window mover and bounded app launch attempt | Full geometry placement, duplicate windows, app sessions and nested layouts |
| `widgets/TimeW.qml` | Existing CAPTURE PREVIEW / SAVE CHECKPOINT / MARK interfaces | Automatic capture-and-save and simpler differentiated UI |

Existing local v1 checkpoint data MUST NOT be migrated, rewritten or deleted
during v2 development. No actual v1 row magically gains tab history or window
geometry because a new parser exists.

## Stage 1 // Pure geometry projection (this PR)

`MachineGeometryV2.project_geometry(outputs, workspaces, tree, window_keys)`
accepts already-acquired Sway-shaped objects supplied by a future capture
coordinator. It emits an allowlisted, bounded **proposal**, containing:

- active output connector, rect, scale and transform;
- each workspace's identity, output, rect, layout and ordered nested tree;
- each window's checkpoint-local UUID, app ID, workspace, output, floating
  and fullscreen flags, absolute `rect`, optional client `window_rect`,
  `deco_rect` and `geometry`;
- ordered tiled and floating branches, container layouts and split fractions.

No compositor `con_id`, PID, title, URL, shell command, clipboard, browser
content, credentials or raw Sway tree is retained. Numeric `con_id` is a
**transient in-memory lookup input only**, needed to associate an externally
allocated checkpoint-local UUID with a particular window. Those UUIDs are not
proof of the same window after reboot.

The future coordinator MUST create the same checkpoint-local window keys
for both this geometry snapshot and the existing M2b session-identity sidecar
during one consistent capture. Never generate independent keys then attempt
to join two snapshots by app ID or window order.

`compare_to_v1` checks the existing v1 app/workspace/floating multiset but
cannot declare an exact session identity match or authorize a restore.

This prototype has **no CLI, disk access, Sway IPC or QML registration**. It
does not activate any capture, save, launch or move operation.

## Stage 2 // Required before an actual v2 checkpoint

1. Establish a single, consistent Sway capture read, including monitor, workspace
   and window geometry. Verify actual SwayPX output fields and precision.
2. Generate checkpoint-local UUIDs for the same frame, and correlate to
   app-reported identity only where independently verified.
3. Design additive v2 storage with atomic full-snapshot custody, private data
   scope, encryption decision, fault injection and v1 compatibility. Avoid
   inventing an unrelated competing database writer.
4. Add customized selection (monitors/workspaces/windows), correct parent-child
   dependencies and notes/name while making ordinary SAVE automatically
   capture and persist.
5. Verify round-trip of geometry, split ratios and output associations from
   a disposable SwayPX session before exposing an exact-restore claim.
6. Add verified Brave session adapters (individual windows, tabs, page URLs,
   pinned/active/group state where available) and Kitty/Zellij session adapters
   under separate consent and ownership. No automatic terminal command replay.
7. Restore the compositor hierarchy and window geometry only after a safe
   session-identity mapping and conflict-resolution plan; never infer an
   exact match from app IDs alone.

## Recovery and limits

- No local machine changes, Quickshell reload, installed-app inspection, user
  browser tab access or real compositor actions are part of this PR.
- This prototype records numeric logical pixel rectangles. Restoring exact
  *rendered* pixels across output scale, decorations and compositor differences
  still requires measured SwayPX round-trip verification.
- The present v1 store is not a full desktop session. A full reboot recovery
  acceptance test must cover Brave's own recovery state, multiple Brave
  instances, Kitty/Zellij, two monitors, nested tiled layouts and extra live
  windows without destroying unsaved work.
- Native tests and operator visual review, not green source tests alone, are
  required for acceptance.

## Verification

Dedicated synthetic contract:
`python3 -B -I tests/timew/test_machine_geometry_v2.py`

It validates two fictitious monitors, duplicate Brave windows in a split
layout, floating Kitty geometry, separate checkpoint-local keys, output
redaction, and fail-closed malformed tree/key cases. The dedicated CI also
runs existing v1 checkpoint storage and v2 identity/multiplicity tests.

**No runtime acceptance is claimed.**
