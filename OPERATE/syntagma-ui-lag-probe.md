# Syntagma // opt-in UI-event-loop lag measurement

> **Current Media default (October 24):** CAVA latest-frame coalescing is now
> the intended ordinary-launch behavior. The CAVA *diagnostic measurements*
> remain opt-in. See the final section below for normal startup and rollback.
> Earlier A/B launch commands in this document are preserved as experiment
> history, not the current default policy.

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

## October 22 controlled isolation // Network dock subprocess polling

**State: diagnostic experiment only; live operator trial not yet verified.**

Use `POST_APOLLO_NETWORK_POLL_PAUSED=1` in the **Quickshell launch
environment** to skip both the Network dock's initial subprocess probes
and its existing 500 ms polling timer. It is disabled by default. This is
not a network-disconnect or performance fix.

- Suppressed by this flag: only `modules/Network.qml`'s recurring/startup
  `nmcli`, `iw`, and `ethtool` subprocess probes, including its device
  result-triggered link/Internet notification producer updates.
- Preserved: NetworkManager and actual Wi-Fi/Ethernet connections; the
  passive `Quickshell.Networking` device observer; other widgets, services,
  visual effects, and normal lag diagnostics.
- Tradeoff: the dock's polled signal, bitrate, and Ethernet readings can
  be absent or stale; Network-owned notifications may not be generated
  while testing. The flag does not isolate other independent network clients.
- One startup confirmation warning begins
  `SYNTAGMA_BG_PROBE // network widget polling PAUSED`.
  No repeated network poll-gap warnings should occur with polling disabled.
  Persistent event-loop gaps indicate this specific polling path is
  **not necessary** for a freeze, not that networking or rendering is innocent.

Use the existing safe restart script only after verifying the changed
Network source is in the **local** checkout and saving temporary UI state:

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
POST_APOLLO_UI_LAG_PROBE=1 POST_APOLLO_NETWORK_POLL_PAUSED=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Verify both variables in the running Quickshell process and capture a
comparable Radio-stopped/CAVA-resumed interval. To restore the baseline
polling behavior while **keeping the lag recorder enabled**, deliberately
relaunch without the Network pause flag:

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Avoid changing the MPD, CAVA, and Network conditions together: use
comparable windows before and after, and distinguish a genuinely quiet
interval from evidence that the issue was fixed. Neither mode changes the
operator's network configuration.

## October 22 controlled isolation // hidden Notifications history model

**State:** opt-in diagnostic experiment, not an optimization or verified fix.

`POST_APOLLO_NOTIFICATIONS_HIDDEN_REBUILD_PAUSED=1` at Quickshell
launch prevents the persistent-but-closed Notifications Hub from clearing,
filtering, sorting, and refilling its 300-entry filtered HISTORY ListModel.
When the menu opens, it immediately rebuilds that model from the current
NotificationsService state, then resumes the normal revision-driven updates.
A queued zero-delay timer that fires *after* closing is also suppressed.
The default without the flag preserves the original behavior.

The switch does **not** pause NotificationsService, events received from
browsers/apps, popup delivery, history persistence, other consumers of
NotificationsService, or the separately updated Manager DND policy model.
It changes only the hidden window's derived history ListModel. The panel
remains mapped throughout; do not toggle `visible` to isolate this work.

On startup with the flag, logs show exactly one:
`SYNTAGMA_BG_PROBE // notifications hidden-history rebuild PAUSED while closed`.
While the menu remains closed, the prior `notifications rebuild synchronous=`
entries should disappear. An intentional menu open should refresh history
to include notifications received while closed. Do not log private content.

For a direct comparison to the preceding **Network-polling-paused** capture,
leave both isolation flags enabled and keep MPD stopped, CAVA running, and
the Hi-Fi and Notifications panels closed:

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_NETWORK_POLL_PAUSED=1 \
POST_APOLLO_NOTIFICATIONS_HIDDEN_REBUILD_PAUSED=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Save temporary UI state first. After a measured interval, snapshot with
`qs log --tail 3000 > "$HOME/notifications-hidden-pause-test.log"`.
Unlike `qs log --follow`, this does not leave a log reader running.

To restore the Network-only test condition while retaining the lag probe:

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_NETWORK_POLL_PAUSED=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

