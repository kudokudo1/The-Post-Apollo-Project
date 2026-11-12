# CLOCK // BG1-B2B1 Kernel Peer Lifetime Fence

**Status: SYNTHETIC ONLY, DENY-ONLY. No production Clock enrollment, no live
single-writer handoff, no sound, no notifications, and no Quickshell connection.**

## The mechanism

The existing AlarmOwnershipBroker.py listens on a private Linux Unix socket.
A client that says "role":"quickshell" or "role":"background" in a JSON
hello message is *not authenticated as either application*. The original
SO_PEERCRED check proves the connecting process's PID/UID/GID, but a PID can
be recycled or its program replaced by execve during a live socket session.

AlarmPeerIdentity.py now obtains SO_PEERPIDFD directly from the **accepted
socket** (Linux UAPI option 77). This is a kernel-owned descriptor bound to
the actual connected peer process. It refuses on kernels lacking that feature:
there is **no fallback** to looking up a user-supplied PID or pidfd_open(pid)
after a potential reuse. The descriptor is close-on-exec and closed at session
teardown, including refused/disconnected clients.

Each request checks:

1. Kernel pidfd has not signaled exit.
2. Socket SO_PEERCRED still matches the captured PID, UID and GID.
3. /proc/<pid>/stat shows the same process start ticks, not a zombie.
4. /proc/<pid>/status shows unchanged real/effective/saved/filesystem
   UID/GID values matching the socket credentials.
5. /proc/<pid>/exe still identifies the initial executable and the
   expected **synthetic Python** executable.
6. Kernel pidfd is checked again after all userspace lookups.

Any mismatch refuses the request, even before attempting a synthetic lease,
shadow edit, STOP/SNOOZE simulation or reservation. There is no executable
identity or role claim contained inside client-controlled JSON beyond the
unchanged synthetic role name.

## What this does NOT authorize

The broker still has only --serve-synthetic, uses the test-only
bg1-synthetic.sock, and its responses state:

- mode: SYNTHETIC_BG1_B
- roleAuthenticated: false
- actuationEnabled: false
- ownsAlarmFile: false

**A kernel peer descriptor proves process continuity, not installation trust,
signed release identity, role authority, permission to ring or unique ownership
of the live alarm file.** A same-UID Python process can still claim either
synthetic role. That claim is never elevated into production.

The live AlarmManagerService.qml retains its own FileView writer.
AlarmBackgroundObserver.py remains read-only. The broker's synthetic atomic
shadow is not the live V2 store. No bridge, systemd activation or live-file
migration is included here.

## Evidence and test surface

tests/time/test_clock_bg1_b2b_peer_identity.py uses real Linux AF_UNIX
sockets and real subprocesses, including connected peer exit, same-PID
executable replacement, bad witness credentials, missing kernel pidfd and
descriptor closure. Existing B1 and B2A two-client IPC tests still verify
synthetic ownership and shadow atomics. The dedicated workflow compares its
entire branch file set against an explicit allowlist that excludes live QML,
audio, notification and observer paths.

This is a prerequisite security layer, **not** BG1-B2B completion.

## Remaining BG1-B2B work

1. Obtain and verify an authority-owned, signed release/installed service
   attestation for the specific Quickshell bridge and background program,
   plus matching expected executable/session binding. The present Python
   process/role is not that authority.
2. Introduce a **single canonical alarm-document writer** with an explicit
   transaction protocol for all UI edits, timer ticks, STOP/SNOOZE, save
   receipts and crash recovery. Migration must validate and preserve the
   current V2 file and refuse stale or concurrent uncoordinated writers.
3. Prove mutually enforced owner epochs and acknowledgement-backed takeover,
   including process loss, replay attempts, changed source revisions, and
   rollback refusal. The old Quickshell process must not keep writing during
   any new owner interval.
4. Only after native trust and single-writer tests pass may BG2 sound and
   notification delivery be considered; no process may infer permission to
   actuate from the BG1-B2B1 pidfd fence.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock · Reliable Background Alarms (BG1)
STAFF ROLE // External Hospital-compatible DOC
ASSIGNMENT // BG1-B2B1 kernel peer lifecycle proof, deny-only
NEXT // Verified signed process role and canonical writer transition protocol
AUTHORITY // No merge, install, Quickshell reload or production activation
