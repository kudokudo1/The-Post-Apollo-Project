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


## Fifth diagnostic gate // repeated Git dock opening (October 14, 2026)

**Operator test clarification:** Git was opened and closed repeatedly,
with perceptible lag approximately every third opening. This is not
idle-only sampling. Live session 8lcg2b9lwmt shows numerous local Git
refreshes with publication about 365–478ms, and recurring event-loop
gaps, after the previous 2907ms slow publication was reduced.

GitW.onMenuOpenChanged previously called gitService.refresh()
unconditionally on every opening even if an identical repository's
model had just been published. The refresh runs a subprocess and
rebuilds 25 local, 294 remote, 48 topology rows, about 1.4 seconds of
total wall time, often with about 400ms of synchronous model publish.

**Scoped mitigation:** GitW records its own successful GitService
refreshed() timestamp and associated repoPath. A *passive dock-open*
skips redundant GitService.refresh() if a successful snapshot for that
same path was published less than 8 seconds ago; if old, missing,
errored, or for another repository, refresh behaves as before.
If a refresh is already running, the menu does not add another.
Explicit hotkey Refresh/discovery, repo selection, Git actions,
and view-specific refreshes retain original behavior. No timer,
GitService modification, visual/style/layout, or extra restart.

**Trade-off:** a rapid passive reopening can display repository data
up to 8 seconds old, unless the operator explicitly refreshes. The
old model remains fully interactive. This boundary is for the passive
opening path only; it is not a global network polling policy.

**Verification:** source/CI, then operator runtime stress-test
with the previous flags enabled. Track count of Git refresh finished
events, callback duration and lag-probe gaps over rapid openings,
then exercise explicit refresh and repository switching. Reducing
refresh frequency doesn't prove the unrelated 2809ms startup gap is
fixed. No runtime result yet.


## Sixth diagnostic gate // rapid Git stress test accepted (October 14, 2026)

**Operator assessment after PR #260 (commit 28c516e):**
Rapid Git clicking is substantially smoother than the original
baseline and the intermediate closed-view binding fix. The operator
reports the dock opens and closes repeatedly with only minimal,
ordinary-feeling lag; the former roughly-every-third-open hitch
is no longer prominent. This is a meaningful runtime usability
confirmation for bounded passive-open refresh reuse.

**Session 0xls3kmwmt, 11:48 EDT:**
- Two LIVE QUICKSHELL Git refresh-completion records in the short
  reporter. Two separately instantiated GitServices use that same
  label, so this is not the count of unique user-triggered openings.
- Three event-loop timer overruns: 2685ms at 11:48:10.449 when
  Git/Hospital/Notifications were closed; 645ms at 11:48:12.053
  with all three closed; 737ms at 11:48:21.720 with Git open.
- The timer timestamp indicates when it finally ran, and menu flags
  are the state at that instant, NOT causal attribution. The initial
  2685ms bootstrap gap remains unassigned.

**Source inspection:** shell.qml already logs the Git dock's
synchronous toggle time when the lag probe is enabled.
GitService logs successful refresh-completion and model publication
phase costs. These receipts can be correlated from one saved log
without modifying QML or restarting Quickshell.

**New local-only log reporter:**
Run python3 scripts/syntagma_git_lag_report.py --session 0xls3kmwmt
from the Quickshell checkout. It reads the saved log.log from that
session and reports nearby button-toggle, model publication,
Git refresh-completion, and event-loop-gap records. It never
signals, reloads, restarts, talks to Quickshell, changes environment
flags, or modifies any files. A --log /path/to/log.log option
accepts an exact saved log; with no option it uses the latest
session containing a readable log.log. Correlations are temporal,
not attribution of cause. Synthetic tests cover known log ordering,
missing diagnostic logs, and unsafe session IDs.

**Next decision boundary:** inspect the existing toggle and refresh
timeline around the 737ms event. If a slow synchronous toggle is
recorded, investigate open-panel bindings. If toggle is fast but a
DONE model publication coincides with the gap, investigate remaining
model subscribers or secondary view refreshes. If neither coincides,
investigate other startup or compositor/Qt work. Do not disturb the
now-responsive Git dock or restart solely for these measurements.


## Seventh diagnostic gate // recurring LIVE Git refresh callbacks despite fast dock toggle (Oct 14, 2026)

