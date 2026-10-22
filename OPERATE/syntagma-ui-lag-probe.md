# Syntagma // opt-in UI-event-loop lag measurement

**Owner:** Nurse 3c. **Status:** diagnostic instrumentation only, not
an optimization or fix. **Introduced:** October 13, 2026.
**Original scope:** `shell.qml` (dock Git/Hospital controls and a shell timer).
**October 22 follow-up:** optional background timing in Media dock, Network dock,
and Notifications Hub (no production behavior changes).

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

## October 22 follow-up // background callback timing (draft diagnostic)

The existing `POST_APOLLO_UI_LAG_PROBE=1` launch flag now also enables
`SYNTAGMA_BG_PROBE` lines. No second environment variable, new timer,
process, background data collector, or change to control/visual policy.

- **Music / CAVA:** warn if a single synchronous CAVA parse/model-update
  callback takes **25 ms or more**. A `media cava-frames 5s` line reports
  received and changed frames and maximum callback duration once per
  five seconds of incoming frames. This does not measure asynchronous
  rendering, blur effects, or MPD decoding.
- **Network:** report a `network poll-gap` when the existing **500 ms**
  timer is delayed to at least **850 ms** (correlation only, **not**
  proof that Network caused the delay). Dispatch and each existing
  stdout callback log only when their synchronous work reaches **25 ms**.
  The ethernet-device callback includes the existing link/internet
  notification producers; original commands/interval remain unchanged.
- **Notifications:** time the existing filtered-history model rebuild.
  Log if it takes at least **25 ms**, or once per five seconds of
  rebuild activity, with scanned/retained counts and menu-open state.
  This does not time asynchronous disk persistence or deferred Qt painting.

Logs contain numeric timestamps, durations, aggregate counts and menu
state only. They do **not** expose notification text, site URLs, finance
records, song titles, or subprocess output. On a normal launch without
the flag, no additional timer or logging is active; the fast-path has
only dormant condition guards.

Retrieve both streams together using a terminal with wide output:

```bash
qs log --tail 3000 | rg 'SYNTAGMA_(LAG|BG)_PROBE'
```

The merged source must exist in the actual Quickshell checkout, and the
process must be deliberately restarted with the flag to run the
instrumentation. A GitHub branch is not live-shell runtime.

**Interpretation:** a slow callback temporally aligned with an event-loop
gap is a candidate bottleneck. A 10–20 second event-loop delay without
one of these callbacks logging as slow does not clear any widget or prove
a driver issue; unmeasured callbacks and deferred scene-graph work remain.
Timer gaps from multiple components may all describe the **same** stall.
Do not optimize, disable features, or declare a cause from one log.

**Rollback:** relaunch without `POST_APOLLO_UI_LAG_PROBE=1` using the
existing restart procedure above. Reverting the diagnostic PR also
removes the source instrumentation without data migrations.
