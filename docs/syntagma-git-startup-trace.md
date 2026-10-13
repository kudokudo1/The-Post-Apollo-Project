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
