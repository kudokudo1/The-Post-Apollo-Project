# 🏥💜 C3e-K // OS-separated release witness, disposable CI only

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS · Protected host / signed release trust  
STAFF ROLE // DOC · Original development assignment  
PROVIDER // OPEN AI // CHATGPT, external Hospital-compatible (not live registered)  
SOURCE // C3e-I merged #1540; C3e-J merged #1585  
NEIGHBOR OWNERS // C2v/C4b Silverblue rollback; TASKS C5 protected-consent broker  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-J proved kernel-backed connection and per-message identity, but its request client and witness were running under the same Unix UID. That client could directly read or alter its own synthetic witness database. C3e-K demonstrates the next layer of the intended protected-host boundary using a disposable Ubuntu Actions machine:

1. A root process owns the witness SQLite ledger and its private `/run/c3ek-ci-*/private` directory; its permissions are `0600` and `0700`. The simulated requesting program runs as Linux `nobody` with a different UID. The non-root process cannot open the witness file.
2. A root-controlled socket directory is traversable by the intended client's group but not writable by that client; its socket uses mode `0660`, root owner and the client group.
3. A test supervisor pins the expected client PID/UID/GID and kernel process-start clock ticks at launch. The server checks both the connection's kernel `SO_PEERCRED` and every request's `SCM_CREDENTIALS`. A different process or a forwarded connected descriptor is denied even when the alternate sender has the same UID.
4. The ONLY operation is J's read-only witness-floor inspection using existing C3e-F row validation and SQLite `mode=ro`. The server returns enrolled identity digest, policy epoch and release sequence; no signing pins, file paths, approval authority, key material or mutation are exposed.
5. The server refuses missing or symlinked ledger, invalid enrollment, writable socket directory, oversized packet and all mutation requests. The client cannot choose a witness path or impersonate an operator identity inside its packet.

The test runner constructs only `/run/c3ek-ci-*` fixtures, and removes them. This is **not a production service**, does not install root code on the user workstation, and neither enables the Connections QML broker nor changes the C2v/C4b or C5 owners' files.

## HOW TO USE

Source: `tests/connections/c3e_release_trust/C3eProtectedWitnessPeer.py`  
Tests: `tests/connections/test_connections_c3ek_protected_witness.py`  
Workflow: `.github/workflows/connections-c3ek-protected-witness-identity.yml`

The GitHub workflow runs the isolated test as root **only inside its disposable Ubuntu runner**, then runs prior C3e-J/I/H/G/F signed-release and crash regressions as the ordinary runner. No instructions here authorize running this sudo test on a user's Fedora machine.

## VERIFY

- [ ] Exact-head C3e-K workflow and eleven adversarial identity/DAC checks pass.
- [ ] Real non-root client cannot open or replace protected witness; server can inspect it.
- [ ] Kernel PID/UID/GID/process-start and per-packet sender must all match.
- [ ] Forwarded socket FD, foreign process, mutation, oversized packet, missing/symlinked ledger and misconfigured directory refuse.
- [ ] Prior signed release, recovery and existing same-UID J checks pass.
- [ ] Independent security review; no merge without required authorization.

## WATCH OUT FOR

The CI root-vs-nobody demonstration is **not a production root daemon**, an enrolled root of trust, or an independent remote witness. It has **no independent rollback protection** against privileged restoration of all ledger copies. The process pins are supplied by a test supervisor, not a signed host policy; real identity, persistent trust, confinement, service lifecycle and operator consent have not been established. Running a real root daemon would require separate threat-model review, package provenance, hardened systemd/SELinux confinement, and C4b owner coordination.

A distinct UID does not by itself authenticate a signed executable or prove a human consent gesture. The socket is request/response and read-only. It does not authorize C3e-I supersession, C5 TASKS drafts, NASA FIRMS, Proton, key release, deployment changes or any production credential action.

## CHECKLIST

- [x] Reconstruct current DOC and parallel owner scope.
- [x] Preserve C3e-J implementation and signed recovery gates.
- [x] Add separate OS identity and protected-file proof with adversarial tests.
- [x] Add dedicated CI and durable handoff.
- [ ] Inspect exact-head real Linux results, repair only observed defects.
- [ ] Independent security review and operator disposition.
- [ ] Design separately authorized, confined single-writer operations and verified production enrollment before any integration into the real host.

## NEXT / DECISIONS

Keep this an isolated prototype and the production Connections broker disabled. Next development should be a precise, owner-coordinated plan for an authenticated service that can combine C3e-I release trust, C4b signed system lifecycle and C5 bounded consent without treating any test-only identity as production authority. Our original DOC development lane proceeds in parallel with the Silverblue rollback owner.
