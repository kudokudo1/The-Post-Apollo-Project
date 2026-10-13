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


## Third diagnostic gate // DONE body looks fast; callback remains slow

**Operator's October 13, 2026 trace (before this proposed patch):**

```text
SYNTAGMA_LAG_PROBE // event-loop interval 2714ms (target 100ms) // git=false hospital=false notifications=false
SYNTAGMA_STARTUP_TRACE // git slow refresh callback // LIVE QUICKSHELL :: /var/home/mapple/.config/quickshell // tag=DONE duration=2999ms
SYNTAGMA_STARTUP_TRACE // git refresh finished // LIVE QUICKSHELL :: /var/home/mapple/.config/quickshell // wall=4167ms lines=376 callbackSum=3011ms callbackMax=2999ms
SYNTAGMA_STARTUP_TRACE // git DONE phases // LIVE QUICKSHELL :: /var/home/mapple/.config/quickshell // state=0ms publish=1ms localSelection=1ms remoteSelection=1ms revision=0ms available=0ms refreshedSignal=0ms followup=0ms // localRows=25 remoteRows=292 topologyRows=48 stale=false
```

The `DONE` body measurements account for just a few milliseconds,
yet the enclosing SplitParser callback takes roughly three seconds.
**This does not demonstrate that model publication, signal emission,
or branch-list processing individually took three seconds.** Work may
be occurring during the diagnostic console emission or across the
QML/JS return boundary, including engine bookkeeping and deferred
binding work. This trace does not distinguish those possibilities.

### Proposed opt-in boundary measurement

The same `POST_APOLLO_GIT_STARTUP_TRACE=1` switch now also produces
`SYNTAGMA_STARTUP_TRACE // git DONE boundary` with four fields:

- `handler`: start of SplitParser's callback to last timestamp inside
  `consumeRefreshLine`, including its diagnostic log;
- `afterReturn`: last internal timestamp to first timestamp after
  `consumeRefreshLine` returns to the SplitParser handler;
- `log`: cost of emitting the existing `git DONE phases` warning;
- `outer`: total synchronous callback duration, measured as before.

Expect approximately `handler + afterReturn = outer`; minor
rounding and clock granularity differences are possible.
The `handler` value is an inclusive wall-clock span, not CPU-time.
A long `log` points to diagnostic logging itself. A long
`afterReturn` suggests expensive return-boundary/engine activity
but **does not prove QML binding reevaluation**. A long `handler`
with a short `log` suggests unmeasured work or a timing anomaly
inside the function; profile before changing model logic.

The boundary receipt is returned only in traced mode. No window
lifecycle, model contents, Git commands, service scheduling, or UI
behavior is changed. Source checks are not live-performance evidence.

After this patch is merged and the operator's clean local checkout
receives it, run the existing one-restart, menus-closed procedure.
Collect the paired `DONE phases`, `DONE boundary`,
`slow refresh callback` and event-loop lines from the **same**
session. Do not diagnose from output truncated by terminal width.
