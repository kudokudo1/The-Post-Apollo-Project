# CLOCK // BG1-B2B4 Default-Deny Writer Quiescence Preflight

**State:** Read-only preflight in mounted AlarmManagerService, synthetic-only
future barrier model. **No authenticated release, no handoff, no alarms moved.**

## What actually changed

The current AlarmManagerService singleton is still the sole live writer of
Quickshell.dataDir/time-alarms-v2.json. It retains its original Save, delayed
queued-write, V1 migration, STOP/SNOOZE, checkDue, notification, sound and
FileView lifecycle. There is no bridge to the synthetic broker.

The new AlarmWriterQuiescencePolicy.js examines a **bounded status snapshot**
containing only storage phase, queued/pending write flags, V1 migration
flag, ringing count, preview activity, audio state and notification delivery
state. It never accepts raw alarm notes, names, sound paths, user content,
or a caller-supplied credential as proof of ownership.

A locally drained snapshot requires:
- storageState is ready (not loading, empty, error or saving);
- no pending FileView write or queued write;
- no V1 migration request;
- zero ringing occurrences;
- no sound preview and audioState IDLE;
- no outstanding notification delivery.

Only then the status is LOCAL_WRITE_QUEUE_DRAINED_ONLY. This is a limited
**instantaneous local observation**. It does not prove the saved JSON was
flushed and authenticated, that callbacks cannot enqueue a later save, that
another Quickshell singleton stopped, or that a different process acquired
exclusive control.

The live QML singleton now exposes:
- writerQuiescenceStatus: pure read-only readiness summary;
- writerReleaseAcknowledged: hardcoded false;
- writerReleaseActivated: hardcoded false;
- requestWriterRelease(): returns a stable **refusal only**, with reason
  NO_TRUSTED_WRITER_RELEASE_BRIDGE when locally drained.

Requesting release does **not** change storageState, canEdit, pendingDocument,
queuedDocument, FileView, checkDue, audio, notification, or UI state.
A fictional signedOwner:true flag in an input cannot promote this observation.
The current QML write path remains functionally unchanged.

## Why no actual PAUSE or RELEASE yet

BG1-B2B2 signed role observation is still separately under review in PR #1959.
Its success flags are read-only, not installed role authority. BG1-B2B3's
candidate migration PR #1965 is fixture-only; its synthetic release HMAC
does not stop the actual Quickshell writer.

Introducing a public QML pause or allowing background authority from a
boolean would let any same-process UI module disable alarms. An unsigned
local status flag cannot prove a secure release and must not act as the
authority gate. Therefore this milestone deliberately **does not freeze
live writes** until a trusted native control channel and authenticated
installed counterpart can be verified.

## Next implementation (not tests)

1. Establish a Clock-specific independently enrolled native bridge with
   actual process/release identity and supervised session ownership;
   coordinate with Connections/Identity owners without reusing their
   signing keys or modifying their assignments.
2. Integrate a *verified* old-writer PAUSING state which prevents new UI,
   timer, queued callback and migration writes only after all existing
   FileView saves are durably acknowledged; retain a separate local
   emergency STOP/silence behavior without claiming a durable STOP.
3. Require a signed, one-use challenge and a durable original V2 hash +
   revision witness before releasing to the new canonical writer. Fence
   all old writer paths after takeover and prove crash/restart rollback.
4. Keep BG2 ringing disabled until a protected single-writer cutover,
   delivery acknowledgements and operator-approved installation.

## Tests and limits

The dedicated Node test covers every disqualifying local status,
malformed and forged role flags, privacy-free replies, all transition
barriers (ACTIVE/QUIESCING/RELEASED), and the unchanged live QML
saveDocument, onSaved queued write, STOP fallback, tick and FileView paths.
Existing Clock alarm, note recovery, B1, B2A and B2B1 security tests rerun.

**This is BG1-B2B4 local preflight, NOT completed BG1-B2B.**

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock · Background Alarm Writer Release
STAFF // External Hospital-compatible DOC, not live registered
ASSIGNMENT // BG1-B2B4 read-only default-deny writer-release preflight
SCOPE // Five files: pure policy, mounted QML diagnostics, test, CI, docs
NEXT // Verified native Clock release handshake and real write-gate cutover
RECOVERY // PR branch and tests; no persisted or host-side state changed
DECISIONS // No merge, host install, production activation, background ringing
