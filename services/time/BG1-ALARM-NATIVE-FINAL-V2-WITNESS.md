# Clock BG1-B2B16 // Native Final V2 Synced-Source Witness

**STATE:** Source implemented and tested in a real Linux native AF_UNIX
supervisor, with purpose-separated signed Clock-origin verification.
**ACTIVATION:** NO. The installed signing issuer, native supervisor
release-floor pin, final source-file pin and actual trusted Quickshell
control channel are **not provisioned**.

## IMPLEMENTATION // What the computer actually does

B2B15 installed a dormant mounted QML FileView local save-drain
mechanism that can track accepted generations and callbacks.
A FileView onSaved callback is **not** a proof that final V2 source
bytes are synced to stable storage, still less a proof that the
old writer has exited.

B2B16 adds `AlarmFinalV2SourceWitness.py` and a new
`INSPECT_FINAL_V2` action to the **existing real native Clock
AF_UNIX supervisor** (not a separate stand-alone untrusted fixture).

### Signed process before file access

The supervisor first verifies the accepted socket's actual
SO_PEERCRED/SO_PEERPIDFD process against the independently signed
Clock installed-role policy (B2B9) and synthetic active-session
ledger (B2B11); installed mode also requires the B2B12 signed
session and B2B14 current floor. Unknown, changed or retired
processes refuse before the source is inspected.

No socket request may set a source pathname, digest, UID, owner
epoch, access mode or permission. The frame still contains **only**
the canonical version and action. Test-only
`pin_synthetic_final_v2()` pins a mode-0600 disposable V2 source
and digest outside the socket, and cannot enroll production.
In installed mode, the separately protected expected source path,
source SHA-256 and owner UID are all intentionally unprovisioned
`None`. A signed client without this independent source pin
cannot request a native file witness.

### Exact source bytes and actual Linux synchronization

The verifier:
- Opens every source parent directory from `/` via dirfd and
  `O_DIRECTORY|O_NOFOLLOW`; rejects symlink components or
  untrusted writable ancestors. Disposable CI permits only a
  root-owned sticky `/tmp` traversal followed by private 0700
  test directories; production has no such exception.
- Opens **only** the exact `time-alarms-v2.json` basename with
  `O_NOFOLLOW|O_CLOEXEC`; checks regular file, one hard link,
  expected owner UID, non-group/world-writable mode and a 2 MiB cap.
- Reads the raw bytes, validates a minimal V2 JSON structure
  (`version=2`, positive `nextId`, a bounded alarm array with
  nonduplicate positive IDs), then compares SHA-256 against
  the **independently configured** expected digest. Full alarm
  semantic validation still belongs to `AlarmManagerPolicy.js`.
- Executes real Linux `fsync()` on the opened **read-only file
  descriptor** and containing directory descriptor. It then
  rereads the exact bytes and compares file descriptor metadata
  against the path's current inode. Errors, a changed digest,
  inode replacement, content modification, symlinks, bad
  permissions or unsafe directories refuse.
- In synthetic mode, the supervisor checks the original held
  kernel pidfd **before and after** the sync observation.
- Replies with no V2 alarm data, path, notes, source digest or
  private signing material. Success means only
  `originObserved=true`, `finalV2RevisionObserved=true`,
  `fileSyncObserved=true` and
  `parentDirectorySyncObserved=true`, with `ok=false`.

**Every result still has**
`sourceExclusive=false`,
`finalRevisionDurablyLocked=false`,
`oldWriterRestartPrevented=false`,
`writerStopped=false`, `releaseAcknowledged=false`,
`ownsRealAlarmFile=false`, `canTransferOwnership=false`,
`canRing=false` and `canNotify=false`.

### What this does NOT establish

An fsynced read-only snapshot **does not prevent an additional
FileView write** immediately after the check, prevent a new
Quickshell process, establish an exclusive file lease, or make
the native process the new owner. It also does not guarantee the
physical storage firmware truly made writes power-loss-proof.
No ownership transfer can use this observation alone.

B2B16 does **not** create an authenticated Clock-to-QML
`QUIESCING` channel. That requires separately approved installed
Clock issuer custody, a live signed one-use process-bound pause,
and protected old-writer exit/restart fencing. The live QML
`alarmWriterBarrierPhase` remains immutable ACTIVE and
`nativeWriterDrainBridgeInstalled` remains false.

## VERIFY

CI launches a real Linux child over the actual supervisor
AF_UNIX socket with separately signed test-only Clock installed-role
policy, and a real disposable on-disk V2 source. It checks a
successful read-only file+dir fsync witness, tampered source bytes,
missing file, symlink and hardlink, unsafe modes and ancestor
paths, forged request fields and wrong process signing pins,
overlarge or invalid V2 source, atomic inode replacement
**during fsync**, and in-place mutation during fsync.
The tests assert that the response never leaks alarm contents
and never grants writer, release or ring permission.

Existing B2B9-B2B15 native/QML/AlarmManager contracts are
rechecked. Only ten Clock-owned review files, including historical
exact-allowlist CI guards, may change. No user machine files or
alarms are read or edited by this GitHub CI.

## NEXT // Actual integration, not an operator test request

1. Design and independently review a *trusted* native
   Clock-to-Quickshell pause channel: protected Clock issuer,
   B2B12 session + B2B14 current floor, one-use signed challenge,
   kernel PID/start ticks and old-writer process handle, plus
   a local QML control path that **cannot be called by other
   widgets or untrusted same-user programs**.
2. Exercise B2B15 private local drain against a real mounted
   Quickshell process on disposable V2 data. Bind a final exact
   source digest and actual native fsync observation to that
   process's terminal receipt, then **stop/fence** the old process
   and prevent its restart before any canonical owner migration.
3. Independently install and accept the Clock-specific native
   service, signing key custody and protected release floor on
   Fedora Silverblue with operator authorization.
4. Establish one owner, crash-safe rollback/recovery, and
   BG2 independent scheduler+audio+notification under system
   restart/logout/suspend conditions. Operator separately
   accepts production activation.

## HOSPITAL CHECKPOINT

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, not live registered
ASSIGNMENT // BG1-B2B16 native exact final V2 synced-source observation
SCOPE // Ten Clock-only source/CI/tests/docs files, no installed changes
PERMISSIONS // GitHub draft only; no merge/host/install/release/ring
RECOVERY // PR head + CI; no live rollback needed
DECISION // Source sync is evidence only, NEVER ownership authority
