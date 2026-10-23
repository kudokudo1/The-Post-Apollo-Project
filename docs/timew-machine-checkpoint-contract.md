# TimeW // MACHINE: desktop checkpoint and restoration contract (proposal)

**State:** DRAFT for operator review. **Not approved**, implemented, live, or merged.
**Scope:** TimeW's future **local Sway/SwayFX desktop layout** checkpoints only.
**Owner:** The-Post-Apollo-Project / TimeW. No Hospital ownership is assumed.
**Evidence baseline:** TimeW MACHINE currently provides process-local named UTC time
markers and window-instance age. It neither captures nor restores desktop state.
**Explicitly out of scope today:** backend, UI capture button, disk writing,
screenshot capture, layout mutation, window launches, service restart, and merging.

## 1 // Identity: three different checkpoint meanings

- **MACHINE timestamp marker:** An in-memory TimeW record of a name, UTC time,
  and TimeW-instance age. Existing implementation; lost on Quickshell restart.
- **MACHINE desktop checkpoint (proposed):** A user-requested, *metadata-only*
  description of the current Sway layout and its partial-restoration candidates.
  It is not a saved app session or a screenshot.
- **Hospital Room checkpoint:** A separate continuity/assignment record owned by
  Hospital. It is not an operating-system snapshot and must not be read as one.
  Git's repository snapshot/operation journal is also a separate domain.

Labels and IDs must reflect these distinctions. Do not advertise a timestamp
marker as recoverable desktop state.

## 2 // Consent and authority

This proposal grants **no ongoing permission** to inspect a desktop, save data,
move windows, or restore layouts.

A future implementation requires a separately approved assignment and a
concrete, reviewed UI/action flow for:

1. **CAPTURE PREVIEW**: On an explicit operator click, query current local
   Sway state (read-only) and show the metadata fields that would be retained.
   No screenshot, file write, or remote call.
2. **SAVE CHECKPOINT**: A second explicit operator action, after choosing scope
   and redactions, persists a metadata record in the user's local profile.
   File location, retention and permissions require an approved decision.
3. **RESTORE PREVIEW**: Select a saved checkpoint and review a current-vs-target
   diff, missing outputs/windows, ambiguous matches, and proposed operations.
   This step does not move, launch, focus, kill, resize or close anything.
4. **APPLY SELECTED ACTIONS**: Only after the operator approves *this specific*
   plan; no blanket authorization or automatic replay. Apply a bounded sequence
   with reports. Never silently expand into application startup or shutdown.

Closing TimeW, opening MACHINE, switching tabs, booting, or starting Quickshell
must not trigger capture, save, or restoration.

## 3 // Read scope and privacy boundary

**Candidate local read-only sources** (need live capability verification):
- Sway IPC read paths such as output/workspace/tree metadata; prefer existing
  Quickshell/Sway integration when sufficient.
- Quickshell in-memory TimeW timestamp marker metadata *only if the user elects
  to associate it with the new checkpoint*. No automatic conversion.

**Potential allowlisted fields** for a metadata-only record:
- Format/schema version, capture UTC time, compositor family/version evidence,
  local capture session token (not username, hostname, IP or auth material).
- Output connector identity, resolution, position and scale *needed to remap*.
- Workspace identifiers/names and output assignments, with an explicit option
  to omit user-named workspaces.
- For each selected window: ephemeral checkpoint-local record ID, app_id or
  XWayland class/instance (if available), workspace association,
  tiling/floating designation, and optional non-sensitive geometry/size.
- Optional source/target focus **only as a previewed suggestion**, never an
  implicit promise to acquire or hold keyboard ownership.

**Excluded by default, even if Sway could expose them**:
- Screenshot pixels, thumbnails, video/audio, clipboard and clipboard history.
- Application window titles, document names/paths, URLs, command lines,
  environment variables, authentication tokens, PID identities and window text.
- Browser page content, private-message contents, terminal buffers, keystrokes,
  passwords, and application data/state.
- Hospital assignments, Git diffs/contents, network identity and device secrets.

Workspace names, app IDs and monitor configuration can still reveal habits.
Preview them before saving; allow the operator to exclude individual windows,
workspaces and outputs. Do not send checkpoint metadata to a server or include
private fields in telemetry/error logs. A public Git repository never receives
captured data.

## 4 // Proposed versioned record

A future implementation should store *only* explicitly allowed information.
Illustrative **schema concept**, not an implemented JSON API:

