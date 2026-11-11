# MACHINE // Kernel-anchored process lifecycle invalidation

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE / protected Brave archive metadata
STAFF ROLE // External Hospital-compatible DOC; no verified live Hospital session
ASSIGNMENT // Reject stale requesting-process evidence after process exit, changed executable, changed UID/GID/starttime or expiration
SCOPE // Linux negative-only process lease, existing deny-only broker ingress, CI regression. No installation, identity grants or restoration

## IMPLEMENTATION

The prior MACHINE [PR #1872](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1872) is merged. Its intent binding hashes the exact archive metadata request and kernel SO_PEERCRED PID/UID/GID. That was not enough to tell whether the process had exited or changed since a request began.

This milestone adds `services/time/MachineBraveProcessLease.py`, a short-lived negative-evidence check:

1. Read the accepted Unix socket's existing kernel `SO_PEERCRED` tuple, never a PID/UID from request JSON.
2. Obtain **SO_PEERPIDFD** from the same connected Unix socket (Linux UAPI constant 77). This kernel-created FD stays attached to that socket peer task, avoiding a post-hoc `os.pidfd_open(peer_pid)` lookup that might pin a *different* process after PID reuse. If unsupported or inaccessible, reject.
3. Before and after reading `/proc/PID`, poll that pidfd for exit. Compare the observed `/proc/PID/stat` starttime (field #22), all four UID and GID values from `/proc/PID/status`, and the device/inode of the running executable via `/proc/PID/exe`. Missing/inaccessible or inconsistent evidence refuses.
4. Hold the pidfd only for the bounded request, with a two-second monotonic expiry. A stale, exited, or changed-identity lease returns **false**. Close the descriptor on every normal and exceptional route.
5. In `MachineBraveProtectedMetadataContract.py`, capture the lease **before reading the request**, revalidate it and SO_PEERCRED after parsing and again after exact request-binding, then close it. **No metadata result can be returned.** The broker's response remains `request_rejected` for every client because valid signed C3e host evidence and purpose-bound one-use C5 consent are not available.

### What this does NOT prove

A pidfd proves the referenced task's lifecycle, **not** its signed release, trusted executable custody, login/session/seat, OS security label, or the origin of a Brave extension. `/proc/PID/exe` device/inode detects a change to a *different* executable, but re-exec of the same inode is not reliably detectable with this snapshot. `SO_PEERCRED` is socket-originated but can be stale regarding credentials changed later. The process could also be controlled or replaced by a hostile actor with sufficient privileges. All these observations are **negative checks only**.

Do not interpret a live lease as C3e admission. The current Connections C3e-Y signed witness is synthetic CI evidence; the independent C5 one-use human-consent issuer and replay custody remain unintegrated. Any positive broker admission requires separately reviewed owner-issued APIs, further process/seat checks and explicit operator authorization.

## HOW TO USE

There is no new TimeW control, native host, background process, installed service, archive migration, or browser permission in this milestone.

For repository developers, the relevant synthetic test is:

```bash
python3 -B -I tests/timew/test_machine_brave_process_lease.py
```

It launches only synthetic child processes and disposable Unix sockets under the CI account, then tears them down. The GitHub workflow also reruns the previous privileged **distinct UID** archive-bypass proof, request-binding negative tests and encryption regressions.

## VERIFY

Tests require actual Linux pidfd support. They verify:
- A live socket peer produces a valid temporary lease, including kernel PID/UID/GID, start ticks and executable identity.
- Process exit invalidates the lease, including after PID-fd remains open.
- `execve` changing the executable inode within the same PID invalidates the lease while the replacement process is still alive.
- Artificial changed starttime, executable identity, UID/GID, inaccessible `/proc`, negative/backwards time and elapsed TTL invalidate.
- Unsupported SO_PEERPIDFD and malformed kernel data fail closed, **no os.pidfd_open fallback**.
- Broker ingress checks live lease twice yet always returns refusal, and direct synthetic browser-UID access to a different service-owned 0700 archive is still denied by the kernel.

Passing CI is *not* live workstation verification or a production host-signed witness.

## WATCH OUT FOR

- Kernel SO_PEERPIDFD is Linux-specific and may not be exposed on older kernels; these machines fail closed. The code does not fall back to a weaker PID lookup.
- Accessing `/proc/PID/exe` can be denied by ptrace security, hidepid or sandbox policies even for a real client. Such failure is an explicit refusal, not permission to remove checks.
- Re-executing the same inode, injected/in-memory code and a privileged attacker may evade executable inode checks. None of these checks establish signed process identity.
- A lease must never be saved as a durable receipt or used to authorize future requests after its two-second lifetime. Its pidfd must be closed when the request ends.
- Source-only code is not a production listener or protected service installation. Do not move user-owned archives or register any live Brave native messaging host.
- Existing C3e/DOC and C5 workstreams retain their ownership. This implementation is a MACHINE-owned compatibility and invalidation seam only.

## CHECKLIST

- [x] Reconcile merged #1872 and unchanged C3e/C5 boundaries
- [x] Bind transient lifetime to SO_PEERPIDFD rather than PID-only lookup
- [x] Compare kernel task starttime, credentials and executable identity
- [x] Integrate negative lifecycle checks into deny-only ingress and close fd
- [x] Add true subprocess exit/exec, TTL, missing proc and unsupported-kernel tests
- [ ] Exact-head GitHub CI and independent Nurse 2 security review
- [ ] Independently measured signed host, process, seat and security label
- [ ] C5 purpose-bound one-use consent and replay-resistant receipt consumption
- [ ] Operator-approved protected service deployment and archive migration
- [ ] Trusted browser metadata and eventually restorable multi-monitor windows

## NEXT / DECISIONS

Next MACHINE implementation after this should bind an independently issued signed process/seat witness to this kernel lifecycle handle *only once the C3e owner supplies an approved interface*, and bind a C5 one-use receipt to the exact request after independent review. No positive access path is permitted in the interim. Keep the PR under operator review; no merge, production activation or local machine modifications performed.