**Interpretation:** long event-loop stalls despite both pauses rule out
these specific closed-history rebuilds and Network subprocess polls as
*necessary* causes. Fewer stalls in one session alone do not prove causality;
compare similar intervals. This does not isolate notification service I/O,
popup rendering, or shared Qt/QML work outside the filtered history model.

## October 22 // first-stall out-of-process thread sampler

**State:** proposed diagnostic, synthetic tests only; live operator run pending.
**Ownership:** this script and runbook are independent of actively edited
`modules/Mediaplayer.qml`; do not change the Media worker's source in this pass.

The earlier opt-in 100ms QML timer cannot run *during* a blocked Qt event
loop. `scripts/syntagma_quickshell_thread_sampler.py` instead reads
`/proc/<pid>/task/<tid>/stat` (plus advisory `wchan`) every 250ms from an
**independent Python process**, writing one JSON record per sample to
stdout. It can therefore observe Quickshell's thread CPU consumption while
QML timers are not firing. It measures kernel thread scheduling information,
**not QML functions, user text, GPU utilization, or stack traces**.

- Default duration: 180 seconds; interval: 250ms. CLI constraints are
  1–1800 seconds and 100–5000ms per sample.
- Auto-selects the most recently started same-user process whose comm is
  `quickshell`. It can be overridden with `--pid` for verified cases.
- `main.cpuPct` is the process-leader thread's percent of one logical core
  (100%=one fully occupied logical CPU); `totalCpuPct` sums all read threads.
- `sampleIntervalMs` helps identify whether *the external sampler* also
  experienced a scheduling gap; thread `state` and `wchan` are advisory.
- If Quickshell exits or PID identity changes, the capture stops. It never
  automatically restarts Quickshell, mutates a source file, runs `qs log
  --follow`, signals any process, or needs elevated privileges.
- Does not store track names, notification bodies, network data or argv.

### Operator procedure

Verify the script is present in the actual local checkout after review,
merge, and pull. If the current Quickshell runtime already has the previous
`POST_APOLLO_UI_LAG_PROBE=1`, `POST_APOLLO_NETWORK_POLL_PAUSED=1`,
and `POST_APOLLO_NOTIFICATIONS_HIDDEN_REBUILD_PAUSED=1` flags, preserve
that runtime. **Do not restart merely to start this external sampler.**

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
python3 -B "$qsdir/scripts/syntagma_quickshell_thread_sampler.py" \
  --duration 180 --interval 0.25 > "$HOME/quickshell-thread-sample.jsonl" &
