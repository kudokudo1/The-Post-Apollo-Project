# 🏥💜 Universal Connections C3e-AG // Real Linux Identity process observer

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e installed Identity host/source evidence
STAFF ROLE // DOC, external Hospital-compatible · live Hospital registration unverified
ASSIGNMENT // Observe actual Linux process and root-owned Identity script in a disposable CI test, with an opt-in guarded C4b guest candidate mode
OWNERSHIP // Only new C3e-owned reader, tests, workflow, documentation; C4b, Identity, C5 and production unchanged
STATE // Draft GitHub test-only implementation. PROD HOLD

## IMPLEMENTATION

C3e-AF #1996 has merged with four green workflows. Its signed release/witness/receipt key enrollment and full runtime snapshot SHA-256 remain **synthetic CI inputs**. C3e-X/Y/Z validate signed records but do not, on their own, inspect live kernel process state. Older C3e-P checks a different Connections **status** Python host, not the Identity signed RPM gateway. C3e-AG provides a separate, specifically scoped Identity read-only OS observer instead of weakening the status-host verifier.

The observation function reads an **actual Linux process** through a stable pidfd and kernel /proc files, not a guest UART claim or caller-supplied process description alone. It checks:

1. Fixed expected PID/startTicks, the complete kernel effective/real/saved/filesystem UID/GID records (must be nonroot), and a living pinned pidfd before and after the observation.
2. Actual Linux cgroup v2 and actual LSM/SELinux process context from /proc, both matching independently provided *test* pins.
3. Kernel executable inode from /proc/PID/exe, matching the pinned interpreter's actual inode, and bounded exact executable SHA-256.
4. Exact Python isolated invocation `interpreter -I -B script` from /proc/PID/cmdline, and root-owned mode-0555, single-link, nofollow script with root-owned nonwritable parents and independently supplied SHA-256. It rereads start, identities, cgroup, label, cmdline and inode to fail closed on replacement during the observation.
5. In the **optional C4b official Silverblue guest candidate mode**, require an explicit owner-provided test marker, ostree-booted guest, enforcing SELinux, exact C4b Identity test unit, runtime interpreter, installed source path, dedicated systemd cgroup/domain, and read-only `systemctl show` checks of `MainPID`, `ControlGroup` and `ActiveState` before and after the same observation.

The default fixture observes a **real** unprivileged Python child process under disposable Ubuntu GitHub Actions, with a root-owned read-only Identity-named test script at a bounded /run/c3eag-ci-* location. It does NOT claim that child is C4b's signed Silverblue-installed host. The CI root supervisor supplies expected pins. No independent cross-host attestation exists.

All positive return fields explicitly say `InDisposableCI`, `MatchCallerPinsInCI` or `NotAttested`. `independentInstalledHostAttested`, `signedHostOriginAuthenticated`, `operatorReleaseRootEnrolled`, `externallyProtectedChallengeIssuerVerified`, `externalRollbackResistanceVerified`, `c5HumanConsentVerified`, `hostAuthenticated`, `canBeginSignIn`, `credentialActionsEnabled` and `productionAuthority` remain unconditionally FALSE.

## HOW TO USE

The C3e-AG GitHub workflow automatically runs against the PR. It starts only a disposable, unprivileged Linux fixture child and reads real Linux /proc state from a short-lived root CI observer. No package, service, key or password is installed on your workstation.

The C4b official Silverblue branch must not be changed or invoked by this C3e worker. If its **separately authorized owner** decides to opt in later, that owner may run this read-only observer inside the real CI guest *while the installed deny-only service is running*, with independently pinned signed RPM/script digests and expected PID/start/UID/GID. The guarded candidate mode refuses ordinary Ubuntu runs.

That future integration must independently verify expected release-root provenance, signed RPM ownership, SELinux and logind seat, authenticated delivery of the observation to a separately controlled verifier, and cross-check that the process has not been replaced or the key revoked before C3e-Z/AF consume signed evidence. The C3e observer is **not** an attestation or permission API.

## VERIFY

- [ ] Exact-head 22 test cases covering one real UID 65534 Python subprocess, kernel start, process identity, cgroup, LSM, executable, script bytes, path/symlink/mode, process exit, CI guard and no-grant flag refusal
- [ ] Previous 22 C3e-AF signed enrollment and 20 C3e-Z signed witness cases
- [ ] Grammar, release admission and other triggered GitHub regressions
- [ ] NRS-2 independent source review and operator-controlled merge
- [ ] Future C4b-owner opt-in official Fedora Silverblue guest test and independently protected witness-provenance evaluation (NOT INCLUDED IN THIS PR)

## WATCH OUT FOR

The process can rewrite its own argv memory, and a Python file's on-disk hash cannot prove which code is already resident in a running interpreter's memory. Even a genuine kernel /proc observation on one CI host does not become remotely authenticated evidence when copied into JSON, logs or another process. A malicious privileged supervisor can forge expected data, restore unprotected keys, replace files, modify installed system packages or interfere with systemd.

C3e-AG does not verify an installed signed C4b RPM through an independently enrolled production root, secure executable memory, measured OSTree deployment, authenticated active logind seat, separate witness signer, external issuer custody or one-use C5 human intent. Its `c4b-guest-candidate` mode is an **opt-in read-only diagnostic** and not a source of `hostAuthenticated=true`.

Existing C3e-AF test enrollment keys, C3e-Z root-local ledger and C4b test RPM keys are all disposable CI mechanisms. They cannot authorize production sign-in or credential actions.

## CHECKLIST

- [x] Recheck merged C3e-AF, current main and C4b/Identity/C5 ownership
- [x] Distinguish C3e-P status host observer from Identity's own actual installed test runtime
- [x] Add new read-only C3e-specific real Linux observer, adversarial fixture and workflow
- [ ] Exact-head real process test / CI and independent security review
- [ ] Operator approval for any C4b owner-controlled guest integration
- [ ] Independently enrolled trust root, signed host witness channel, external replay issuer, consent and host replacement/loss testing

## NEXT

Close exact-head CI and review the new real-process measurement. Then coordinate a **C4b-owner-controlled** official Silverblue guest opt-in, based on the merged Identity service's exact running PID, script and dedicated enforcing domain. A separately controlled trust/issuer authority must sign and validate those measurements using operator-enrolled keys before any production host-admission proposal.

## DECISIONS

No C4b/Identity/C5 source modifications, real Fedora install or Quickshell restart, local machine write, production enrollment, activation, credentials, merge or claimed live Hospital connection. Operator retains final authority.