Operator saved report for session 0xls3kmwmt accumulated 109 Git
button toggles, 18 LIVE QUICKSHELL refresh-completion records,
and 41 event-loop overruns. Last 12 toggle handlers were mostly
1–2 ms with a single 13 ms outlier. The rapid-open interaction
is substantially improved.

From roughly 11:55:48 to 11:56:01, however, Git refreshes completed
about 1.6–1.8 seconds apart, with 400–500 ms synchronous callback work,
and 680–802 ms event-loop delays. The last recorded toggle before this
burst was 11:55:30.676, and the next at 11:56:01.512, consistent with
refreshes repeating while the menu remained open; no cause is proven.
The previous startup-only 2685ms gap is separate.

GitW caches a successful model for eight seconds on passive opening.
No normal GitService timer refreshes every ~1.6 seconds. GitService
refresh can originate from explicit actions/pages, repository discovery,
selection, or a queued followup when refreshPending/staleRead are true.
Two service instances can share the same LIVE QUICKSHELL display label.

Opt-in source refinement: With POST_APOLLO_GIT_STARTUP_TRACE=1, emit
SYNTAGMA_STARTUP_TRACE // git refresh requested with the caller's
first few JavaScript Error.stack frames, and busy/pending state.
Emit git refresh queued on repository selection while a refresh
is already running. The DONE phases message gains pendingAtDone
and followupQueued booleans. There are no new runtime refreshes,
bindings, QML model changes, timers, or UI behavior changes.
Normal executions do not create an Error stack or log these lines.

Verification: review source and CI, then single operator-safe trace
session when convenient. Open Git once for 15–25 seconds without
manually refreshing; record requested and DONE phases lines.
If request sources repeat or followupQueued remains true, identify
that caller/feedback loop first. Do not guess or suppress refreshes.


## Eighth candidate // preserve topology delegate identity on repeated Git refresh (October 15, 2026)

The operator reports substantial everyday smoothness improvements across Git,
browser tab switching, terminal output and multi-app use. This is an important
perceived-UX observation, not proof that the Quickshell changes alone caused
all system-level improvements. The long-running Post-Apollo target must avoid
unbounded state growth and idle refresh work as more services (AI, social,
notifications, weather, AppControl, Hospital) arrive.

**Current evidence:** two LIVE QUICKSHELL full graph publishes had topology
phases of 237ms/270ms (48 rows), while remote publication had fallen to
14ms/49ms. The graph's BranchMap.qml subscribes through a Repeater to the
GitService topologyModel, with per-row text, stars, glows, DropShadows and
a Canvas. Previous publishPendingModels() cleared the topologyRows model,
then appended all 48 records, re-instantiating the presentation delegates.

**Scoped candidate:** reconcile topologyRows by stable commit SHA rather
than unconditional clear+append. The algorithm reuses an identical row with
zero ListModel write notifications; moves surviving commits into their new
order, inserts newly discovered SHAs, updates only changed roles
(shortSha/parents/refsText/epoch/author/subject/lane/isHead), and removes
only rows no longer in the 48-row window. Revision signal, selection by SHA,
Canvas repaint, all BranchMap visuals and remote-only empty-repo reset are
retained. The opt-in git publish phases trace now prints a topologyDelta
summary of inserted/moved/updated/removed/unchanged rows.

**Expected behavior:** repeated scans of unchanged topology should avoid
destroy/recreating the 48 visual row trees; newly inserted leading commits
should only create new delegates and update moved/revised ones. This is a
candidate performance optimization, **not** evidence of eliminated CPU
stalls or a measured latency improvement until operator runtime testing.
Initial construction of a fresh 48-row graph still costs work, and the
other local/remote models remain unchanged. Never mask new commit content
or remove stars/glows to improve benchmarks.

**Concurrency:** GitService-only runtime code change (no BranchMap/
GitW/SelectorSlider visual or behavioral edits). Team 3r's separate
draft PR #252 includes BranchMap scroll/star work and must not be
overwritten; the service model schema and public topology interfaces
remain unchanged.

**Runtime gate:** compare opt-in topologyMs/topologyDelta across an initial
scan and subsequent explicit REFRESH of an unchanged repository (then
a real new commit/branch update). Ensure graph order, SHA selection, lanes,
star/glow preservation and scrolling remain correct. CI/source checks
only cannot prove Qt ListModel delegate runtime behavior.