echo "SAMPLER_PID=$!"
```

Use the desktop normally and note the approximate time of any visible
freeze. The script writes for three minutes and stops on its own. Later,
capture the corresponding existing Quickshell diagnostics without a
persistent log-reader process:

```bash
qs log --tail 3000 > "$HOME/quickshell-first-stall.log"
```

Share both files for timestamp alignment. The event-loop log `tsMs` and
sampler JSONL `tsMs` are Unix milliseconds; process CPU percentages are
computed using actual monotonic elapsed time between samples.

**Interpretation:** near-100% main-thread CPU immediately before or during
a stall strengthens a QML/main-thread computation hypothesis. A sleeping
main thread with an active render thread strengthens a different avenue.
If the independent sampler also has long `sampleIntervalMs`, investigate
OS scheduling, resource contention, or machine-wide stalls. Neither
case names the responsible QML function without deeper profiling.

### Media worker coordination // proposed CAVA recovery mitigation

The prior freeze capture with Network and Notifications both paused
recorded a **33,993ms** delayed event-loop tick and **265 slow CAVA
callbacks (8.52 seconds total)**, many clustered around recovery.
These measurements support checking whether buffered CAVA stdout and
repeated scene updates amplify recovery latency, **not** a claim that CAVA
caused the initial unresponsive period. The operator had already reproduced
freezes while CAVA's process was SIGSTOP'ed.

Proposed bounded Media-owned implementation (not changed by this PR):

1. Keep the 20-bar default, PipeWire input, MPD independence, and 15fps
   output intent. Do not change radio playback or palette/glow ownership.
2. Make CAVA stdout ingestion cheap and latest-wins: retain only the most
   recent well-formed raw frame; discard obsolete intermediate visual states.
3. At most once per visual tick (~67ms), parse/apply the most recent
   pending frame to `levels`. Prevent queued frame bursts from spawning
   hundreds of distinct bar/halo updates.
4. Report **aggregate** accepted/dropped/input counts instead of emitting
   a synchronous warning per slow frame during recovery.
5. Use a separate opt-in flag and compare stall time plus recovery time
   before promoting any behavior change to the default.

**Collision boundary:** the other Media chat owns `modules/Mediaplayer.qml`
and has been making rapid commits. No Media files or CAVA config were
modified in this diagnostic branch. Coordinate integration before touching
the shared `stdout: SplitParser` or `receiveCavaFrame` seam.

## October 23 // opt-in JavaScript array-copy hotspot observations

**Status:** source-only diagnostic on review branch. The operator's `eu-stack`
capture (Quickshell PID 3586090, TID 3586090) found Qt V4 inside
`ArrayPrototype::method_slice` during a QML signal evaluation. That stack
does NOT name the QML expression or show that the same operation explains
every long UI stall. It suggests a narrow measurement, not a fix.

The new launch flag `POST_APOLLO_ARRAY_COPY_PROBE=1` is disabled by default.
It adds only guarded, in-process measurements to two unowned copy paths:

- `services/system/GraphHistory.qml`: the `linePoints`, `downsampleHistory`,
  and `appendBounded` helpers. Five-second *activity-driven* aggregates
  report function, call count, longest input-array size, sum of copy times,
  total function time, maximum function time and timestamp. Uses no timer
  or new subprocess. Each `GraphHistory` instance aggregates separately;
  if no calls occur, no graph report is emitted.
- `services/notifications/NotificationsService.qml`: **one-shot on-load**
  timing of `entries.slice()` and the surrounding history parse/normalize/
  prune path. Reports only scanned/retained counts and milliseconds.
  Notification content, IDs, URLs and history JSON are never logged.

Existing `POST_APOLLO_UI_LAG_PROBE=1` measures CAVA receive callbacks and
event-loop gaps. We intentionally do NOT change `modules/Mediaplayer.qml`
here: its CAVA ambient-height binding includes `levels.slice().sort()`,
but the Media worker actively owns that surface. Its existing probe
reports overall callback cost, not the inner slice duration. Therefore
**absence of graph/history hotspots does not clear Media**.

### Controlled trial

After review, merge and pull, verify the changed source is in the real
Quickshell checkout, save temporary UI state, and restart once with both
array and event-loop probes enabled. To reproduce the previous
Network/Notifications-paused conditions, keep their two opt-in flags:

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_ARRAY_COPY_PROBE=1 \
POST_APOLLO_NETWORK_POLL_PAUSED=1 \
POST_APOLLO_NOTIFICATIONS_HIDDEN_REBUILD_PAUSED=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Then use the desktop under a comparable audio workload. Save the log:

```bash
qs log --tail 3000 > "$HOME/quickshell-array-copy-test.log"
```

Expected diagnostic prefix: `SYNTAGMA_ARRAY_PROBE //`. Startup history
loading should emit one notification-history record if valid saved history
is available. Graph records appear only when those helper functions run.
Match `tsMs` with `SYNTAGMA_LAG_PROBE` intervals but do not claim temporal
correlation proves causation. Aggregate `workTotalMs` and `copyTotalMs`
overlap, so do not add them as independent workloads.

**Rollback:** relaunch without `POST_APOLLO_ARRAY_COPY_PROBE=1`; the
underlying graph and notification-history behavior is otherwise unchanged.
To restore baseline Network and Notifications behavior as well, also
omit their two pause flags. No persistent state or schema changes.

**Media handoff:** Only after coordination with the Media owner, consider
a separate gated counter around `cavaAmbientTargetHeight` and its
20-value slice/sort binding, rather than modifying it in this branch.

## October 24 // Music CAVA A/B trial plus radio PAUSE/STOP observation

**Status:** operator-approved experimental fix + measurement, source/CI
verification only. **Not** an accepted default or a confirmed freeze fix.
**Ownership:** narrow `modules/Mediaplayer.qml` seam has another Media
worker; keep this as an isolated DRAFT PR pending its integration review.

### Original mode versus latest-wins mode

- `POST_APOLLO_CAVA_TRIAL_PROBE=1` adds five-second aggregate-only
  `SYNTAGMA_CAVA_TRIAL` records. Off by default. It also suppresses
  the older per-frame `SYNTAGMA_BG_PROBE // media cava-frame synchronous`
  warnings (when the old UI lag probe is on), avoiding logarithmic
  stdout inflation during recovery; the old five-second summary remains.
