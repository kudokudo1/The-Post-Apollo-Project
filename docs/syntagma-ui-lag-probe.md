# Syntagma // opt-in UI-event-loop lag measurement

**Owner:** Nurse 3c. **Status:** diagnostic instrumentation only, not
an optimization or fix. **Introduced:** October 13, 2026.
**Scope:** `shell.qml` only (dock Git/Hospital controls and a shell timer).

## Why this exists

The operator saw the entire Quickshell desktop stall, including its MPD/CAVA
visualizer, when opening/interacting with large menus. A `top -H` capture
showed Quickshell's **main/UI thread** spending ~4 consecutive seconds at
~99% of one logical CPU, with the render thread not leading the sampled
CPU usage. `qmlprofiler`, `qtcreator`, and `perf` are **not found on the
operator's current PATH**. This lightweight timing experiment does not
require installing those tools.

## What it actually measures

Set `POST_APOLLO_UI_LAG_PROBE=1` at **Quickshell process launch**.
The default (unset or any other value) runs no diagnostic timer and
produces no timing logs.

1. A 100 ms QML Timer records elapsed wall clock between its own
   callbacks and warns only if the interval reaches 350 ms (250+ ms
   later than requested).
2. The **dock-button** Git and Hospital toggle handlers report elapsed
   synchronous wall time across the **unchanged** calls to
   `gitWindow.toggle()` or `hospitalWindow.toggle()`.
3. Log lines begin with `SYNTAGMA_LAG_PROBE`; long gaps include whether
   Git, Hospital, and Notifications were open **when the delayed timer
   callback finally ran**.

**Limitations:** Timer scheduling can slip for reasons besides a
CPU-heavy QML handler (normal scheduling, compositor stalls, suspended
process, etc.). This does not capture a JavaScript stack, name an expensive
binding, or prove that a lag spike occurred precisely at an open command.
Dock-toggle duration includes synchronous change-signal side effects
but **not** deferred `Qt.callLater` work, asynchronous service results,
or all keyboard/IPC opening paths. This is a useful correlation instrument,
not a replacement for a QML profiler.

## Safe local trial

First verify the **actual Quickshell checkout**, normally the symlink
target of `~/.config/quickshell`, has the merged probe:

```bash
qsdir="$(readlink -f "${XDG_CONFIG_HOME:-$HOME/.config}/quickshell")"
grep -n 'POST_APOLLO_UI_LAG_PROBE' "$qsdir/shell.qml"
git -C "$qsdir" status --short
git -C "$qsdir" log -1 --oneline
```

Do **not** overwrite dirty work or automatically `reset --hard`. If that
`grep` finds nothing, reconcile/pull the safe changes before proceeding.

Save unfinished widget edits. Restart the real Quickshell configuration,
**not** the unrelated `post-apollo-dev-runtime` repository, and set the
flag on the new process:

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Then open **Git just once**, wait for recovery, and optionally try
**Hospital once** separately; do not spam-click or revive the known
crashing unmap/remap tests. Your visualizer remains the visual symptom
to compare with the logged delay.

Retrieve logs (depending on local Quickshell executable):

```bash
qs log --tail 250 | grep SYNTAGMA_LAG_PROBE
# or: quickshell log --tail 250 | grep SYNTAGMA_LAG_PROBE
```

If the `--tail` option is not supported in this build, use
`qs log --help` and `qs log` to identify the available log command
or check the path printed by Quickshell when it launched.

Sample messages (illustrative, NOT observed):

```text
SYNTAGMA_LAG_PROBE // git dock toggle synchronous=24ms // nowOpen=true
SYNTAGMA_LAG_PROBE // event-loop interval 4120ms (target 100ms) // git=true hospital=false notifications=false
```

The **presence** of a long gap would support a main-loop responsiveness
problem; the accompanying sync-toggle measurement helps distinguish the
immediate open handler from work occurring afterwards. **Absence** of
gaps during an unrelated interval is inconclusive.

### Restore default behavior

```bash
env -u POST_APOLLO_UI_LAG_PROBE \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

No extra packages, system configuration changes or device restarts needed
beyond the deliberate Quickshell process restart. Both normal dock
toggle paths, the persistent Git/Hospital window surfaces, the keyboard
ownership contract, CAVA, and service refreshes are unchanged.

## Accept/reject and next step

A successful diagnostic has paired observations: a single normal
opening, actual visual stall, log timestamps/intervals, and synchronous
toggle duration. If the toggle duration is already multi-second,
instrument smaller synchronous handlers in a separately reviewed PR.
If the toggle returns quickly but the loop gap is long, focus on
deferred callbacks, model signals, JS bindings, and service result
processing. Do not infer the precise function from the gap alone.

Existing evidence ledger:
`EVIDENCE/syntagma-main-thread-freeze-evidence-20261013.md`.
