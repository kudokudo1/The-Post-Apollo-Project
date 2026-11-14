# CLOCK // BG1-B2B6 Mounted Old-Writer Barrier (Trust Hold)

**Status:** Actual QML write-path guards are mounted in the Clock owner, but
the live gate is **immutable ACTIVE**. No installed authority, no pause
activation, no writer release, no background alarm ownership.

## What changes in the running program when reviewed and merged

The single mounted AlarmManagerService QML module remains the only writer
for Quickshell.dataDir/time-alarms-v2.json. It imports the pure
AlarmWriterBarrierPolicy.js, whose phase grammar is ACTIVE, QUIESCING,
RELEASED, and unknown. Only ACTIVE may save, tick, announce ringing or start
alarm audio. All other phases deny those operations by default. STOP always
retains a local emergency-silence path and explicitly refuses to claim a
durable STOP if persistence is barred.

The QML owner has one **read-only literal** alarmWriterBarrierPhase: ACTIVE.
There is no setter, external release token, IPC request listener or button
that can change it. A call to requestAlarmWriterPause returns an explicit
denial, including when a local status snapshot appears idle. This deliberate
restriction is the only safe posture before an independently authenticated
installed native Clock role and old-writer release bridge exist.

The barrier is now checked at the real execution surfaces:
- canEdit, saveDocument and beginWrite, with beginWrite checking again
  immediately before the only alarmFile.setText(...) call.
- maybeInitialize, covering V1 migration and initializing an absent V2.
- checkDue, including every 1-second timer, restart and delayed callbacks.
- restored-ring and freshly fired notification announcements.
- previewSound, syncSound and the asynchronous AlarmAudioV2 loader start.
- FileView.onSaved: if a future authorization error causes an unexpected
  phase switch while a queued edit exists, the queued edit is retained,
  storage becomes error, and the UI says NOT DURABLE. No queued write is
  silently converted into a successful saved alarm.

Clock create, duplicate, save, favorite, pause and delete paths already
converge on saveDocument; they now inherit the barrier. STOP and SNOOZE
converge there when storage can save, and their existing non-durable
local-silence fallbacks remain available otherwise.

## Security boundary

**A guard is not an authority.** The QML phase is non-switchable. Nothing
has actually paused or released the live FileView writer. In particular,
setting a QML property or receiving a signed synthetic response would not
prove that another Quickshell instance, service or timer stopped touching
the V2 alarm file.

This patch does NOT modify the source/permissions of the user's real
alarm file, nor schedule/play a second alarm. It does not install a systemd
unit, native bridge, signer, release root, migration service, sound player,
notification producer or new background process.

PR #1959 is a separate signed-origin observation; #1965 is synthetic
atomic migration; #1968 is passive drained status; #1973 is a signed
test-old-writer response. None is a native installed authorization grant
or real old-writer revocation. Their branches are intentionally not
edited here, and this code does not import them.

## Tests

Dedicated Node tests evaluate permitted/denied phases, refuse fabricated
authority fields and malformed readiness, and check QML source integration
at the direct FileView write, pending queue callback, timer, migration,
STOP/SNOOZE fallback, notification and audio loader.

Mounted Alarm Manager V2 and note-recovery tests, BG1-A, B1, B2A and B2B1
regressions rerun. GitHub also runs its other Clock QML-dependent workflows.
Passing tests here proves the source contracts and existing behavior, not a
native Quickshell pause or production takeover.

## Next implementation

1. Provision an approved Clock-only signing root and independent, protected
   source of installed program and session identity. Keep separated from
   the other Connections and Identity workers' release authority.
2. Add the **private authenticated** channel that can trigger QUIESCING;
   it must deny new edits/ticks, allow previously accepted FileView saves
   to finish, refuse if queued or migration data remains, and retain
   emergency local STOP. Record a durable post-flush V2 revision witness.
3. Only then permit RELEASED after an independently confirmed old-writer
   stop with a one-use signed receipt and crash/restart revocation. The old
   writer must never default back to ACTIVE while a protected new owner
   exists.
4. Migrate all mutations to one canonical owner, prove rollback and
   at-most-once delivery, and obtain explicit production approval before BG2.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock · Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC (live registration unverified)
ASSIGNMENT // BG1-B2B6 mounted write-path barriers, inactive until trust
SCOPE // Mounted AlarmManagerService, new pure policy, tests, CI and docs
HOW TO USE // Existing Clock unchanged: no pause UI or host actions
RECOVERY // Exact PR head and old source QML; revert branch/PR to discard
NEXT // Authenticated installed role + real writer quiescence/flush receipt
DECISIONS // No merge, live change, production release or background actuation
