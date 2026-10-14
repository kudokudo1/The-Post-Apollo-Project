# Syntagma // GitService startup and refresh callback trace

**Status:** disabled-by-default diagnostic, **not** performance fix.
**Owner:** Nurse 3c, October 13, 2026.
**Source scope:** `services/git/GitService.qml`. No changes to surface,
focus, opening, transport, menu state, audio, glows or effect lifecycles.

## Motivation

After an opt-in Quickshell timer probe registered ~3,074, ~3,408 and
~1,432 ms UI event-loop delays shortly after Quickshell restart with all
Git/Hospital/Notifications menus closed, a subsequent 20-second CAVA
suspension interval **and** a subsequent 20-second CAVA-running interval
produced no new warnings. A single quiet interval cannot prove CAVA is
responsible or exonerated; Quickshell startup work remains an important
hypothesis.

Static source audit confirms `GitService.qml` calls
`discoverRepos()` in `Component.onCompleted`. Git's `GitW.qml`
constructs one `GitService`, and Hospital's `HospitalW.qml`
constructs two instances (`hospitalEvidenceGitService` and
`attentionCatalogGitService`) regardless of those menus being open.
Each `discoverRepos()` launches a background shell command that
enumerates local projects and may request up to 200 remote repository
entries with `gh repo list`; QML `SplitParser` then handles rows
synchronously, and `DONE` leads to a refresh. These are potential
contributors to startup UI work, **not verified sources of the stall**.

## Opt-in measurement

The opt-in environment variable is
`POST_APOLLO_GIT_STARTUP_TRACE=1`. Without that exact value, no
timestamps/statistics are recorded and the existing QML callbacks
invoke the same parser methods as before.

Each `GitService` instance records three kinds of log events:

- `git scan started`: synchronous time around discovery setup;
- `git scan finished`: wall-clock time for the shell scan, number of
  stdout lines, cumulative synchronous `consumeRepoLine` callback
  wall time, and maximum cost of a single callback;
- `git refresh finished`: corresponding wall and callback metrics for
  `consumeRefreshLine`.

Logs have prefix `SYNTAGMA_STARTUP_TRACE`.
`wall` includes external process time and scheduling delay; the callback
sum/max includes QML downstream property/model reactions. Both are
wall-clock measurements and do **not** give stack traces or true thread
CPU time. A callback count is not a count of repositories. The label
uses the service's repo label and configured query/path; instances may
have similar labels. Failures or subprocesses without a `DONE` line
may show a start event without a finish event.

## Test on the operator machine

Ensure the **real** checkout at `~/.config/quickshell` has received
the merged change; do not operate from the separate
`~/.local/share/post-apollo-dev-runtime` repository.

```bash
qsdir="$(readlink -f ~/.config/quickshell)"
git -C "$qsdir" status --short
grep -n 'POST_APOLLO_GIT_STARTUP_TRACE' "$qsdir/services/git/GitService.qml"
```

If local changes exist, preserve them and reconcile the update; do not
run a destructive reset. After saving any unfinished UI interaction,
restart intentionally with **both** baseline and startup traces enabled:

```bash
POST_APOLLO_UI_LAG_PROBE=1 \
POST_APOLLO_GIT_STARTUP_TRACE=1 \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

Do **not open any menu** for a short idle observation.
Collect the ordered output (prefer keeping timestamps if your
Quickshell build displays them):

```bash
qs log --tail 500 | grep -E 'SYNTAGMA_(LAG_PROBE|STARTUP_TRACE)'
```

The purpose is to compare the event-loop intervals against the actual
startup scan and refresh completion. One normal startup should
suffice for a first comparison. Do not deliberately spam-click menus
or enable the known-crashing unmap/remap pilot.

Example only (invented timings; **not** a measured result):

```text
SYNTAGMA_STARTUP_TRACE // git scan started // ... // setupSync=2ms
SYNTAGMA_STARTUP_TRACE // git scan finished // ... // wall=1600ms lines=17 callbackSum=9ms callbackMax=5ms
SYNTAGMA_LAG_PROBE // event-loop interval 3211ms (target 100ms) // git=false hospital=false notifications=false
```

If callbackSum/max are tiny while the gap is huge, the discovery output
handler is less likely to be the entire cause. If a callback takes
seconds and aligns with the delayed Timer, it is a strong profiling
lead. Still check initial QML object creation, other network/audio
callbacks and renderer work as alternative contributors.

## Restore the default

```bash
env -u POST_APOLLO_UI_LAG_PROBE -u POST_APOLLO_GIT_STARTUP_TRACE \
  bash "$qsdir/scripts/restart_quickshell_safe.sh" "$qsdir"