- **Original**: leave `POST_APOLLO_CAVA_COALESCE` unset. Each accepted
  stdout frame runs the existing CAVA QML decode, levels deduplication,
  20 bars, and visualizations. Diagnostic counters do not change playback.
- **Optimized trial**: set `POST_APOLLO_CAVA_COALESCE=1`. Each received
  frame is cheaply validated; only the latest well-formed raw frame
  remains pending. A single 67ms timer renders at most one pending
  frame per tick. All obsolete pending frames are overwritten and counted
  rather than initiating repeated level binding/animation work.
- **Both** use the single existing 15-FPS CAVA subprocess and MPD observer.
  Neither touches PipeWire source selection, MPD transport, Radio Browser,
  Hub bridge, visual palette, CAVA config, nor the underlying output data.
  The optimized mode does **not** prevent `SplitParser` from delivering
  individual lines; it bounds only downstream model/visual updates.
- Aggregate metrics: `received`, `applied`, `dropped`, `changed`,
  `invalid`, `applyTotalMs`, `maxApplyMs`, `pending`, `mpdPlaying`, `tsMs`.
  In the optimized mode, `received` includes invalid input lines; the
  `dropped` count is only valid frames overwritten before a visual tick.
  Values measure synchronous handler time, not GPU repaint duration.

### Operator workflow (one mode at a time)

After Media owner review, merge and pull, use the desktop normally,
and save temporary state before restarting Quickshell. For comparison,
keep Network/Notifications flags the *same* in both modes. Their
pauses are optional; do not change several conditions between trials.

Original A (measurement only):

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_CAVA_TRIAL_PROBE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Optimized B (same measurement plus experimental change):

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_CAVA_TRIAL_PROBE=1 \
POST_APOLLO_CAVA_COALESCE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Verify each runtime actually inherited the flags:

```bash
pid="$(pgrep -n -x quickshell)"
tr '\\0' '\\n' < "/proc/$pid/environ" | rg '^POST_APOLLO_(UI_LAG_PROBE|CAVA_TRIAL_PROBE|CAVA_COALESCE)='
```

Expected `SYNTAGMA_CAVA_TRIAL // startup mode=original` or
`startup mode=coalesced` in that instance's log. If no marker exists
do not draw a performance conclusion. Run a comparable radio PLAY →
PAUSE → browser show sequence, with ordinary window load; no need to
open all widgets. Stop the trial and recover your desktop if lag is severe.

The current `qs log --tail 3000` may select a **new Quickshell instance**
after a reset, losing the old diagnostic data. For a survivable recording
start a short-lived separate reader BEFORE each test:

```bash
qs log --follow > "$HOME/cava-trial-current.log" 2>&1 &
echo "QS_LOG_READER_PID=$!"
```

The reader creates additional log I/O, so note it when comparing A/B.
Stop that particular reader when done, using its printed PID. Never
kill arbitrary `qs` processes by name. Review the log for personal
contents before uploading; other widgets may log their own metadata.

### Read-only radio lifecycle evidence

`scripts/media/media_pause_state_probe.py` samples only the existing
user-owned controller's `snapshot` command (no playback mutation),
collecting `mpdState`, controller ownership, loaded source category,
sanitized relay state, and byte-count delta. It never emits station
names, raw URLs, relay tokens, queue IDs, or controller error details.

```bash
python3 -B "$qsdir/scripts/media/media_pause_state_probe.py" \
  --samples 20 --interval 2 > "$HOME/media-radio-state.jsonl" &
```

Start that bounded observer while radio is playing, press PAUSE in Hi-Fi,
then begin the browser show. You can separately compare STOP if safe.
`relayState=streaming` may be a *last recorded state*, not proof a live
socket is still open. An increasing `relayBytesDelta` supports continuing
relay traffic; a constant byte count is not proof the TCP connection
was torn down. Snapshot calls may be delayed by other controller work.

### Recovery and interpretation

**Rollback:** Restart Quickshell without `POST_APOLLO_CAVA_COALESCE=1`.
To eliminate all experiment overhead also omit
`POST_APOLLO_CAVA_TRIAL_PROBE=1` and any older optional lag probes.
No audio controller, MPD service, PipeWire settings, queues, persisted
files, or media policy is changed by this experiment.

