# 🏥💜 C3e-M // Signed running native host origin, CI-only integration

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · protected host and release trust  
STAFF ROLE // DOC · Original protected Connections development assignment  
ASSIGNMENT // Bind the two-sided kernel status-transport test to independently signed, purpose-bound native host executable bytes  
DEPENDENCY // C3e-K merged #1591; C3e-L mainline recovery #1596 merged  
PARALLEL OWNERS // C2v/C4b Silverblue deployment/rollback, TASKS C5 consent  
PRODUCTION // HOLD; GitHub-only, no host installation

## IMPLEMENTATION

C3e-K checks the requester's Linux credentials and OS-separated witness file permissions. C3e-L makes the nonroot client check the responding root host's kernel PID/UID/GID, process-start tick, socket provenance, enrollment digest and release floor. C3e-M adds a **third, privileged test-supervisor observation** of the kernel's actual running `/proc/PID/exe` inode rather than trusting the process name, client-supplied executable path, Python interpreter script, or a status response.

This is an intentionally narrow bridge of existing C3e-A signing primitives and C3e-L transport:

1. The disposable test runner generates a root signing key, delegated signing key and attacker key. A purpose-bound root policy authorizes exactly the `postapollo.connections.test-native-status-host.v1` role, minimum epoch, release sequence and delegated key. The delegated signature covers a manifest pinning the compiled native ELF's exact SHA-256 and size.
2. A privileged test verifier snapshots bounded, nofollow, root-owned signing inputs into a private directory; imports keys into isolated temporary OpenPGP keyrings; verifies both real detached signatures, root fingerprint, delegation, exact role and release floors.
3. The verifier checks a pinned root host PID and Linux process-start tick; opens the **kernel-referenced actual executable inode** through `/proc/PID/exe`, validates ELF shape, hashes up to 2 MiB, and refuses any unsigned, changed or divergent executable. A second process-start check prevents admitting an obvious process replacement during verification.
4. A separately compiled C **test-only** native host accepts one Linux `SOCK_SEQPACKET` read-only packet, checks the nonroot caller's `SO_PEERCRED` and per-message `SCM_CREDENTIALS`, and sends a bounded **synthetic status** containing the already-enrolled fixture digest and floors. The existing C3e-L nonroot client verifies this root process and status independently.
5. The combined test associates the same root host PID and process-start across privileged signed-code verification and the nonroot C3e-L transport checks. It does **not** issue a reusable authorization token, write any witness/authority/client ledger, enroll a real operator, or change actual Post-Apollo QML behavior.

The native C fixture deliberately does **not** read the C3e-F SQLite database. Its reply is synthetic; using it to assert real witness custody or production signing authority would be wrong. The real protected SQLite witness remains root-owned and unchanged. This milestone proves the signed *running executable* seam plus two-sided transport, and identifies the next owner-coordinated native service integration needed.

Five additive files only: this documentation, purpose-bound signed verifier, native C test fixture, adversarial real-GPG/Linux-process tests, and CI workflow. No changes to C2v/C4b, TASKS C5, production `ConnectionsBroker.qml`, installation files, or credentials.

## HOW TO USE

Run only the GitHub Actions workflow `.github/workflows/connections-c3em-signed-native-host-origin.yml`. It compiles a native ELF on the disposable Ubuntu runner, creates temporary root/delegate signatures, runs the verifier under CI `sudo`, and spawns a separate root native status host with a nonroot C3e-L client. There is no desktop action, RPM install or production secret.

**This is not a production host installer**, and the test-only root code must not be run on an operator Fedora workstation.

## VERIFY

- [ ] Exact-head C3e-M real GPG/ELF and two-sided transport positive test.
- [ ] Unsigned/wrong binary, forged root public key, wrong signer, signed wrong role, tampered manifest, obsolete floor, stale PID start, wrong UID and unsafe file paths refuse.
- [ ] Real distinct-UID witness remains unavailable for direct nonroot reads, and all observed fields have grants disabled.
- [ ] Existing C3e-L/K/J transport and C3e-I/H/G/F recovery suites pass.
- [ ] Exact-head Grammar, offline root-pinned release admission and signed fake-RPM tests pass.
- [ ] Independent source/security review and operator final acceptance separately documented.

## WATCH OUT FOR

A verified ELF digest does **not** by itself establish runtime integrity of loaded modules, signed OS package installation, immutable Silverblue origin, kernel attestation, or a trustworthy human consent gesture. The test signing keys are made by the same disposable runner and are **not** operator-enrolled or hardware-protected. A signature on a Python interpreter would identify the interpreter only; not the Python service script. That is why the positive fixture is an actual compiled C ELF, not the existing Python host.

The test supervisor has root authority and controls the expected PID, enrollment and signatures; a hostile privileged process or restore of all software ledgers remains beyond this experiment. Root-owned private storage is not remote rollback-resistant custody. C3e-M **does not authenticate a signed installed executable** through C4b's official systemd/SELinux installed service, because that integration is another owner's dependency.

Never elevate `signed_native_elf_verified_in_ci` or `transport_peer_verified` into production `hostAuthenticated`. The verifier's output explicitly includes `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

## CHECKLIST

- [x] Recheck original DOC development work and Syntagma Hospital role continuity.
- [x] Detect and repair C3e-L's earlier merge-to-stale-branch issue with separate mainline recovery PR #1596.
- [x] Preserve native Silverblue C2v/C4b and TASKS C5 owners.
- [x] Add purpose-bound signed running ELF gate, real native/OS peer fixture and adversarial regression suite.
- [x] Add isolated CI workflow and handoff.
- [ ] Inspect exact-head CI; correct only demonstrated scoped defects.
- [ ] Independent review, parent dependency reconciliation and operator final acceptance.
- [ ] Coordinate future signed installed service identity and host-owned consent with existing C4b/C5 owners before any real credential action.

## NEXT / DECISIONS

This PR is **based directly on current main**. The original C3e-M PR #1597 merged into C3e-L's already-landed development branch; those files never reached main. This separate mainline recovery carries the same tested implementation. Review and authorization remain required before merge. Do not merge a child to a branch that has already landed on main; retarget onto main after its parent merges and verify the changed files are truly present there.

Next after this bounded prototype is an owner-coordinated **C4b signed native installation / C3b origin** contract for the running host, then C5 controlled consent and a first real read-only provider transaction. This cannot be represented as completed by synthetic GPG fixtures. No production activation or local machine modifications are authorized.

## RECOVERY // MAINLINE MISSING FILES

Original C3e-M PR #1597 is marked merged into a stale C3e-L development branch but its five files were absent from main at recovery checkpoint. This PR copies the same source/tests/workflow and only updates this provenance note. Its exact-head CI is required before acceptance.
