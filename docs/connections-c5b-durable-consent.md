# 🏥💜 Connections C5b // Durable TASKS consent and per-packet sender identity

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Universal Connections protected host ↔ TASKS encrypted draft recovery
DOCTOR // External Hospital-compatible DOC, OPEN AI // CHATGPT; live Hospital registration unverified
ASSIGNMENT // Advance C5a's isolated scope broker toward host-owned restart-safe state and kernel sender authentication, without production activation
PHASE // GitHub-only disposable implementation and CI verification
SOURCE // C5a PR #1514 merged at `20a3b025`; baseline main at `237eda15e8173234883dafdd7cb0d0b64b0b1061`
PERMISSIONS // Operator's November 8 "let's go" continues bounded TASKS/Connections integration on GitHub. No Fedora edits, desktop restart, real draft access, Secret Service, production credentials, service installation, source writes or merge until relevant checks pass.

## IMPLEMENTATION

C5a proved independent reviewer and requester FDs with three fixed scopes but held its approvals in memory and had no per-packet origin check. A pre-created Unix socketpair's SO_PEERCRED records the socket origin, not necessarily the *current sender* after its endpoint is passed elsewhere.

C5b adds **only an experimental, never-mounted host**, reusing C5a's scope/target validation and all production-denied response flags:

- `services/connections/experiments/C5bTasksDurableConsentHost.py` receives **SCM_CREDENTIALS via SO_PASSCRED and recvmsg on every Linux SOCK_SEQPACKET message**, binding the requesting client to a reviewer-specified test-process PID/UID/GID and its kernel process-start tick. A transferred client FD used by a different process is denied, even if it has the same UID. Separately, the reviewer FD's per-message sender must match its original kernel SO_PEERCRED origin. The trusted reviewer here is **only the disposable test harness**. The caller is *not* authenticated to a signed Post-Apollo release.
- A host-owned private SQLite ledger, with synchronous FULL commits and 0600 regular files inside a 0700 test fixture, stores each exact-scope/target/source-generation request. Only the separate reviewer FD can approve, revoke or stop the host. A one-time execute records CONSUMED **before acknowledging** its synthetic step. A persisted revoke marks all pending and approved requests REVOKED. On every new host process, any outstanding PENDING/APPROVED state becomes INTERRUPTED and can never be reused, including across OS restarts. Approval freshness is bounded to 30 seconds by the host monotonic clock while the process remains active.
- Exclusive host file locking prevents two test hosts from sharing the same authority database concurrently. Directory marker and environment requirements deny execution outside a disposable nonroot GitHub Actions fixture. Bounded request count prevents growing a sensitive uncontrolled log in a test run.
- `tests/connections/test_connections_c5b_durable_consent.py` uses real independent subprocesses, transferred FDs, crash/restart, exact scope enforcement, revoked/expired/consumed tombstones, malformed frames, private-file permissions and default-deny production inventory. The workflow reruns C5a, C2c/C2l and TASKS M15e/M15d/M15c/M13m/M13p/M13t writer/Connections regression gates.

Every response retains C5a's false values for host/operator authentication, real source verification, credential actions, key release, real capture, real preview, real clear and source write. No task text, source path, checkpoint, key or access token enters the host or its database.

## HOW TO USE

There is **nothing to install or activate**. This PR runs only in GitHub disposable CI. In production, TASKS → SYNC → RECOVERY → CAPTURE → CHOOSE UNSAVED EDITOR still presents disabled SAVE ENCRYPTED DRAFT; PREVIEW and CLEAR remain disabled. A kernel PID bind supplied by CI is not a human consent prompt.

## VERIFY

Required at the reviewed head:
- Real Linux nonroot separate host/client processes, with reviewer FD never given to the client.
- A forwarded client descriptor and reviewer descriptor used from a different process are denied through kernel per-message credentials.
- All three scopes enforce exact target/epoch/source generation; no self-approval, cross-scope reuse, repeated execute or key operation.
- A consumed request never replays; a durable revoked approval stays refused; crashed-host outstanding approvals become INTERRUPTED before the restarted host accepts new work.
- Expired approvals consume and deny, private file/symlink/weak permission and concurrent-host checks fail closed, malformed requests never expose plaintext.
- C5a/C2c/C2l, M15e/M15d/M15c/M13m/M13p/M13t and C2a/M11d regressions remain green; production flags and one FileView writer unchanged.
- **Not tested or claimed:** signed executable-release identity, independently authenticated human consent, SELinux isolated service UID, host-owned Secret Service keys, real TASKS draft snapshot, actual cryptography in this new broker, or Silverblue desktop activation.

## WATCH OUT FOR

This is **not** a production permission host. The reviewer channel is created by a CI harness running under the same test UID; same-UID compromise, ptrace/FD theft before binding, privileged process impersonation, tampering with files owned by the test UID and malicious replacement of the Python interpreter are **not** solved by SO_PASSCRED. The host records test PID credentials, not signed release provenance. Future production host must be launched and attested through the approved signed/SELinux-protected Connections trust chain before any real capability exists. A stronger authority is needed for explicitly authenticated human consent and release pinning.

Concurrent Connections C4b Silverblue confinement PR #1521 is owned by another worker. C5b does not touch its branch, policies, code, services or tests. C3e release-floor work also stays under its existing ownership.

Restart is **fail closed**: outstanding approved requests never survive a host crash; the user must explicitly approve again once a real host exists. That is a deliberate safety decision, not a missing continuity feature.

## CHECKLIST

- [x] Reconcile main, C5a and Syntagma protocols; find C4b concurrent ownership.
- [x] Implement isolated C5b kernel per-message sender identity and durable refusal ledger.
- [x] Add real process, restart and denial tests plus dedicated CI.
- [ ] Exact-head test run and necessary corrections.
- [ ] PR verified, then merge under existing approval.
- [ ] Reconcile signed release, confined UID/SELinux and independent human-consent authority with their owners.
- [ ] Host-owned real key lifecycle, trusted source receipts and one-editor snapshot integration.
- [ ] Actual encrypted checkpoint save, restart/unlock preview, explicit clear.
- [ ] Fedora native verification and operator acceptance.

## NEXT

After CI passes, merge the isolated C5b test-only layer. The next protected-host stage must bind kernel sender identity to an independently verifiable installed release (not just PID/interpreter), and bind reviewer identity to a genuine protected operator-consent channel. Coordinate with C4b/C3e owners; do not merge their implementation into this room. Only then may the TASKS editor adapter send real plaintext directly to a protected encryption host.

## DECISIONS

No extra TASKS writer, no automatic replay, no altered saved-source behavior, no permission widening, no UI-only consent substitute, no production key release. C5b approval intentionally does not survive host restart. The PR is GitHub-only and unmounted; none of these tests constitute real operator consent or final user acceptance.
