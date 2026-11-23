# 🏥💜 DOC 1 // Identity-purpose packet origin is not protected Sign-In authority

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF:** DOC 1, external Hospital-compatible. Live Hospital registration unverified  
**IMPLEMENTATION:** Test-only, non-activating GitHub CI  
**PRODUCTION SIGN-IN:** HOLD

## IMPLEMENTATION

A Linux Unix-domain `SOCK_STREAM` connection can expose `SO_PEERCRED`, which identifies the process associated with **connecting** the socket. Merged [DOC 1 #2355](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2355) demonstrated that a different forked process can later send bytes over the inherited connected descriptor, so connector PID/UID is not sufficient per-message sender attribution.

The existing, independently reviewed, **dormant** `services/connections/ConnectionsTimeWNativePacketObservation.py` already implements the harder kernel primitive for TimeW: `SOCK_SEQPACKET` framing, `SO_PASSCRED`/`SCM_CREDENTIALS` for the exact packet, `SO_PEERPIDFD` for original peer-process lifetime, bounded reads, unexpected `SCM_RIGHTS` descriptor cleanup, and fail-closed inherited-sender refusal. It returns untrusted observational facts, not native selection or consent.

This DOC 1 milestone **reuses that existing kernel observer unchanged** alongside the original `C3eLocalReadOnlyIpcProbe`, also unchanged. A new test-only Identity-purpose composition:

1. Requires disposable GitHub-hosted root CI and exactly one bounded, canonical length-prefixed expected **read-only** C3e frame, with duplicate JSON keys and non-finite values refused.
2. Consumes one actual kernel-attributed Unix `SOCK_SEQPACKET` message using the existing observer. The expected frame is caller-supplied; its SHA-256 must match the observed packet's digest and length. This is only a **local consistency check**, not a protected signed request or enrollment.
3. Strictly validates the existing observer's full false-authority field set, kernel flags and exact status, then invokes the existing C3e read-only `SNAPSHOT`, `OUTCOME` or `CUSTODIAN_STATUS` route using the matched **local test expectation**.
4. Returns the original local diagnostic status and kernel-observed PID **without** any protected root, host, signing key, current history, C5 consent, terminal receipt, retry or Sign-In authority. The protected mode still refuses local fallback.

No raw message or trusted authorization is returned. No application, service, protocol, socket listener, root enrollment, production writer or native command path is installed.

## HOW TO USE

No workstation or NAS action. The entire test is disposable Linux CI, using the existing local signed test fixture and one socket pair per test. Four **additive DOC 1 files** only:

- `tests/connections/c3e_release_trust/C3eIdentityPacketOriginNonAdmissionCI.py`
- `tests/connections/test_connections_c3e_identity_packet_origin_nonadmission.py`
- `.github/workflows/connections-c3e-identity-packet-origin-nonadmission-ci.yml`
- This document.

DOC 5/TimeW-owned semantics are **not changed**. The reused observer is a low-level kernel provenance diagnostic; it does not certify the Identity gateway, native SwayPX sender, installed release or selected seat. In particular, the SHA supplied by a local caller and an observed real peer are **not** a signed, independently pinned identity-purpose request.

## VERIFY

22 new real Linux and adversarial cases cover local and protected read-only diagnostics, issued and consumed challenges, protected no-local-fallback, prohibited Sign-In/history writes, extra authority fields, wrong challenge, wrong raw bytes despite a valid expected frame, cross-purpose TimeW bytes, malformed length prefix, duplicate JSON operation, inherited FD sender, stream versus packet transport, missing `SO_PASSCRED`, missing kernel pidfd, unexpected `SCM_RIGHTS` descriptors, forged observer or router success, unknown report fields and unconditional production refusal.

The dedicated workflow also reruns **188 inherited cases**, as counted from the existing suites: 11 native kernel observer, 32 C3e custodian cutover, 30 IPC non-settlement, 24 accepted Unix socket, 46 original read-only IPC, 28 storage-boundary and 17 real SIGKILL. Standard Grammar, root-pinned admission and Fedora fake-signed RPM/SELinux regression workflows remain separate exact-head gates.

## WATCH OUT FOR

- Even **per-packet kernel process attribution** is not an independently enrolled signing root, authentic release/seat or verified command authorization. Kernel identity can establish which local process sent bytes under certain conditions; an approved credential operation additionally needs a cryptographically authenticated audience, root, durable one-use challenge, current history and protected transaction settlement.
- Reusing a native kernel observer from TimeW does **not transfer TimeW C5** or other product permissions to Identity. The output grants nothing.
- A digest match against a **caller-provided expected frame** must never be interpreted as a trusted signature or independent command. This fixture deliberately does not design a production message wire format.
- An unavailable pidfd, incomplete/forged packet, inherited sender or unexpected FD transfer fails closed. No automatic retry of unknown protected state.
- Local SQLite can be restored and forked as shown in reviewed #2334 and #2348; this code cannot repair the independent custody problem.
- No local workstation modification, NAS provisioning, signing-key enrollment, official service installation, PR merge or Sign-In activation is authorized by this source-only experiment.

## CHECKLIST / NEXT

- [x] Reconcile #2334, #2348, #2355 and DOC 6 #2353 merged and independently scoped-reviewed on GitHub.
- [x] Add bounded Identity-purpose kernel packet/readonly diagnostic negative integration using existing code.
- [ ] Exact-head dedicated, Grammar, root release and Fedora CI.
- [ ] Independent Nurse 2 source/CI review and operator merge disposition.
- [ ] Future protected enrollment, authenticated gateway source and independently current head/receipt/custodian recovery.

## DECISIONS

The operator's accepted direction remains **local development now, separately administered independent protected hardware later**. No trust anchor or production permission is inferred from an experiment on a disposable local Linux process. **PRODUCTION SIGN-IN HOLD.**
