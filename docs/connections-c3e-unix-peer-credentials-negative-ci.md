# 🏥💜 DOC 1 // Real Unix peer credentials: inherited socket is not sender identity

**PATIENT //** `The-Post-Apollo-Project`  
**ROOM //** Universal Connections · Protected C3e Identity  
**STAFF ROLE //** DOC 1 · External Hospital-compatible; live Hospital registration not verified  
**ASSIGNMENT //** Narrow CI-only attack test of the merged [read-only IPC #2240](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2240) before proposing any independently protected custodian transport  
**STATE //** Source-only negative kernel demonstration. **Production Sign-In HOLD.**

## IMPLEMENTATION // What the operating system really reports

A Unix domain stream socket has a kernel-managed `SO_PEERCRED` observation. But the meaning of that observation depends on when the socket connection exists.

1. **Inherited socketpair:** A privileged disposable GitHub CI process creates a connected `AF_UNIX` pair **before forking**. A child then drops its groups and user ID to synthetic unprivileged UID 65534 and writes a marker using the inherited endpoint. The parent receives that marker and asks the kernel for the peer credentials. On the tested Linux semantics, the credentials reflect the socketpair's **creation-time** process and root UID, not the unprivileged process that subsequently sent the marker.
2. **Fresh accepted connection:** A disposable parent creates an **abstract**, temporary `AF_UNIX` listener inside the CI kernel namespace. A child first drops to UID 65534 and then establishes a **new connection**. The accepted socket's kernel peer PID/UID is tied to that connecting child. The listener is closed when the test ends and no filesystem socket or service remains.
3. **Never grants trust:** Even in the second case, kernel peer PID/UID are only evidence of a local process relationship at connection time. They do not independently authenticate the package's signed release, running binary, actual unlocked seat, root enrollment, current history head, protected nonce custody, human consent or production Sign-In permission.

A copied or inherited socket descriptor could otherwise make a process-origin assertion misleading. A future real trust service **must not infer signed host identity from `SO_PEERCRED` on a pre-created socketpair alone**. It needs a separately approved protocol and evidence bound to the actual connection, executable/process lifecycle and independently enrolled root. It must refuse ambiguous or stale observations.

The new test-only module and 20-case suite are:

- `tests/connections/c3e_release_trust/C3eUnixPeerCredentialsNegativeCI.py`
- `tests/connections/test_connections_c3e_unix_peer_credentials_negative.py`
- `.github/workflows/connections-c3e-unix-peer-negative-ci.yml`
- This documentation file.

They are **additive**. The original read-only IPC, local SQLite fixture, signed history, cutover, C4b gateway, C5 grant and Identity Center files are not changed.

## HOW TO USE

No workstation commands or NAS provisioning. GitHub CI executes two short-lived subprocess probes on an isolated hosted Linux runner, with transient test-only root to exercise UID drop. It compares kernel observations against the process IDs returned by `fork()`.

The probes write no Post-Apollo persistent records, install no software, create no real signer keys and expose no production socket. The abstract Unix listener used in the control test exists only for the CI test's lifetime and is never packaged or activated.

## VERIFY // What a passing result actually proves

**20 new test cases** assert:

- Inherited socketpair `SO_PEERCRED` reports the original privileged process, despite a separately forked unprivileged sender.
- A new Unix connection made *after* the UID drop reports the connecting process's PID and UID.
- Both observations return explicit diagnostic statuses and all trust, host, seat, credential, C5 and production authorization flags false.
- Forged positive flags, extra fields, pid substitution, type-confused PIDs, fake statuses and missing fields are refused.
- Production-admission calls always refuse, and the test requires the disposable GitHub hosted execution guard.

The workflow also reruns the **28 local IPC + 32 cutover + 28 storage-independent + 28 SQLite-ledger + 24 signed history + 22 signer enrollment + 22 AF + 20 Z = 204 inherited cases**. It checks that `ConnectionsBroker.qml` still has `credentialActionsEnabled: false`.

This is **not** a full descriptor-passing/fork-attack matrix; it is a focused demonstration of one subtle Linux credential distinction. The real host/seat and custodian design still needs independent Native KVM, recovery and actual network trust reviews.

## WATCH OUT FOR

- Linux `SO_PEERCRED` reports kernel-observed **connection credentials**; on a precreated socketpair it cannot establish who subsequently inherited or used the descriptor.
- Neither `SO_PEERCRED` result establishes independent operator-approved trust, security of the NAS or protected current nonce/history.
- `GITHUB_ACTIONS` and `RUNNER_ENVIRONMENT` control *where we run test fixtures*, but are not cryptographic security attestations.
- A future NAS service requires separate administrator/root/key ownership and may not use a guest-local shared SQLite fallback after an outage.
- Merged #2229, #2232 and #2240 have passing automated tests but lack recorded Nurse 2 independent reviews at this checkpoint. The retrospective security review debt remains.

## CHECKLIST / NEXT

- [x] Read Syntagma `AGENTS.md`, Hospital and permissions; verify current `main` and C3e/DOC 2 ownership.
- [x] Demonstrate the inherited socketpair credential pitfall on an isolated Linux runtime.
- [x] Add a new test-only kernel negative milestone without modifying production.
- [ ] Verify exact-head GitHub CI, including 20 new tests and 204 regressions.
- [ ] Obtain Nurse 2 **pre-merge** review of this milestone and retrospective review of #2229/#2232/#2240.
- [ ] Operator decides merge separately; no local-machine, NAS, production service or key actuation.
- [ ] Real future custodian must separately prove independently enrolled roots, authentic live process+seat, current history and crash/rollback recovery, with DOC 2 and C5/Identity owner acceptance.

## DECISIONS

The operator's **Local Development Ledger first → Independent Trust Custodian later** sequence remains accepted. This milestone solely clarifies the Linux process-origin boundary. No actual custodian host, production API, signing key or Sign-In release is selected. **Production Sign-In HOLD.**
