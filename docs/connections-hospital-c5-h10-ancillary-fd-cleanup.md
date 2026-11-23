# 🏥💜 DOC 4 // C5-H10 native issuer ancillary descriptor cleanup

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Hospital C5 protected native issuer  
**STAFF ROLE //** DOC 4, external Hospital-compatible (live registration not verified)  
**ASSIGNMENT //** Hardening of C5-owned Linux native issuer socket input
against ancillary file-descriptor leaks, while its human-consent signing
HOLD remains unconditional  
**PRODUCTION //** HOLD

## IMPLEMENTATION

**Concrete issue fixed.** A connected Linux Unix socket can carry
`SCM_CREDENTIALS` and also `SCM_RIGHTS` control records. After
`recvmsg()`, the kernel has already created new file descriptors
in the receiving process for any delivered `SCM_RIGHTS`. Before this
patch the C5 issuer's `_packet_recv` checked credentials and packet
bounds but did **not** close these unexpected received descriptors.
An attacker able to reach the native IPC socket could submit rejected
packets that leave descriptors open in a long-running privileged issuer,
potentially exhausting its descriptor table.

C5-H10 updates **only the existing DOC 4-owned**
`services/connections/hospital/HospitalNativeIssuerService.py` runtime
source:
- Receiver requires Linux `MSG_CMSG_CLOEXEC`, then calls `recvmsg`
  with that flag and bounded ancillary space for credentials plus
  possible unexpected rights.
- New `_discard_unexpected_native_rights` walks **every** delivered
  `SCM_RIGHTS` cmsg, closes each complete received fd, flags malformed
  trailing bytes, negative fds or failed closes and **refuses** the packet.
- Disposal runs **before** any decision about `MSG_TRUNC`,
  `MSG_CTRUNC`, sender credentials, payload bounds or foreign
  ancillary controls. The kernel itself disposes descriptors it could
  not deliver because of ancillary truncation.
- Rejects unknown ancillary controls and requires exactly one valid
  `SCM_CREDENTIALS` record matching the pinned original sender.
  Valid single-credential native packets remain accepted.
- **No new authorization path:** C5-H4's
  `_require_independent_room_consent` still denies before
  `load_installed_key`, `sign_px_grant` and PX COMMIT. No key,
  agent, socket installation, human display, external custodian or
  protected PX writer is provisioned.

## HOW TO USE

Run the isolated H10 GitHub Actions job on the draft pull request. The
test uses ordinary unprivileged disposable Linux `SOCK_SEQPACKET`
socketpairs and `/dev/null` descriptors. It compares local
`/proc/self/fd` before and after rejection, ensuring imported
`SCM_RIGHTS` descriptors were not left open. No access to a real
Hospital Room, PX database, host native service or operator session is
needed.

There is no UI or workstation action to take, and H10 must not be
installed by bypassing the required operator/native approval process.

## VERIFY

New adversarial checks:
- Real normal same-process credential-only packet remains accepted.
- Real one, several, wrong-expected-peer, oversized-data and
  ancillary-truncated `SCM_RIGHTS` packets are all refused without
  leaking imported descriptors; the sender's pre-existing fd is intact.
- Multiple fake delivered rights controls are all closed.
- Malformed trailing rights data, unknown/negative fd and failed close
  cannot prevent cleanup of other delivered valid fds.
- Even `MSG_CTRUNC` or `MSG_TRUNC` with delivered rights cannot skip
  cleanup.
- Missing, malformed, duplicated or unexpected ancillary credentials,
  and a sender address on the connected socket path, are refused.
- `MSG_CMSG_CLOEXEC` and `SO_PASSCRED` are required at the receive
  boundary; the current native signing HOLD remains intact.
- Inherited C5-H4, C5-H7 and H6 Polkit context regressions must PASS.
  All CI numbers are targets until raw exact-head logs confirm them.

## WATCH OUT FOR

This is a **source-level security hardening**, not native-host security
acceptance. It does not independently verify installed systemd socket
activation, source SELinux confinement, live release provenance,
operator-authenticated display, independently protected C5 SPENT,
safe PX one-use original request, rollback-resistant history or
all legacy writer cutover. PX #130/#133 remain separate owner drafts.

Even with perfect packet origin and descriptor cleanup, the received
bytes can be untrusted. No network or authorized user action is
created, and no protected signing capability becomes available.
Reviewers should pay particular attention to real Linux ancillary
truncation behavior, multiple cmsg disposal and the unchanged hard
consent refusal ordering.

## CHECKLIST

- [x] Read Syntagma/Hospital and current app/PX ownership
- [x] Identify actual existing C5 native receiver fd-cleanup gap
- [x] Add bounded runtime cleanup before all packet refusal paths
- [x] Add targeted real Linux SCM_RIGHTS and malformed ancillary tests
- [ ] Exact-head native CI plus inherited regression PASS
- [ ] Independent Nurse 2 **pre-merge** source/security review
- [ ] Separate operator merge disposition
- [ ] Owner acceptance for C5-H8 S0/R0/H0/C0/W0/T0
- [ ] Operator native-host and production acceptance

## NEXT

After exact-head CI, request Nurse 2 to independently inspect the
existing native receiver diff and raw Linux fd-leak tests. If scoped
PASS, await operator authorization before merge. The separate C5-H8
real trusted human-consent producer/custody contract stays blocked until
DOC 1/DOC 2, native display and PX owners explicitly accept it.

## DECISIONS

**This PR is a bounded DOC 4-owned native input hardening only.**
No PX, C3e/C4b, Quickshell, SwayPX or Hospital DB owner files changed.
No signer policy, key, active socket, running service, local workstation,
real Room, merge or production activation performed.

**HOSPITAL C5 PRODUCTION HOLD.**