If B reduces long UI stalls or recovery, inspect its dropped/applied
counts to quantify contribution. If stalls remain, CAVA model updates
are not sufficient to explain them. This does NOT override the earlier
observation of freezes while CAVA was suspended, nor identify the
underlying main-thread JavaScript signal from a single stack snapshot.

## October 24 // CAVA coalescing promoted to the normal launch path

**Scope and authorization:** Following the operator's repeat observation of
severe lag on an ordinary PC/Quickshell restart and significant improvement
after launching with `POST_APOLLO_CAVA_COALESCE=1`, the CAVA latest-frame
visual update path is promoted to the intended default. This is an operational
mitigation, **not** a verified single root cause or final performance sign-off.
Other optional probes were also enabled in the successful experiment, so
their independent effects have not been isolated.

**Normal Quickshell startup:** no special `POST_APOLLO_*` environment flags
are necessary for CAVA coalescing. `modules/Mediaplayer.qml` now treats
`POST_APOLLO_CAVA_COALESCE` unset, blank, or `1` as coalescing enabled. It
still uses the same CAVA process and 20-bar UI, validates frames, and applies
only the last valid pending frame per approximately 67ms visual tick.

**Explicit rollback to the previous frame-per-event behavior:**

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
POST_APOLLO_CAVA_COALESCE=0 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

**Opt-in observation without modifying the optimized default:**

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_CAVA_TRIAL_PROBE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

The two optional measurement flags remain disabled on ordinary launches,
avoiding continuous diagnostic log traffic. The existing A/B capture
procedures above remain valid **only** when the "original" case explicitly
sets `POST_APOLLO_CAVA_COALESCE=0`.

**Verification gate:** GitHub source/CI checks establish configuration and
logic contracts; they cannot verify sustained desktop responsiveness. After
merge and local pull, verify a *normal*, unflagged restart is responsive during
the specific radio PLAY → PAUSE → browser-show transition and during ordinary
work. If severe freezes recur, compare against the same launch with temporary
probes and keep the fault open. No automatic audio/MPD/radio-controller or
notification behavior changes are authorized by this decision.

## October 26 // subprocess completion to QML array-copy stall discriminator (draft)

**Evidence:** A live 100% Quickshell main-thread CPU capture on October 26
at 08:43:10 EDT recorded `QProcess::finished` -> QML signal expressions ->
`ArrayPrototype::method_slice` -> Qt allocation. The stack does not identify
the originating QML file. Do not label an individual service as the cause yet.

**Opt-in source-only trace:** `POST_APOLLO_SUBPROCESS_LAG_PROBE=1`.
There is **no additional timer, subprocess or polling**. The flag is off by
default and does not change behavior, signal connections, saved state,
network access, visual layout, or subprocess commands.

This first bounded seam records `SYNTAGMA_SUBPROCESS_PROBE //` stage markers
*before* potential slow work in the existing GitHubService collectors/exits,
GitHubAttentionProvider completion and parsing, HospitalAuditService completion
and auditing, and HospitalRoundsService's array-copy / sort and metrics work.
The traces contain only a static service/stage label, size/count, and `tsMs`.
No CLI payload, repository slug, audit JSON or notification text is logged.
An unmatched `:begin` marker can localize a blocking handler; a paired
`:end` marker bounds it. A negative result **does not clear other services**.

This adds no general-purpose monkey patch of `Array.prototype.slice`, no
instrumentation to Media's separately owned CAVA handler, and no interception
of every QML signal. GitService has a separate startup/refresh trace; do not
confuse it with this service-completion coverage.

**Trial gate:** draft PR must pass source guards, receive review, be merged,
and be explicitly applied to the live checkout *before* changing the
Quickshell launch environment. Never reset/overwrite the dirty checkout.
After the operator authorizes a controlled restart, use the already approved
safe-restart method with the new flag and `POST_APOLLO_UI_LAG_PROBE=1`,
then correlate the last stage markers before a delayed event-loop tick.
Rollback by restarting without the new environment flag. The resulting
logging and the runtime causality claim must be verified separately.

## October 26 // idle freeze follow-up, Git and SystemTelemetry completion coverage (draft)

