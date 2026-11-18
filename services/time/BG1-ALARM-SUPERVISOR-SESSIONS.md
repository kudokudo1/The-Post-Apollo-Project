# Clock BG1-B2B11 // Native Supervisor Durable Session Epoch

**Phase:** Code + real Linux subprocess tests; production rights remain
denied. The supervisor is a real foreground native Unix socket listener,
but the session ledger is **explicitly synthetic-only** until an
independent protected Clock issuer, release-floor and installed authority
are approved and provisioned.

## GitHub integration correction

PR #2022 (B2B9) merged into `main`.
PR #2027 (B2B10) was marked **Merged**, but its base was the B2B9
*feature branch*, not `main`. Consequently, the native supervisor
file was missing from `main` even though its PR was closed.

The B2B11 review branch is based on the current `main`, reintroduces
the exact B2B10 supervisor source, original tests, docs and workflow,
and adds the B2B11 session extension. B2B10's scope CI was updated to
recognize this exact integration. **No production branch was changed**
and no previous PR was reopened or rewritten.

## What the computer actually does

A foreground native Python server accepts a single strict JSON frame on
`/run/user/<uid>/post-apollo-clock/clock-supervisor-v1.sock`. The
read-only `INSPECT_ORIGIN` action uses SO_PEERCRED, kernel
SO_PEERPIDFD and B2B9's independently signed Clock role to examine
the same running program and process.

In the isolated CI supervisor only, B2B11 now persists a single test
session in a private mode-0600 SQLite file under the test runtime
directory. Each row contains:
- actual kernel boot ID
- monotonic synthetic owner epoch, **matching the signed policy epoch**
- original PID and process start ticks
- pinned Clock release-root public-key fingerprint
- `SIGNED_PROCESS_OBSERVED` or `PIDFD_EXIT_OBSERVED`

Transactions use `BEGIN IMMEDIATE`, `synchronous=FULL` and journal
DELETE, so a competing second candidate cannot replace an active
session midway through an update.

On a valid original signed request, the server duplicates and
retains the **socket's original kernel pidfd**, rather than looking up
a PID later. A same-epoch repeated observation of that same process
may succeed. A different process, changed start ticks, or conflicting
signed epoch is refused while the old session remains active.

Only when that original retained pidfd signals process exit can the
supervisor durably mark `PIDFD_EXIT_OBSERVED`. After that, the retired
epoch remains denied even when the ledger is reopened; a different
signed process with a **strictly higher** epoch can be observed.
A restart without the original pidfd **does not infer exit** from
a PID number. It conservatively leaves the prior session active and
refuses replacements until an approved separate recovery mechanism
exists. A different boot ID also refuses implicit recovery.

These are observation permissions only, not writer permissions.

## Protected trust hold

The native supervisor's production mode still has **no protected
session enroller**, no installed signing-root grant and no CLI path to
add a roster entry. `add_synthetic_session` and
`observe_synthetic_session_exit` are limited to the explicit
disposable test runtime. The durable SQLite file is under a
test-user-owned directory and **must not be claimed as a privileged
production registry**.

B2B11's journal cannot prevent an unrelated old Quickshell process
from opening the V2 file or starting on reboot. It only denies
cooperative signed test admissions through the actual native
supervisor. Every returned result has:
`roleAuthenticated=false`, `writerStopped=false`,
`releaseAcknowledged=false`, `oldWriterRestartPrevented=false`,
`canTransferOwnership=false`, `canRing=false`,
`canNotify=false`.

The live `AlarmManagerService.qml` remains hard-coded
`alarmWriterBarrierPhase: "ACTIVE"`; its FileView continues to
own alarm saves. `FileView.blockWrites` is synchronous I/O, **not**
an exclusive ownership lock.

## Verify and recovery

CI starts an independently signed real Linux child and the real
AF_UNIX listener. It tests matching B2B9 role and B2B11 epoch,
pidfd-observed process exit, denied attempts while the old writer is
still enrolled, retired-epoch refusal after reopening the database,
positive observation (not actuation) at a new signed epoch after exit,
server-crash fail-closed restart, fake FDs, unsafe database modes,
a changed boot ID, competing sessions, malformed pins, and no
production permission escalation. B2B10/B2B9/B2B6/B2B1 regressions
run again.

Rollback of a **review branch** requires no host cleanup. The CI
ledger is disposable. No local files, user systemd services,
Quickshell processes, production alarms or background delivery were
changed by the PR.

## NEXT // Next implementation, not a user testing request

1. Operator-approved Clock-specific installed trust issuer, public
   root fingerprint, root-owned enrollment provenance, durable
   signed release floor and live session owner. Coordinate with
   independently owned Identity/Connections; their keys are not
   automatically Clock authorization.
2. Replace the **synthetic** enrollment boundary with a genuinely
   protected native supervisor that supervises the actual Quickshell
   process from start through exit, including restart/boot recovery.
3. Add a trusted private `QUIESCING` transition to the mounted QML
   old writer. Stop new edits/ticks without dropping accepted
   pending/queued saves; obtain durable final V2 source evidence
   after FileView writes flush. Preserve local emergency STOP/SNOOZE.
4. Then prove exactly one canonical writer, crash-safe rollback and
   BG2 audio and notification delivery on actual Silverblue hardware.
   Production activation requires operator approval.

## HOSPITAL checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
STAFF ROLE // External Hospital-compatible DOC, not live registered
ASSIGNMENT // B2B11 durable native test-session epoch and exit fencing
DEPENDENCY // B2B10 main integration, B2B9 already on main
SCOPE // Eight total Clock-owned files vs main, including four B2B10 files
PERMISSIONS // GitHub draft PR only, no host changes, merge or activation
DECISIONS // No production Clock role or ring capability ever granted
