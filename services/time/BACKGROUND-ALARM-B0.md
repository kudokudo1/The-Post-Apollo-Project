# Clock Background Alarm B0 // Observer-only foundation

**State:** source and tests only. **No installation, auto-start, sound or notifications.**

## Fundamental mechanism

Quickshell currently owns `time-alarms-v2.json`, the one-second alarm scheduler,
Qt audio, alarm notifications and STOP/SNOOZE. Quickshell's `dataDir` is scoped to
the particular shell ID; the background worker must not guess it.

`AlarmBackgroundObserver.py` is an independent Python process that can run
without the graphical shell. It **only reads a caller-supplied absolute path**
ending in `time-alarms-v2.json`, validates its size, owner and V2 structure,
then prints bounded JSON assessments to stdout. It does not modify the alarm
document, emit alarm events, play sound or publish notifications. It never
reads or reports private alarm names, notes or sound file paths.

Observation labels include `FUTURE`, `ELIGIBLE_IF_OWNED`,
`MISSED_CANDIDATE`, `UNKNOWN_ARM_TIME`, `ALREADY_PROCESSED`,
`ACTIVE_RING_IN_QUICKSHELL`, `SNOOZE_PENDING`, `DISABLED` and `PAUSED`.
**Candidate** and **eligible** are diagnostic labels, not an instruction to
ring. Each snapshot carries `actuationEnabled: false` and
`ownsAlarmFile: false`. A failed read yields `REFUSED`, never a fabricated
due event.

The separate observer process uses a user-runtime `flock` to prevent
**two observers** running simultaneously. Crucially, this lock does **not**
coordinate ownership with Quickshell. It is therefore **not** authority to
play a sound or acknowledge any alarm.

## Read-only development / testing

One-shot command, using the *actual* per-shell Quickshell.dataDir from a
trusted source (not a guessed default):

```sh
python3 -I -B services/time/AlarmBackgroundObserver.py \
  --once --alarm-file "/absolute/quickshell/dataDir/time-alarms-v2.json"
```

Test fixtures can use `--at-ms 1794408000000` with `--once` to freeze
the observation instant. `--at-ms` is refused in watch mode.

`--watch` repeats read-only observations at a one-second interval and writes
changes to stdout. It holds an exclusive **observer-only** runtime lock under
`$XDG_RUNTIME_DIR/post-apollo-alarm-observer/observer.lock`. A second
observer refuses to run. No persistent records or alarm files are written.

The included `ops/systemd/user/post-apollo-alarm-observer.service` is a
**source-only, disabled systemd user-unit template**. It has intentionally
no `[Install]` section, an explicit data-file environment prerequisite and
no restart loop. Do not install/start it as a production alarm service: it
cannot produce audible alarms.

## Ownership handoff still required

Before a future service may actuate an alarm:

1. A trusted native-side process must resolve and verify the **exact**
   Quickshell.dataDir and the full saved-alarm revision.
2. Both the background process and Quickshell must enforce the **same
   single-owner lease** before changing a ring state. Merely observing process
   presence or holding a separate observer flock is inadequate.
3. Each occurrence must have a durable, atomic claim/acknowledgment
   identified by alarm ID plus expected due time (and schedule revision).
   Crash and restart behavior must be tested without double notification.
4. STOP/SNOOZE and notification route controls must dispatch to the actual
   current owner with the existing exact-occurrence authorization, rather
   than implementing a second parallel set of buttons.
5. Actual output needs an audibly verified non-GUI playback device and
   independent notification delivery, without bypassing DND/BLOCK policies.
6. Suspend/wake requires another explicit OS/runtime assessment. A normal
   systemd user process does not automatically wake a suspended or powered
   off machine.

**No automatic service activation or local-machine write is approved by B0.**

## Recovery and rollback

B0 changes only new repository files, so dropping the unmerged PR removes
it. Existing alarm schema, audio, QML owner and notification history remain
unchanged. If a future observer produces erroneous reports, stop that
observer; it has no mechanism to mutate saved alarms.
