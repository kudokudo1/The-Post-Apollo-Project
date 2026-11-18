# Clock BG1-B2B15 // Mounted Accepted-Save Drain, Trust Hold

**STATE:** Source change in the actual mounted `AlarmManagerService.qml`,
with executable Node tests for its real FileView callbacks. **The old
Quickshell alarm writer remains live ACTIVE by default**, no signed native
pause bridge is installed, and none of the new private drain transitions
is reachable from the public AlarmManager API.

## IMPLEMENTATION

The mounted V2 alarm file is still owned exclusively by Quickshell's
`FileView` at `Quickshell.dataDir/time-alarms-v2.json`.
A save may have two stages:

1. `saveDocument(next)` accepts a new valid V2 document, updates the
   in-memory state and starts `beginWrite(next)` using FileView.
2. If a FileView save is already pending, a later accepted revision is
   coalesced into `queuedDocument`; the onSaved callback must finish
   that queued revision. The manager must never release the old writer
   in between these two completed callbacks.

B2B15 adds a **private local** `writerDrain` QtObject inside the
mounted singleton. It starts in ACTIVE and its entry method
`beginInternalSaveDrain` refuses unless the read-only
`nativeWriterDrainBridgeInstalled` property becomes true.
**It is hard-coded false.** The existing public
`requestAlarmWriterPause()` and `requestWriterRelease()` still
return their hard-denial status and have no route to the private method.

An eventual trusted bridge can request a local drain, but this PR
does not create that bridge or authorize its activation. Once an
independently approved native controller safely enters a local drain:

- The manager would **freeze new edit acceptance immediately**, and
  independently block new scheduler ticks, ring announcements, audio
  starts and preview. Existing local emergency STOP/SNOOZE silence
  remains available with an explicit unsaved warning.
- The original mounted `FileView` write may finish while its
  authority barrier remains ACTIVE. Only an already accepted queued
  document, from **the actual FileView onSaved callback**, may proceed
  through the sole `alarmFile.setText` call. A public direct
  `beginWrite` call is refused during the drain.
- Save generations distinguish an accepted latest document from the
  generation that FileView actually signaled saved. Coalesced identical
  content needs no redundant write but still gets a generation
  observation; a distinct queued revision must generate its own save.
- After storage becomes ready, the queue and pending stages are empty,
  no migration, ring, audio or notification remains in flight, and
  the observed generation matches the last accepted generation, the
  private local state may become **QUIESCING**. That phase blocks all
  new normal V2 saves. A FileView failure or refused queued write
  enters **FAILED**, never a release state.
- `AlarmWriterDrainPolicy.js` contains pure readiness and status
  logic. Its status deliberately reports
  `finalRevisionDurablyWitnessed=false`,
  `writerStopped=false`, `releaseAcknowledged=false`,
  `canTransferOwnership=false`, `canRing=false`.

There is **no native release receipt**. FileView onSaved is a Qt
callback, not independent `fsync` verification by a protected actor.
The revision/generation values prove only local callback ordering;
no sensitive alarm names, notes, file bytes or private keys are
returned by the status.

## SAFETY AND COMPATIBILITY

- B2B6's `readonly property string alarmWriterBarrierPhase: "ACTIVE"`
  remains unchanged, preserving the installation trust hold and all
  previously merged source expectations. `localWriterDrainPhase`
  separately reports the private, initially ACTIVE internal state.
- All new edit/scheduler/audio gates consider the private drain state
  as well as B2B6's installed barrier. No new public QML pause setter,
  Process handler, IPC listener or default-on service is introduced.
- No `FileView.blockWrites` ownership-lock illusion. This property
  remains `false` for asynchronous atomicWrites semantics.
- The existing STOP/SNOOZE unsaved local fallback and other Clock
  programs, Identity and Connections are not modified.
- Existing V2 files are neither read nor written by GitHub tests.
  No real hardware-level Quickshell execution or Silverblue boot test
  is claimed: CI executes the QML callback JavaScript in a bounded VM
  with synthetic model state and checks the mounted source contracts.

## VERIFY

The B2B15 CI suite runs pure readiness tests and the **actual extracted
onSaved callback body** with test-only FileView state. It proves
accepted A -> queued B -> B saved -> local QUIESCING; direct edit
refusal; identical coalescing; missing onSaved refusal; failed queued
write -> FAILED; and no durable release or ringing authority.
B2B4/B2B6 barrier tests and relevant V2 alarm, notes and ownership
regressions run again. The strict changed-file guard includes only
this Clock Room's QML/policy/tests/docs/workflows.

## NEXT // Engineering, not a user test request

1. Create a **private, independently authorized** native Clock-to-
   Quickshell channel. The current read-only bridge gate must stay
   false until the protected Clock issuer, per-session enrollment and
   signed CURRENT floor are installed and verified on Silverblue.
2. Bind the actual protected pause to a specific kernel process,
   release epoch and one-time challenge, not public QML flags.
   Test premature exit, concurrent control requests and replay.
3. Obtain a protected **final file-byte revision + durable fsync
   witness** after this local drain. Validate the expected V2 source
   and hold old writer restart prevention before RELEASED and a
   single canonical native writer takeover.
4. Implement BG2 true background alarm scheduling, audio and
   notifications with logout/suspend/reboot native acceptance.
   Operator decides activation after independent review.

## HOSPITAL CHECKPOINT

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
ROLE // External Hospital-compatible DOC; not live registered
ASSIGNMENT // BG1-B2B15 mounted QML accepted-save drain (trust hold)
SCOPE // QML/Clock JS, executable source checks, regression CI, docs
PERMISSIONS // Draft GitHub PR only. No host modification, merge or activation
RECOVERY // PR and exact-head workflow logs, no installed rollback required
DECISIONS // Local drain is dormant; native release, ringing and owner
             transfer remain hard-denied
