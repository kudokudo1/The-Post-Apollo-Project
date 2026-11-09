# 🏥💜 Universal Connections // C3e-J read-only witness peer

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · protected release trust  
STAFF ROLE // DOC · Developer (restored from original parallel-work assignment)  
ASSIGNMENT // C3e-J bounded process isolation of read-only witness observation  
PROVIDER // OPEN AI // CHATGPT, external Hospital-compatible; live registration unverified  
CONCURRENT OWNER // C2v/C4b Silverblue recovery, separate owner/branch  
PRODUCTION // HOLD

## IMPLEMENTATION

Following merged C3e-I #1540, the release-trust witness is a separate *logical* SQLite file but not an independently protected process. The next architecture step is to exercise Linux process isolation before admitting write operations, not to grant synthetic authority to a real host.

This GitHub-only additive fixture introduces `C3eReadOnlyWitnessPeer.py` as a separate one-request Linux AF_UNIX SOCK_SEQPACKET server. A test supervisor pins the expected **PID, UID, and kernel process-start tick** at launch. The receiver verifies both the connection's kernel `SO_PEERCRED` identity and the request packet's `SCM_CREDENTIALS` identity. A connected descriptor forwarded to a child is refused because the packet sender differs from the connecting process.

The only accepted packet is `WITNESS-FLOOR-READ-V1`. The server examines the existing C3e-F witness ledger through SQLite `mode=ro` / query-only, calls the *existing* witness record validator, and returns just the enrolled identity digest and observed release floors. It never updates a client, witness, authority, key, service, policy, deployment or approval ledger. It refuses nonexistent/symlink/world-readable witness files, invalid records, unsolicited operations, foreign packets, redirected descriptors and stale configured process identity. It does not automatically recreate missing state.

This is a **source-isolated disposable CI prototype**, not a trusted production process. No production daemon, live UI control, real signing key, provider credential, account grant or active deployment is introduced.

## HOW TO USE

The tests run in GitHub Actions at `.github/workflows/connections-c3ej-readonly-witness-peer.yml`. No workstation commands or UI deployment are involved.

The supervisor creates a fixture under a private temporary directory, enrolls one synthetic C3e-F-style witness row, launches the peer as a separate process, and attempts authorized and adversarial reads. CI also reruns C3e-I/H/G/F crash and signed history regressions plus C2n deny-only policy checks.

## VERIFY

- [ ] Exact branch code parses and new process-based unit tests pass.
- [ ] Kernel connection and packet sender identity match; stolen socket FD and foreign process refuse.
- [ ] Only read-only floor inspection works, no raw signing pins/credentials returned, no DB mutation.
- [ ] Missing/symlink/tampered witness and mutation requests fail closed without initialization.
- [ ] Earlier C3e-I/H/G/F signed approvals and recovery tests remain green.
- [ ] Independent source/security review and operator acceptance separate from CI success.

## WATCH OUT FOR

A separate same-UID process is **not a rollback-resistant external witness** and not independent key custody. The test supervisor supplies its own process identity pins and controls the witness file. Another process with the same UID or privileged file access can still alter/replace all software ledgers. A kernel PID alone is insufficient across process restarts, so the fixture compares process-start ticks; it does not prove executable release identity, an OS-confined domain, a genuine human gesture, or a signed external authority.

The read-only response **does not authorize** C3e-I supersession, C5 TASKS recovery, RPM installation or key release. No production Connections permissions or real authentication are enabled.

## CHECKLIST

- [x] Reconstruct merged C3e-I source and identify missing process boundary.
- [x] Verify C2v/C4b and TASKS C5 have distinct owners.
- [x] Implement independent read-only kernel-peer fixture and adversarial tests.
- [x] Add separate CI and recovery documentation.
- [ ] Fix observed CI defects and request independent review.
- [ ] Design next stage: privileged single-writer witness custody with a distinct OS identity, signed authority attestation and operator-controlled enrollment; this requires a separate operator decision before any live integration.

## NEXT / DECISIONS

This milestone restores the primary DOC development line rather than replacing it with Nurse 2 review. It is an isolated first step toward separate witness custody; it deliberately does not touch C2v Silverblue rollback, C4b signed-service source, TASKS C5-owned code, or live Post-Apollo. The next work should use its test results to determine which authenticated command protocol can safely evolve beyond read-only, while preserving C3e-I's pending-intent and signed-approval rules.

No production activation, local modification, GitHub merge, or final operator acceptance is implied.
