# 🏥💜 DOC 1 // Real accepted Unix socket, diagnostic-only C3e process boundary

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF:** DOC 1, external Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT:** Exercise actual Linux pathname AF_UNIX accept + per-connection `SO_PEERCRED`, without turning a kernel process observation into a trusted host credential  
**MODE:** Disposable GitHub-hosted local development only  
**PRODUCTION:** Sign-In HOLD

## IMPLEMENTATION

At the mechanism level, two programs communicate through a Unix socket. The Linux kernel can report the PID, UID and GID associated with a connecting process through `SO_PEERCRED`. This is more meaningful for a **freshly accepted connection** than for an inherited `socketpair()`, where the credential snapshot can describe the task that originally created the socket, not the child that later sends bytes.

The merged C3e [#2248](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2248) already demonstrated that identity distinction using kernel credentials. The merged [#2258](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2258) hardened the original disposable **read-only** IPC request/response shape. This milestone combines those *original existing* components on an actual disposable pathname socket without editing either source:

1. Under a new root-owned `/run/c3es-ci-*` directory (mode `0700`), create **exactly one** `AF_UNIX/SOCK_STREAM` listener `read-only-ci.sock` (mode `0600`). Reject existing/symlink/regular socket-path collisions and unsafe directory owners/modes.
2. Fork a connecting client process and a one-request server process on disposable GitHub CI. The CI harness supplies the **expected connector PID**. The server calls `accept()` and obtains `SO_PEERCRED` on the newly accepted socket. A mismatched connector PID/UID receives a fixed refusal **without request parsing**.
3. If that kernel observation matches the test expectation, reuse unchanged `C3eLocalReadOnlyIpcProbe.serve_one_ci_only`. It supports only `SNAPSHOT`, `OUTCOME` or `CUSTODIAN_STATUS`, and returns exact deny-only diagnostic or fixed refusal fields. No challenge issuance, history write, enrollment, credential command, Sign-In, or local fallback in protected mode.
4. Close the listening socket after one accepted connection and unlink only the original socket inode. No persistent service, systemd unit, NAS endpoint, remote network listener or installed runtime is created.

**Important limitation deliberately tested:** A client can connect as root, then **fork a different process** that inherits the connected socket descriptor and actually writes the request. The server's `SO_PEERCRED` remains associated with the original **connecting** process. Thus, even an exact kernel PID/UID match does **not** prove the identity of the specific process currently writing the bytes, and cannot replace role/key enrollment, authenticated message source or actual selected Linux seat.

The directory/socket modes deny an unprivileged client access before it could submit a request, but filesystem permissions do not authenticate the real installed Silverblue gateway or establish independent protected history. All new proof/credential/host/current-head/terminal/automatic-retry flags remain **FALSE**, including after a valid read-only snapshot.

## HOW TO USE

There are no user workstation, NAS or service commands. Tests run only on disposable root-owned GitHub-hosted Linux runners. This is not a local production service.

Exactly four new DOC 1-owned files:

- `tests/connections/c3e_release_trust/C3eAcceptedUnixReadOnlyPeerCI.py`
- `tests/connections/test_connections_c3e_accepted_unix_readonly_peer.py`
- `.github/workflows/connections-c3e-accepted-unix-readonly-peer-ci.yml`
- This document

No existing DOC 1 original ledger, C3e trust boundary, DOC 2 C4b gateway/process/install, DOC 5 C5 consent, DOC 6 Identity commands, SwayPX, TimeW, Hospital or Forest files are modified.

## VERIFY

The **24-case** real-process suite covers local snapshot, protected status, protected-mode no SQLite fallback, issued/consumed local challenge, mismatched connector PID refusal before parsing, prohibited Sign-In/history commands, forged grant, duplicate JSON operation, truncated frame + half-close, unknown challenge, one-shot socket cleanup, symlink/regular collision refusal, unsafe directory/root, actual nonroot access refusal, **connector-versus-inherited-FD sender PID mismatch**, strict non-authorizing observation, extra receipt/positive authority rejection and unconditional production refusal.

The dedicated workflow also reruns **173 inherited C3e tests**: 32 custodian cutover +30 IPC non-settlement +20 Linux peer credential +46 original read-only IPC +28 storage-independent trust +17 real SIGKILL recovery. Exact-head Grammar, offline root-pinned admission, and Fedora signed fake RPM/SELinux guest workflows remain separate requirements. Nurse 2 independently reviews the current PR head and raw CI, followed by operator-only merge disposition.

## WATCH OUT FOR

- A named Unix socket is **not** a production security daemon. Test-only process, filesystem, UID and PID observations are not a remotely enrolled authority.
- `SO_PEERCRED` describes connecting credentials, not necessarily the later sender if the socket descriptor is inherited/transferred. There is no `SCM_CREDENTIALS` per-message security claim or enrolled original-process binding in this milestone.
- The existing one-request JSON diagnostic remains untrusted for authorization. A fixed refusal is not terminal settlement of an earlier different command; an absent response is UNKNOWN/HOLD, never permission to replay.
- The test root guard `GITHUB_ACTIONS=true` and `RUNNER_ENVIRONMENT=github-hosted` limits execution scope but is **not** an attestation of host or key enrollment.
- The user approved local-first development and later independently administered hardware/NAS custody; the actual administrator, root enrollment, current history, one-use challenge and protected recovery are not yet selected. DOC 2 remains owner of real Silverblue process/boot/package/receipt evidence.

## CHECKLIST / NEXT

- [x] Reconcile #2334/#2348 merged 4/4 CI, correct remaining independent review requests to retrospective.
- [x] Add isolated CI-only accepted pathname AF_UNIX read-only boundary using original IPC handler.
- [ ] Verify exact-head CI and raw 24+173 security tests.
- [ ] Obtain Nurse 2 independent pre-merge scoped source/CI review and separate operator merge decision.
- [ ] Continue approved local-development security-service architecture only within DOC 1 scope, preserving independent trust gates.
- [ ] Future separate hardware/admin/root, authenticated native DOC 2 source, current protected nonce/history, C5 consent, actual terminal receipts and operator production activation.

## DECISIONS

This milestone is a **networkless, one-connection development fixture** and does not freeze a production wire schema. Kernel credentials, filesystem modes and a successful diagnostic remain insufficient for independent production Sign-In trust. **PRODUCTION HOLD.**
