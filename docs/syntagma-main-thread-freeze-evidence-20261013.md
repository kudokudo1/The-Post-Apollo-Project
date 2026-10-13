# Syntagma // Quickshell-wide responsiveness freeze: runtime evidence

**Hospital staff:** Nurse 3c. **Date:** October 13, 2026.
**Scope:** Quickshell performance under opening / interaction with large widgets.
**State:** Proven sustained main-thread CPU saturation; exact hotspot unverified.
**Change type:** Evidence checkpoint **only** — no QML changes, no focus or surface lifecycle changes.

## Operator observation (primary signal)

The operator reports that when opening/interacting with Git/Hospital, the
*entire Quickshell* visibly lags: the compact MPD/CAVA spectrum in the dock
stops animating as well. This is **not** merely keyboard Tab latency or
window-mapping slowness. A first preliminary test included only **one open**;
later tests allowed just **two or three opens** before the lag made further
interaction difficult. Do not categorize those as successful stress tests.

The compact visualizer at `modules/Mediaplayer.qml` runs `cava` as an
independent process, parses frames with `SplitParser`, updates a 16-bar QML
array, and animates height changes. A freeze of its *display* is therefore a
useful shared-UI responsiveness symptom; it does not independently establish
whether the audio pipeline itself also stalls.

## Quantitative evidence

The operator ran

```bash
pid="$(pgrep -n -x quickshell)"
top -H -b -d 1 -n 12 -p "$pid" -o %CPU -w 220 \
  > /tmp/post-apollo-qs-threads.log
```

at approximately 16:45:43–16:45:54 local time. TIDs and observed utilization:

| Moment | Main/UI thread, TID 4070873, process PID | Other threads |
| --- | ---: | --- |
| 16:45:43 | 4.9% | QSGRenderThread 4073552 ~14.8% |
| 16:45:45 | 26.9% | QSGRenderThread ~8% |
| 16:45:47 | **98.7%** | Other shown threads at 0%; render thread not among top five |
| 16:45:48 | **99.7%** | Other shown threads at 0% |
| 16:45:49 | **99.7%** | Other shown threads at 0% |
| 16:45:50 | **98.7%** | Other shown threads at 0% |
| 16:45:51 | 35.9% | QSGRenderThread ~6% |
| 16:45:54 | 6.0% | QSGRenderThread ~9%; separate GL/driver threads ~5%/2% |

**Interpretation:** The Quickshell **main thread** consumed nearly one
logical CPU continuously for ~4 seconds. This can stall unrelated QML
animations and input processing even if the system as a whole has idle
cores. Evidence favors a **main-thread workload** (JS/QML bindings,
signal callbacks, item creation/layout, or synchronous C++ operations)
*for this specific observed interval*, not a CPU-saturated
`QSGRenderThread`. It does **not** prove which function ran, nor exclude
a GPU/driver stall in a different interval. No frame-time instrumentation
or time-aligned visual freeze marker was collected.

An earlier process-level `top` sample showed the entire Quickshell process
at ~100% of one CPU. It also showed multiple Brave processes at high CPU
usage, so the system may have concurrent scheduling pressure. `vmstat 1 20`
samples had very low swap-in/swap-out and generally low blocked-I/O
counts, despite ~5 GB occupied swap. These observations do not support
**active swap thrashing** as the leading cause.

## Source leads; not proven hotspots

In current source (`main` at
`15ab87d2731d2d6b508ba15bb53a1854578a08bc`):

- `widgets/GitW.qml`: `onMenuOpenChanged` invokes `gitService.refresh()`,
  view-dependent refreshes, and possibly `githubService.refresh()`.
  `Qt.callLater(ensureGitKeyboardControl)` also scans registered controls
  and may call `mapToItem()`; measure before optimizing.
- `widgets/HospitalW.qml`: `open()` calls
  `refreshReceptionData()`, which synchronizes receptionist collections;
  `onMenuOpenChanged` calls `ensureFirstRoomSelected()`,
  `requestOpenAudit()` and `floorService.discover()`.
  Staleness logic may initiate `auditService.runAudit(false)` and
  `githubService.refresh()`. Asynchronous external processes can still
  produce costly QML result/model updates.
- Existing startup warnings include missing `DP-5` screen objects and
  null record/property access in Hospital Reports and Git Blame. Those
  bindings warrant safe correctness fixes, **but have not been shown to
  fire repeatedly during the multi-second freeze**; do not present them
  as the performance root cause on present evidence.

## What is settled / not settled

**Settled:**
- Treat the issue as **Quickshell-wide GUI responsiveness**, not just
  Git/Hospital keyboard acquisition.
- The particular measured spike involved the main/UI thread, not the
  render thread as the highest-CPU consumer.
- Do **not** revive the Git/Hospital visibility-controlled unmap/remap
  pilots, which separately crashed on repeated opens.
- The 120 ms keyboard-focus boost-release timer is not a pre-open delay
  and has no observed causal connection to the 4-second busy period.

**Not settled:** Which QML function, binding, model change, C++ call or
resource lifecycle consumed four seconds; whether the first/open and
second/open paths have the same cause; effect of Brave scheduling
competition; whether different freezes also have a rendering cause.

## Next gated measurement