```

This patch intentionally does not alter startup sequence, timers,
background work, query breadth, output processing, visible UI,
or the persistent Git/Hospital window mapping that avoided the earlier
Wayland/Qt crash.

## Acceptance boundary

CI validates the diagnostic's source guard and existing lifecycle
safety contracts. **The probe is unverified at the user's live Qt
runtime until a single opted-in restart is observed.** An optimization
or timing-based deferral is not authorized by the measurement alone;
coordinate any shared GitService behavioral change with its owner.


## Second diagnostic gate // source-level callback identified as expensive

**Operator trace on October 13, 2026, before this refinement:**

```text
SYNTAGMA_STARTUP_TRACE // git refresh finished // taskbars-post-apollo :: taskbars-post-apollo // wall=888ms lines=272 callbackSum=6ms callbackMax=3ms
SYNTAGMA_STARTUP_TRACE // git refresh finished // LIVE QUICKSHELL :: /var/home/mapple/.config/quickshell // wall=4604ms lines=376 callbackSum=3409ms callbackMax=3398ms
SYNTAGMA_STARTUP_TRACE // git refresh finished // LIVE QUICKSHELL :: /var/home/mapple/.config/quickshell // wall=4687ms lines=376 callbackSum=5ms callbackMax=2ms
SYNTAGMA_LAG_PROBE // event-loop interval 3697ms (target 100ms) // git=false hospital=false notifications=false
```

The **3,398 ms maximum single callback**, within a 3,409 ms callback
total, is strong evidence of a single synchronous QML refresh-result
handler dominating the stalled interval. The similar two LIVE QUICKSHELL
service identities have radically different costs; the first measurement
does not identify which specific view's bindings were involved. A
preceding 3,068 ms missed timer interval was also logged. Thus there
may be **more than one expensive callback** or logging order/timing
effect; do not assume the 3,398 ms callback explains every gap.

**Refined opt-in trace (same environment flag):**
- Any `consumeRefreshLine()` callback taking at least 100 ms logs
  `SYNTAGMA_STARTUP_TRACE // git slow refresh callback` with its
  **row-type tag only** (`DONE`, `COMMIT`, etc.) and duration. The
  raw repository output is intentionally not logged.
- For a `DONE` row, log
  `SYNTAGMA_STARTUP_TRACE // git DONE phases` with synchronous
  wall-clock cost of: finishing `refreshing` state; publishing
  pending models; restoring local/remote selection; incrementing
  topology revision; updating availability; calling the `refreshed()`
  signal; and queuing any follow-up refresh. Report pending row
  counts and whether the result was stale.
- These timings execute only if `POST_APOLLO_GIT_STARTUP_TRACE=1`;
  normal source ordering and business logic are preserved.

**Interpretation:** If `tag=DONE` is slow and `publish` is large,
the likely cost is rebuilding branch/topology rows or the synchronous
QML bindings those model mutations trigger; do not assume the loops
themselves are intrinsically expensive. If `refreshedSignal` is
large, inspect consumers attached to `GitService.refreshed`.
If a different tag is slow, investigate that row's QML processing
path. Compare against the existing `SYNTAGMA_LAG_PROBE` lines
without opening menus or running repeated unsafe experiments.

This stage still measures the **existing** code only. Any
optimization requires separate evidence and coordination with
other workers touching Git or Hospital UI.


## Third diagnostic gate // model publication consumes nearly the entire freeze

**Operator session recovered from persisted `log.log` at 18:45 EDT,
October 13, 2026.** The earlier terminal output truncated the crucial
slow `DONE phases` line. These measurements are for the slow
`LIVE QUICKSHELL` refresh, not the distinct, fast service instance:

