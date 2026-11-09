# 🏥💜 Universal Connections C3e-P // Observe an actually running Python host script

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected service identity  
STAFF ROLE // DOC · Original development assignment  
ASSIGNMENT // Read-only kernel process + Python script-file measurement for the C4b handoff  
CONCURRENT OWNERS // C2v/C4b Silverblue signed guest/reboot, C5 consent/reviewer  
PREDECESSOR // C3e-O #1605 merged: signed C3d RPM contains exact script, unit and D-Bus policy  
HANDOFF // [Issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606)  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-O proves the **signed RPM's extracted host script bytes** match the tracked Python script, but not that this script is running. C3e-M proves which **native ELF interpreter** a test process executes, but a Python interpreter's signature cannot authenticate the *Python script* it loads.

C3e-P is a bounded **read-only live process observer** for Linux, to be used in disposable CI and only later as an optional C4b-owner-invoked guest fixture. With a separately supplied expected script SHA-256 from the successful signed C3e-O verification, pinned PID/start/UID/GID/interpreter and expected script path, it checks:

1. Real kernel /proc PID and boot-local process-start tick before and after measurement, four kernel real/effective/saved/filesystem UID/GID values, and the actual interpreter inode reported by `/proc/PID/exe` against the exact expected interpreter's inode.
2. Exact command-line shape `interpreter script --read-only`; no arbitrary write action, alternative script, extra flags or shell wrapper is accepted.
3. The root-owned, single-linked, mode-0555 script opened through `O_NOFOLLOW`; bounded exact byte hash and stable file inode/timestamps during the read. Path ancestors must be root-owned, directories and non-writable by other users; the test fixture is limited to `/run/c3ep-ci-*/status-host`.
4. A later owner-controlled C4b Silverblue guest may explicitly opt into checking the real `/usr/libexec/post-apollo/connections-status-host` path only if `GITHUB_ACTIONS=true`, `POST_APOLLO_C4B_TEST_GUEST=1`, root and `/run/ostree-booted` are present. This source alone does NOT start a guest, install a package or alter the C4b runtime script. The other worker retains its own file ownership and verification gates.

An Ubuntu GitHub Actions runner starts a **real separate nonroot Python process** executing a deliberately inert 0555 root-owned test script. Seventeen cases test correct live process identity, changed script after launch, mismatched reference hash, swapped PID/start/UID/GID/interpreter, unapproved command action, symlinks, writable or missing file, invalid script scope, malformed pins and production-authorization refusal.

This verifies actual running process and observed on-disk file bytes, rather than fabricated success-only evidence. **It does not measure the C4b guest yet**; the test program is not the signed C2r service and does not claim otherwise.

## HOW TO USE

GitHub Actions workflow `.github/workflows/connections-c3ep-running-python-source.yml` runs automatically on PR, using `sudo` only inside its disposable Ubuntu 24.04 runner. No user workstation commands, credential loading, host installation, network service, or native QML changes.

When the C4b owner supplies guest integration, the intended proof input is the exact script SHA-256 from C3e-O's verified signed RPM, *not* a digest chosen by the process being inspected. The exact owner-approved guest measurement must also bind systemd MainPID, D-Bus owner, SELinux domain, installed RPM identity and package source according to C3b, before it is admissible even as installed test evidence.

## VERIFY

- [ ] All 17 real Linux subprocess/kernel/process-file tests pass on exact PR head.
- [ ] C3b installed origin/C2n denial and C3e-N/I existing signed recovery checks remain green.
- [ ] Meta Apollo Grammar and separate signed-RPM offline regression pass.
- [ ] Independent security review; operator acceptance separate from CI.
- [ ] C4b owner approves guest measurement integration and proves script equality during the actual guest's verified running service, prior to cleanup and real rollback.

## WATCH OUT FOR

The `/proc/PID/cmdline` field comes from **mutable process memory**; a process can rewrite its arguments. Matching the on-disk script's SHA-256 does **not** prove those bytes are what Python loaded earlier or is executing now, and a privileged actor could replace the file outside a single observation window. Checking `/proc/PID/exe` proves the *interpreter* ELF, not the script.

Thus, this is **not cryptographic attestation**, not independent executable integrity or an authenticated cross-boundary origin. C3e-O's pinned hash must come from a separately trusted signed artifact validation, and even a matching script file cannot become an authorization token. A guest-produced log or JSON string remains untrusted outside that guest without separately enrolled, challenge-bound signing and replay protection. The proof does not establish SELinux confinement, C4b two-reboot cleanup, a real signed deployed host, human consent, C5 authorization, or provider credentials.

All output grant fields are FALSE, including `installedGuestMeasured` unless the real restricted C4b guest path is explicitly used; even then `evidenceCryptographicallyAttested:false`, `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

## CHECKLIST

- [x] Reconcile C3e-O merged source, 4/4 green CI and C4b/C2v ownership.
- [x] Add read-only process/script observer without modifying any C4b files.
- [x] Add real nonroot subprocess and adverse identity/script-file tests.
- [x] Add separate CI and durable handoff.
- [ ] Fix observed exact-head CI errors within DOC-owned branch.
- [ ] Independent review and operator disposition.
- [ ] C4b owner takes its side of [handoff issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606).
- [ ] Authenticated signed installed guest provenance and human consent before any provider operation.

## NEXT / DECISIONS

This is a **main-based, reviewable, deny-only DOC implementation**. It prepares one concrete local runtime measurement mechanism to pair with C3e-O's actual signed Python package payload. It does not independently solve cross-guest proof authenticity, rollback protection, or active Connections provider operations.

No GitHub merge, live Hospital registration, workstation change, production credential or operator final acceptance is implied.