**Observation:** the operator's opt-in, live idle-desktop log
`quickshell-subprocess-diagnostic.log` recorded event-loop delays of about
19.8s, 44.8s, 4.0s, and 37.9s even with Git/Hospital/Notifications menus closed
during several of the incidents. The instrumented GitHub and Hospital
completion callbacks returned promptly in the sampled sections and were not
running immediately before those major stalls. This is **not** proof that
GitHub, Hospital, or QProcess cannot cause other stalls. The earlier
100%-CPU native stack still shows `QProcess::finished`, QML signal evaluation,
and `ArrayPrototype::method_slice`, without source-file provenance.

The next draft extends the **existing**, opt-in
`POST_APOLLO_SUBPROCESS_LAG_PROBE=1` flag. There is no new flag, timer,
subprocess, mutation, or polling frequency:

- `services/git/GitService.qml`: mark repo-scan and refresh `DONE` messages
  before/after consuming them, in both the ordinary and optional startup-trace
  paths. During refresh `DONE`, independently bracket
  `publishPendingModels()` and `refreshed()`. Log action-process exit
  fallback only when it actually runs. **Do not log every COMMIT or other
  per-line protocol row.** No paths, commit messages, subjects, remotes, or
  operation payload are logged.
- `services/system/SystemTelemetry.qml`: mark existing stdout completion,
  JSON parse, array publication, refreshed and monitor-observation signals,
  and stderr completion before/after. Logs contain only static stage names,
  payload character count or row count, and wall-clock timestamps; never
  process lists, thermal sensor measurements, source paths, or JSON.
- CI executes the new source guard, checking opt-in gates, entry/return
  markers, existing subprocess counts, and no added diagnostic timers.

**Limits:** markers on a single main thread cannot see the operations
inside Qt before the QML handler begins. Both bracketing markers may be
present even if a callback caused *deferred* heavy work. Absence of new
markers immediately before the next delay excludes only these narrow
instrumentation boundaries, not all Git, system, compositor, or Media work.
A slow `Array.slice()` in another binding can remain unidentified.

**Rollout:** draft PR and source-only checks do not activate the diagnostic.
The operator's current live process is independent of GitHub; do not
pull/restart/reset the dirty checkout without separate authorization.
After authorized review/merge and a controlled local verification,
correlate `SYNTAGMA_SUBPROCESS_PROBE` stage timestamps with the existing
`SYNTAGMA_LAG_PROBE` event-loop delays. Keep the original native-stack
evidence for comparison. Rollback by leaving the flag unset at the next
authorized Quickshell launch; the default behavior and metrics are unchanged.


## October 28 // V5 main-thread CPU / native-stack source attribution (draft)

**Evidence:** the operator's independent thread sampler measured sustained
~98–99% use of one logical CPU by the Quickshell main thread during the
49.18-second 10:27 EDT stall and other episodes. The native `eu-stack`
capture for PID/TID 4040770 again shows `QProcess::finished` ->
`Process::onFinished` -> QML bound signals -> `ArrayPrototype::method_slice`
-> Qt array allocation. It **does not** identify the QML file or prove
that the array copy accounts for an entire long stall.

**New diagnostic boundary:** extend the existing opt-in
`POST_APOLLO_SUBPROCESS_LAG_PROBE=1` to additional uninstrumented,
array-processing completion paths without adding any subprocesses or timers:

- `services/git/GitHistoryService.qml`: begin/end around the existing stdout,
  stderr, and exit handlers on its six query/reflog/inspect/detail/diff/action
  subprocesses. Each marker uses a static process slot/stage and an output
  character count on entry, never the output itself.
- `services/hospital/HospitalService.qml`: begin/end around each bounded
  history-commit array-copy/append and the final topology publication. The
  existing command limits output to 36 commits. Markers carry counts only.
- Source-only CI tests assert opt-in gating, paired markers, unchanged
  process/timer counts, and no sensitive data in the logger. No producer
  commands, polling intervals, topology semantics, UI, or mutation paths change.

**Interpretation:** a `:begin` without the matching `:end` around a lag
or native stack is a lead to investigate further, not proof of causation.
Neither path is guaranteed to be running during an idle freeze.
Existing GitService/SystemTelemetry and HospitalAudit/GitHub probes remain
unchanged. Uninstrumented completion paths still exist.

**Rollout:** draft only. Do not merge, pull, or restart until reviewed and
approved. After an authorized merge, the current opt-in subprocess flag
automatically enables these labels on the next controlled Quickshell launch.
Rollback: relaunch without that flag; no persistent data is changed.
