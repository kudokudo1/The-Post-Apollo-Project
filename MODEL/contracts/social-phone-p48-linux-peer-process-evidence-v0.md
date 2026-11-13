# Social PHONE P48 // Linux pidfd-backed peer-process evidence, status only

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff role:** External Hospital-compatible PHONE DOC. Live Room/Assignment/Session unverified.  
**Continuity:** P45 #1957, P46 #1960, P47 #1963 all **OPEN DRAFT** and unmerged at this checkpoint; P48 branch is stacked on P47 **but PR must target `main`** to avoid the P44 false-mainline-merge problem. Each earlier PR needs independent review, merge, and post-merge file verification. The owning C4b/Identity #1785 is still OPEN, and PHONE issue #1885 remains BLOCKED pending real upstream C3e/C5.

## IMPLEMENTATION

This package adds an *actual Linux operating-system process measurement* to the P47 real Unix-socket ingress rather than inventing signed credentials:

1. `services/phone/PhonePersonalPeerEvidenceP48.py` reads a real connection's kernel `SO_PEERCRED`, checks UID/GID equal to the running service, and pins the peer PID via `pidfd_open`. It reads bounded real `/proc/<pid>/stat`, `status`, `cgroup`, optional `attr/current` (LSM), and opens/hashes the real `/proc/<pid>/exe` file bytes. The result contains private process start time, executable SHA-256 and inode/device, cgroup digest and whether a Linux security label was observable. It re-reads PID starttime, cgroup and executable inode before returning and refuses exited/replaced processes, changed credentials, missing pidfd support, malformed/unreadable fields, out-of-bound executable data or UID/GID changes. No provider identity, profile, note, secret, host release root or raw process evidence goes to the QML UI. Repr is content-free.

2. The real `PhonePersonalHostSocketP47.py` now requires **both** an exact bounded STATUS request and P48's successful kernel-/proc-backed peer observation before sending its existing `HOST_UNTRUSTED_STATUS_ONLY` response. A denied/missing/changed process receives the identical content-free DENIED response. The public P47 schema and disabled status flags remain unchanged. Its socket still provides **zero SAVE/KEY/CONSENT actions**, no signer, no vault import or metadata writes.

3. Tests run actual Linux `AF_UNIX` peers, compare executable SHA-256 with the real current interpreter, verify genuine PID/start/UID/GID/cgroup presence, and inject hostile PIDFD unavailability, credential mismatch, PID reuse, executable inode switch, cgroup switch, unreadable proc, malformed proc, and P47 integration refusal. P47 native socket and P45/P44 UI/mainline regression tests run in dedicated CI.

## HOW TO USE

There is no local Fedora deployment, keyring operation, user note, iPhone call or installed systemd service. This is a GitHub review branch only. Its Linux test uses the ephemeral GitHub runner's real kernel and temporary Unix sockets.

## VERIFY

Check exact P48 PR-head dedicated Linux workflow, P47 native socket tests and existing locked PHONE editor/mainline completeness checks. Real `pidfd_open` + remeasurement proves process-replacement detection on the disposable CI runner, not authenticity of an installed software release. Native Quickshell and installed Silverblue service/SELinux/seat verification remain pending.

## WATCH OUT FOR

**Crucial:** P48 observes the **socket peer (client)**, not the service process, and `SO_PEERCRED` plus `pidfd` only establish a consistent Linux process observation. A same-UID malicious client can satisfy all these checks, and a Python interpreter executable SHA-256 does **not** authenticate its running Python scripts or imported modules. The optional LSM string is only observed, not verified against a signed installed SELinux policy or a trusted seat. Never convert a successful P48 observation into a host grant or key release.

The actual C4b/Identity installer must deliver independently signed installed **service** identity and process/module hashes, immutable release/public-key enrollment, seat/session/SELinux/unit/cgroup provenance and full two-boot rollback evidence. C3e must supply independent one-use challenge/consumed/revoked receipt with rollback-resistant floor. C5 must supply genuine signed PHONE per-action consent bound to P41b exact `editHmac` and human SAVE/cancel choice. The PHONE host itself must own key collection/provision/unlock/rotation/erase and durable transaction lease across P35 encrypted CAS/commit/readback. P37/P39 synthetic signed receipts remain non-authorizing. Avoid extending P47's STATUS socket to SAVE with a one-line check.

## CHECKLIST

- [x] Reconfirm mainline and open P45/P46/P47 ownership, C4b and #1885 status.
- [x] Real Linux pidfd-based peer observation and process-replacement refusal.
- [x] Integrate P48 into P47 exact STATUS ingress without changing public authority flags.
- [x] Native Linux peer snapshot/race/denial tests and dedicated workflow.
- [ ] Verify exact PR-head CI and independent review.
- [ ] Review/merge P45, P46, P47 and then P48 **to main**, rechecking all files.
- [ ] Independent C4b/Identity installed service evidence and C3e/C5 producer contracts.
- [ ] Real authenticated protected PHONE host lease, safe key lifecycle and trusted saved readback.
- [ ] Native Fedora/Quickshell installed acceptance and separate operator activation.

## NEXT

Complete a separately owned **installed server identity verification** against genuine C4b release/proc/module/SELinux/seat evidence, then enroll the C3e external one-use issuer and C5 true PHONE human-consent producer. Once those are verified, implement the host-controlled protected key lease for P35, trigger one action per approval, read back authenticated ciphertext and finally enable the Social menu SAVE. P48's peer process observation is a prerequisite building block, not that final trusted host.

## DECISIONS

No external-owner code changes, merges, machine modifications, socket activation on user's Fedora, production keyring use, real notes or iPhone write. Operator retains final authority and acceptance.