- \`schema_version\`: integer, initially \`1\`.
- \`kind\`: \`sway-layout-metadata\`.
- \`capture_id\`: locally generated non-secret, opaque unique identifier.
- \`captured_at_utc\`: UTC timestamp.
- \`scope\`: operator-approved outputs/workspaces/windows.
- \`outputs[]\`: connector identity plus rect/scale necessary for remap.
- \`workspaces[]\`: name/number and output association, if allowed.
- \`windows[]\`: checkpoint-local key, narrow app matcher, intended workspace,
  tiling/floating type, optional geometry. NO title/document/path/content.
- \`excluded_counts\`: count of excluded records, not their names.
- \`capability_limits[]\`: what cannot be safely captured/restored on this host.

Validate strict types, lengths, size bounds, schema version and record count
before accepting saved input. Treat saved metadata as untrusted if manually
edited. Reject unknown versions and refuse partial parsing that silently
enables broader operations.

**Pending operator decisions:** storage path (candidate:
\`$XDG_STATE_HOME/post-apollo/timew/checkpoints/\`), file permissions
(candidate owner-only directories and mode 0600), at-rest encryption policy,
retention/maximum records, backup/export rules, and default exclusion scope.
None is established by this draft.

## 5 // Conservative restore matching

The live Sway tree changes: transient window/container IDs are **not stable
identities across sessions**. Matching must be explicit and fail closed.

- First map requested outputs against currently connected outputs. A missing
  monitor is a **blocked operation**, not an excuse to move all workspaces to a
  default monitor without consent.
- Match only currently existing windows using approved app/class fields and
  workspace/geometry hints. A zero-match or multi-match is **SKIP / REVIEW**.
- Never match on title, URL, secret command-line, or screenshot content.
- Never assume that an app can reload an old file, browser tab, terminal state
  or in-memory process state simply because its window can be repositioned.
- Present every proposed movement and floating geometry change as a diff.
  Tiling order and fullscreen behavior may have compositor-specific limits;
  mark them *unsupported or best-effort* until independently verified.
- A window disappearing or changing between preview and apply invalidates the
  relevant plan item. The plan must revalidate current compositor state.

## 6 // Allowed *candidate* restoration actions

After operator approval and runtime validation, a first restore executor may
**only** attempt selected, non-destructive layout changes for existing windows:

- Move an unambiguously matched window to an existing, explicitly chosen
  workspace or connected output.
- Apply floating position/size **when supported**, with bounds clamped to a
  confirmed connected output and user-visible adjustment previews.

**Forbidden within the first restore scope:** \`kill\`, close, process
termination, app launch, workspace deletion, compositor reload, system sleep,
screen capture, clipboard writes, arbitrary shell, input emulation, network
actions, config overwrite, or permanent focus/keyboard lock.

Reassigning a window or changing its geometry is still a **local mutation**:
the operator must approve the selected plan *at execution time*. No background
apply, auto-restore on login, or permissive wildcards.

## 7 // Preview, apply, failure, rollback

The UI needs explicit, distinguishable states:
\`CAPTURE_PREVIEW\`, \`SAVE_REVIEW\`, \`SAVED\`, \`RESTORE_PREVIEW\`,
\`BLOCKED\`, \`READY_FOR_APPROVAL\`, \`APPLYING\`, \`PARTIAL\`,
\`FAILED\`, \`APPLIED\`. Status names here are proposal, not code.

Every restore preview must show:
- requested and current outputs/workspaces, windows targeted, actions and
  exclusions, unsupported changes, and estimated reversibility;
- any ambiguous/missing match and what will be skipped;
- the explicit selected subset, before-apply validation and cancel action.

Before execution, generate a **temporary before-state** (with separate operator
authorization, bounded to the selected windows) to support potential Undo.
This is not guaranteed transactional rollback: other apps/Sway can race, or a
window can close. Stop on destructive surprise; preserve per-item success,
failure and uncertainty; never report FULLY RESTORED after partial failure.
Undo, when implemented, is likewise previewed and explicitly authorized,
may be best-effort, and must not touch unrelated windows.

Keep the existing Window Keyboard Focus Contract:
keyboard ownership remains transferable, ordinary applications regain focus,
and MACHINE may not retain indefinite exclusive focus. Do not change TimeW's
always-mapped panel/input-mask opening behavior as part of this feature.

## 8 // Acceptance gates before any implementation

- Operator approves capture fields, opt-in/redactions and storage/retention.
- Real Sway/SwayFX source confirms supported read metadata and safe mutation
  commands, including revalidation under changing window identities.
- Isolated tests: missing/disconnected outputs, identical app IDs, windows
  disappearing, invalid records/paths, geometry outside outputs, tiling vs.
  floating, focus handoff, races and partial apply/Undo.
- Source/CI contracts: no capture on menu-open, no background writes, no shell
  interpolation, no screenshot by default, no application termination/launch.
- UI dry-run tests on disposable Sway sessions before *any* live mutation.
- Explicit operator authorization before changing local files, restarting
  services or applying even one Sway placement operation.
- Preserve all existing TimeW CLOCK/CALC/TOOLS and MACHINE marker behavior.

## 9 // Open decisions for operator review

1. Does the first real checkpoint save **layout metadata only**, or should
   screenshots be designed as an explicitly separate, opt-in artifact later?
2. Which outputs/workspaces/windows should be included or excluded by default?
3. Should a checkpoint persist across reboot? If yes, what path, encryption,
   retention and export policy is acceptable?
4. Should a first restore release support only **preview** and manual
   per-window action, or offer a selected batch after a full dry run?
5. What is the desired relationship to the existing in-memory MACHINE markers?
   Candidate: link by optional opaque marker ID, without promoting markers to
   restoration checkpoints or coupling to Hospital.

**Current decision:** definition only. No capture, persistence, Sway control,
or restore permissions granted by creating or reviewing this document.