Prefer **QML Profiler** (Qt Creator or supported CLI): capture JavaScript,
binding/signal handlers, creation, and scenegraph for a **single normal**
widget opening, if a compatible profiling-enabled Quickshell build is
available. The Qt debug/profiler infrastructure is not proven present in
the operator's live binary; check availability **before** giving any launch
or attach commands. Do not blindly attach to an uninstrumented running
process.

If profiling is unavailable, use very small, opt-in, source-controlled,
reversible timings around the **open-handler synchronous paths**, then
service result callbacks. Keep the instrumentation read-only with respect
to focus, mask, window visibility, animation, and business logic; avoid
hot-reloading Qt shader-backed surfaces. Check Git and Hospital separately
and collect one opening per trial, not spam clicks.

**Safety:** This checkpoint changes no runtime code. It is compatible
with active concurrent owners working on Git, Hospital, and widget
components. Any implementation change requires re-checking current
`main` and file ownership before writing.


## Follow-up: actual opt-in event-loop probe result

**Operator runtime log, October 13, 2026, after PR #247**, with
`POST_APOLLO_UI_LAG_PROBE=1` enabled:

| Event at log emission | Reported duration |
| --- | ---: |
| 100 ms timer callback delayed while Git/Hospital/Notifications all showed `false` | **3,120 ms** |
| Git dock toggle's synchronous `toggle()` call | **10 ms** |
| Timer delay while Git showed `true` | **3,579 ms** |
| Second timer delay while Git showed `true` | **5,499 ms** |
| Further timer delay while Git showed `true` | **418 ms** |

**Key interpretation:** The **immediate Git dock-toggle code** measured
only 10 ms in this test. The long delayed timer callbacks occurred
**elsewhere in the UI event loop**. This means a blanket claim that the
toggle function itself blocks for several seconds is unsupported.

**Important timing caveat:** The timer's `git/hospital/notifications`
booleans are sampled **when the delayed callback finally runs**. The
`false/false/false` gap does *not* by itself prove that those menus
were closed for its entire 3.12 seconds; pending work from a prior menu
or earlier callback is still possible. The result *does* establish that
long timer delays can be logged at a point where no such menu is open.

**Current hypotheses, not established causes:**
- Synchronous JS/QML work or bindings from services/result callbacks,
  potentially triggered by earlier events and processed later.
- Recurring baseline work. Confirmed source examples include
  `modules/Network.qml` polling several asynchronous processes
  every 500 ms and `modules/Mediaplayer.qml` polling MPD status
  every 2,000 ms; these intervals do not prove that either service
  consumes seconds of main-thread time.
- Rendering, compositor descheduling or other scheduling delay cannot be
  categorically eliminated from timer observations alone. The separate
  `top -H` 4-second near-100%-CPU main-thread sample makes expensive
  main-thread execution a priority to profile.

**Next safe comparative gate:** Use the existing opt-in probe with a
freshly restarted shell and **no manual menu interactions** for a brief
baseline observation, then perform one normal Git opening and compare
the timestamps/delays. Preserve the full ordered log and test conditions.
If closed-menu stalls persist, attribute background callbacks first,
not window mapping or Git's `toggle()`. For a later scoped patch,
measure specific service parsing/model callbacks without removing them.
Never re-enable the previously crashing unmap/remap experiment.

No production behavior changes were made as part of this observation.


## Follow-up: clean idle baseline with music playing

**Operator's next controlled run, October 13, 2026:** After a deliberate
Quickshell restart with `POST_APOLLO_UI_LAG_PROBE=1`, the operator
did **not manually open Git, Hospital, or other menus** during the short
baseline. They explicitly reported that **music was playing**, so the
compact MPD/CAVA visualizer continued as part of the default taskbar.

The emitted `SYNTAGMA_LAG_PROBE` intervals were:

| Reported timer interval | Sampled menu states when callback resumed |
| ---: | --- |
| **3,074 ms** | git=false; hospital=false; notifications=false |
| **3,408 ms** | git=false; hospital=false; notifications=false |
| **1,432 ms** | git=false; hospital=false; notifications=false |

**Updated conclusion:** The Quickshell event loop has **multi-second
missed deadlines in a normal no-manual-menu-opening scenario**.
This weakens the hypothesis that Git or Hospital dock toggle is necessary
to trigger the issue. It does not isolate which background workload or
earlier startup callback consumed the time. The menu-state flags are
still read when each delayed timer callback executes, not sampled
continuously during the gap.

**Music distinction:** `modules/Mediaplayer.qml` starts
`cava` with `running: true`, collects frames with `SplitParser`,
and reassigns `levels` to drive animated bar heights; separately it
polls `mpc status` every 2 seconds. MPD/audio continuing to play
is not proof the CAVA input or UI visualizer caused the stall.
`modules/Network.qml` also initiates multiple network probes on a
500 ms timer, while other services can update asynchronously.

**Recommended next controlled isolation:** Compare one 20-second
no-menu interval with CAVA's *visualization process* temporarily
suspended (SIGSTOP/SIGCONT for the specific `cava` child), while
music playback continues. Use a shell trap to resume the process
automatically, and avoid broad `pkill` or permanent code edits.
This merely tests whether CAVA frame delivery is *necessary* for
the idle stalls; it cannot prove CAVA is sufficient or distinguish
Qt/driver issues on its own. Re-enable CAVA after the short trial
regardless of outcome.

**No widget code, focus policy, renderer, or lifecycle modified**
to record this runtime observation.
