# CLOCK // BG1-B2B2 Signed Role Origin Observation

**Status:** Signed process-origin verification prototype. **DENY-ONLY.**
No approved Clock release root, production signer custody, supervised
Clock application enrollment, live alarm writer or background ringing.

## Implementation mechanism

An Ed25519 release root signs a canonical Clock-only policy containing the
exact role, epoch/sequence, interpreter, entrypoint digest, command arguments
and UID/GID. The verifier requires that public root and minimum allowed
release floor to be independently pinned by an authorized installer or
protected issuer, not copied out of the client socket.

The verifier checks the signature using domain-separated bytes,
postapollo.clock.bg1-b2b2-signed-role-origin.experimental-v1, which cannot
be mistaken for Identity Center's release enrollment or C3e/C4b evidence.
It rejects unknown fields, duplicate JSON keys, malformed paths, incorrect
roles, wrong signatures and release downgrades.

For each inspection, the verifier binds this signed record to an independently
witnessed exact PID/start and an existing Linux SO_PEERPIDFD session. It
remeasures the running interpreter inode, exact proc cmdline, UID/GID, live
process lifetime and SHA-256 bytes of the exact expected Python entrypoint.
An invalid, replaced or symlinked entrypoint refuses. An installed production
candidate additionally requires a root-owned nonwritable path below
/usr/libexec/post-apollo/clock and root-owned strict-mode entrypoint.

In disposable test mode CI spawns an actual unprivileged Python process
and uses temporary, per-test Ed25519 keys. This exercises the mechanism but
does NOT create an approved release or install a trusted application.

## Important limits

A verified signature is evidence that a key signed specific bytes. It
does not establish that an external trusted authority enrolled the key, that
the running process's imported Python modules/memory are immutable, or that
the broker and Quickshell now share a canonical alarm writer. The expected
PID and start MUST come from a separate protected supervisor; copying them
from an untrusted socket request defeats independence.

The returned ClockRoleOriginObservation always states:
role_authenticated = false
can_write_alarm_file = false
can_ring = false
can_notify = false

No existing AlarmOwnershipBroker, AlarmManagerService, audio, Notifications,
Identity Center, C3e or C4b file is modified by this slice. The synthetic
broker's JSON role remains untrusted. No bridge is enabled. No production
key or signed package is provided.

## Tests

The tests launch a real connected AF_UNIX child, check its Linux peer pidfd,
and verify a separately generated signed test policy. They then reject
wrong signer, role, purpose, rollback, unexpected arguments, changed entrypoint,
symlink swap, forged witness, process exit and user-owned production path.
The older BG1-B2B1, BG1-B2A and BG1-B1 tests rerun in CI.

## Remaining BG1-B2B work

1. Obtain authorized Clock-specific release root and secure install evidence.
   Validate signed release floors against authority-owned durable history.
   Coordinate with Identity/Connections owners without changing their code.
2. Bind the signed role to an independent service supervisor and session
   identity. A signed entrypoint is not by itself an authorized writer.
3. Implement and verify exactly one durable alarm-document writer across
   Quickshell and background process, with protected migration, STOP/SNOOZE,
   owner-epoch fencing, crash recovery and rollback denial.
4. After those gates, prove independent sound and notification delivery
   with actual device/system-state acknowledgements before BG2 activation.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock · Background Alarm Ownership
STAFF // External Hospital-compatible DOC
ASSIGNMENT // BG1-B2B2 signed process-origin evidence, deny-only
CHECKPOINT // Source-only, tested CI fixture with no privileged release grant
NEXT // Authority-owned enrollment and single canonical writer
PERMISSIONS // No local host writes, production activation or merge
