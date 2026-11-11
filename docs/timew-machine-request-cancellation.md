# MACHINE // In-flight archive request cancellation and session-context drift

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE / protected Brave archive
STAFF // External Hospital-compatible DOC; no verified live Hospital attachment
ASSIGNMENT // Invalidate a bounded metadata request when its client/socket or Linux session context changes
SCOPE // Repository-only negative checks, synthetic tests; never a new listener or authorization

## IMPLEMENTATION

The previously merged MACHINE PR #1876 introduced a two-second kernel SO_PEERPIDFD process lease. This PR adds MachineBraveRequestCancellation.py and integrates it into the same disconnected, always-denied metadata ingress. No protected archive may be read over the socket.

The new guard is created *after* the socket's kernel peer pidfd is captured, but **before** consuming the exact one-request frame. It records the socket peer's Linux session ID (getsid), SHA-256 of kernel procfs cgroup membership, and inode/device IDs of the peer's PID/user namespaces. It does not trust a session name, seat, UID, path or other claim from request JSON.

After the framed request is consumed and again after its intent is bound, the guard rechecks:
- The short-lived process lease is still valid and the task hasn't exited or changed its recorded executable/credentials.
- The connected Unix socket has no FIN, half-close, POLLERR/POLLHUP/POLLRDHUP, or trailing second request. A nonblocking MSG_PEEK distinguishes no queued bytes from EOF and unexpected pipelined bytes without consuming data.
- Current Linux SID, cgroup contents and namespace IDs equal the initial snapshot.
- Its separate monotonic two-second limit has not passed, and time has not gone backwards.

Any negative observation invalidates the guard permanently. Failure to access kernel state or lack of Linux POLLRDHUP support fails closed. A guard is explicitly cancelled as the broker finishes; its lifetime is scoped to one socket request, not persisted to disk or a ledger.

**Important:** A matching Linux session ID/cgroup/namespace is not proof of an active, unlocked graphical logind session or a specific Brave extension. Other same-UID applications may share them, and a cgroup path is not a signed identity. This is cancellation and context-drift detection only. The C3e owner must provide separately verified process/seat/logind evidence and the C5 owner must provide purpose-bound one-use operator consent before any positive broker action.

There is no watcher, socket listener, systemd unit, native host registration, background timer, filesystem migration, browser tab action, permanent receipt, or RESTORE permission.

## HOW TO USE

No new Post-Apollo interface or desktop steps. The code is a source-only security boundary. GitHub CI runs:

    python3 -B -I tests/timew/test_machine_brave_request_cancellation.py

The synthetic test uses socketpairs and disposable subprocesses; it does not touch real browsing sessions or archive files.

## VERIFY

The new CI test demonstrates:
- An intact Unix socket after exactly one request remains eligible for *negative-check evaluation* (not for access).
- Peer EOF and half-close invalidate an in-flight request.
- A second pipelined request / unframed byte invalidates the request.
- A **real child process** uses setsid() to move to a different Linux session while remaining alive; its previously captured guard invalidates.
- Changed cgroup, PID/user namespaces, absent proc data, task lease invalidation, timeout/clock regression, and explicit cancellation never permit resumption.
- Source ingress checks the guard after parsing and binding, and always returns request_rejected.

The existing privileged CI fixture still runs synthetic browser/service processes under distinct Unix UIDs, proving the ordinary browser UID cannot directly open/list/write/chmod/unlink service-owned ciphertext. Existing encrypted archive and process lifecycle tests remain.

## WATCH OUT FOR

- Session context equality is **not user authorization** and does not detect the graphical desktop locking or changing active seats; those checks must come from a separately reviewed Connections/logind witness.
- The kernel can deny /proc or namespace access because of host policy. This results in refusal, not a fallback to reading a caller's environment variables.
- Kernel polling samples state at defined request boundaries, not continuously; a transient disconnect or context change outside those samples may be missed. The socket file descriptor is not a durable identity receipt.
- A process can be compromised without exiting, changing namespace/cgroup, or executing a different binary; C3e and C5 evidence are still required.
- The broker's metadata reader remains disconnected from all browser-facing ingress. There is no production installer and no authorization of permanent archive access.

## CHECKLIST

- [x] Reconcile merged #1876, Syntagma Hospital rules and existing MACHINE ownership.
- [x] Capture bounded Linux session-context snapshot before reading the first frame.
- [x] Reject EOF/half-close/pipelined input, expiry and changed Linux session context.
- [x] Preserve unconditional broker denial and explicit cleanup.
- [x] Synthetic subprocess, socket and tamper/cancellation tests.
- [ ] Verify latest GitHub CI and independent Nurse 2 review.
- [ ] Obtain genuine signed host/process/active-seat C3e witness and C5 one-use consent schemas from owners.
- [ ] Operator-reviewed protected runtime and archive migration.
- [ ] Authorized read-only metadata integration, encrypted import/dedup, and multi-monitor restoration.

## NEXT / DECISIONS

The next MACHINE implementation should add a separately reviewed, negative-only **external desktop-seat observation contract** once the Connections owner supplies the authoritative live-session interface. Do not forge a logind/seat witness or activate this code for real Brave. Keep changes repository-only and unmerged without explicit operator approval. No local user data, browser profile, desktop state or system services changed.