| Time | `publish` | `callbackMax` |
|---|---:|---:|
| 18:24:59 | 2,979 ms | 2,999 ms |
| 18:29:34 | 3,057 ms | 3,091 ms |
| 18:29:39 | 3,337 ms | 3,350 ms |
| 18:34:10 | 2,789 ms | 2,812 ms |
| 18:34:16 | 3,030 ms | 3,054 ms |

Across these five events, the mean `publish` duration is ~3,038 ms.
Each refreshed roughly 25 local branches, 292–294 remote branches,
and 48 topology rows. This identifies the **model publication path**
as the dominant synchronous measured phase, not which specific model
mutation, QML binding, or delegate creation made it expensive.

The implementation currently assigns repository metadata, clears three
`ListModel` instances, and appends each pending local, remote,
and topology record. A slow `append()` can include model-notification
and binding costs; a large duration does not prove raw JS loops alone
are the problem. The two LIVE QUICKSHELL service instances must not be
conflated; one originally completed the DONE work in ~27 ms.

### New opt-in subphase trace

The same `POST_APOLLO_GIT_STARTUP_TRACE=1` gate now emits
`SYNTAGMA_STARTUP_TRACE // git publish phases` **after**
`publishPendingModels()` has completed, breaking down:

- `metadata` — scalar repository/status property updates;
- `clears` — clearing the three live QML models;
- `local` — appending pending local branch rows;
- `remote` — appending pending remote branch rows;
- `topology` — appending pending topology rows;
- `total` — enclosing publication time measured by the existing DONE trace.

These durations should approximately add to `total`, modulo
millisecond clock granularity. No extra signal, scheduler, additional
refresh, model mutation, UI lifecycle or logging inside loops is added.
In normal mode this returns no measurement object and emits no extra
log lines. Runtime validation remains pending.

**Next gate:** merge only after shared GitService ownership / CI review,
pull into the actual clean Quickshell checkout, and collect exactly one
normal startup, menus closed, with both trace flags set. Use the saved
plain-text `log.log` or a wide file capture rather than cropped
terminal output. If `remote` dominates, investigate repeated
`ListModel` notifications and downstream recomputation, preserving
all selectors, scrollbars, stars and existing glow semantics.
Do not preemptively delete rows, defer hidden menus, or change mapping
behavior. Continue to treat Qt/JS measured wall-time as **inclusive**,
not function-stack profiling or CPU-time.


## Fourth diagnostic gate // remote-row publication fan-out (October 14, 2026)

**Operator live opt-in restart succeeded.** The new 'git publish phases'
trace from session '4f2mngiwmt' shows LIVE QUICKSHELL with
metadata=97ms, clears=0ms, local=52ms, remote=2504ms, topology=254ms,
total=2907ms for 25 local branches, 294 remote branches, and 48
topology rows. A lag-probe line immediately afterward recorded a
3213 ms missed 100 ms timer interval with Git, Hospital and
notifications closed. Two smaller refreshes publishing 204 remote
rows each took about 1 ms total. Do not generalize from row count alone.

**Candidate fix // gate closed Git view's remote rescans:**
The Git panel deliberately remains alive while closed because of
Qt 6.11 shader-source teardown crashes. Before this change its
remoteSlider.activityPoints binding called remoteActivityPoints()
repeatedly as 294 remote rows arrived, and the hidden
remote-dropdown Repeater.model and height bindings called
remoteTargetResults(7) on the growing model even while the
dropdown was closed. Both routines access the live ListModel and
scan rows. Repeated notification-driven rescans are a likely
contributor, but individual bindings were not directly profiled.

The scoped fix in widgets/GitW.qml gates activity-point computation
behind the menu-open and Git control-page conditions, and gates
remote-suggestion model and height behind menu-open and
dropdown-open. The inactive dropdown has an empty Repeater model
and zero height. Opening the same controls restores the original
functions, ranking and visual effects. The GitService model contents,
selection and actions are unchanged. No glow, icon, color, star,
scrollbar, or selector geometry rules were changed.

**Verification gate:** CI/source checks only until live Fedora/Sway
testing. Do not claim that the 3-second stall is eliminated based on
source evidence. After a safe restart with the two POST_APOLLO trace
flags enabled, compare remote= and lag-probe duration with
2504ms / 3213ms baseline. If still slow, profile additional model
consumers rather than attempting a broad UI rewrite.
