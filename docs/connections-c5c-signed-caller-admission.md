# 🏥💜 Connections C5c // Signed running executable admission (CI only)

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Universal Connections protected host ↔ TASKS encrypted draft recovery
STAFF ROLE // DOC, external Hospital-compatible OPEN AI // CHATGPT (not live-registered)
ASSIGNMENT // Authenticate the exact running test-client executable *before* C5b reviewer binds a TASKS permission requester
SOURCE // C5b PR #1524 merged at `fd60a1fd014d29e59492c63c5a463816a0b37341`
AUTHORITY // Operator "continue" for bounded GitHub security integration; no Fedora changes, secrets, live desktop restart, host installation, real editor text, credential release or production activation

## IMPLEMENTATION

C5b's Linux SO_PASSCRED verifies each packet's PID/UID/GID and a kernel process-start tick, but a PID is not an authenticated Post-Apollo application. A same-UID process could be the correct sender of an unauthorized executable. C5c builds one *test-only* check on that boundary, not a claim of production trusted caller identity.

- **Role-specific trust:** The existing C3e GPG offline signature primitives are reused, including separate test root and delegate public keys in fresh isolated keyrings with gpgv. A root-signed exact policy binds role `postapollo.tasks.recovery.test-client.v1`, policy epoch, minimum sequence and delegated signer fingerprint. The delegated-signed exact manifest binds the same role/epoch, minimum sequence and the SHA-256/size of a compiled dummy executable. Keys are generated solely in GitHub CI, not from the user's keyring or a production signing authority.
- **Kernel evidence before bind:** A candidate PID is not trusted because it was named by the reviewer. The C5c host opens `/proc/<pid>/exe`, streams and hashes the executable inode actually reported by Linux, and checks the process-start tick before and after reading. Only a matching signed manifest allows a C5b `bindClient` reviewer action. After that, **C5b's per-message SCM_CREDENTIALS** still checks the actual sender. Wrong signed role, manipulated unsigned manifest, forged release root, unapproved delegated signer, changed binary and rollback below test floors are refused.
- **Real compiled client:** `tests/connections/fixtures/C5cTasksSignedDummy.c` is compiled in disposable CI. It handles bounded JSON only and contains no TASKS implementation, secrets, user files or code for accessing a credential.
- **Reuse with no host changes:** C5b's existing `serve` accepts an optional injected test ledger class; default C5b invocation is unchanged and C5b regression tests remain mandatory. New `C5cSignedCallerHost.py` uses `SignedCallerBroker` extending C5b's private ledger and binding checks. It does not register a system service or touch production Quickshell.
- **Explicit default deny:** C5a's response flags always remain false for authenticated user/operator, real caller, key release, actual encrypted capture, preview/clear, task source write, checkpoint mutation and general credential actions. A synthetic successful bind is `C5C_SIGNED_TEST_EXECUTABLE_BOUND_NO_REAL_GRANT`.

## HOW TO USE

No operator action or installation is required. GitHub's `connections-c5c-signed-caller.yml` runs real Linux compiled-client and disposable OpenPGP tests.

The running desktop remains unchanged: TASKS → SYNC → RECOVERY → CAPTURE → CHOOSE UNSAVED EDITOR; SAVE ENCRYPTED DRAFT remains disabled. No recovery of real drafts is available yet.

## VERIFY

The exact-head CI must establish:
1. A compiled Linux executable whose running kernel inode matches the separately root/delegate-signed, purpose-bound test manifest is admitted to **C5b's synthetic three-scope, one-use** broker and nothing more.
2. A same-UID process executing a different unsigned binary cannot bind, even when its PID is supplied on the reviewer FD.
3. Signature tamper, forged/swapped root public key, wrong delegated signer, unexpected role and below-floor release fail closed. The requester may not choose trust anchor, key, manifest, policy or release floor.
4. Merged C5b crash-safe consent and per-message credentials, C5a three-scope transport, C3e root signing, M15e snapshot, M15d selection, M15c status controls, and C2a/one-writer guards remain green.
5. Nothing imports C5c into production QML, starts a Fedora service, reads a real key or sends user task contents.

## WATCH OUT FOR

**The verifier authenticates executable bytes and the synthetic signer, not the integrity of every loaded library, runtime memory, SELinux identity, OS package installation or human approval.** An ELF can load libraries or be influenced by same-UID compromise; a signed binary can still have bugs or be abused. Linux /proc-based checks do not stop a privileged attacker who modifies system trust state, keys, process memory or the verifier. The test harness controls its own root fingerprint, keys and release floors, which do *not* constitute independent production custody. C3e's separate history/witness work addresses a different rollback dimension and is not imported as production policy.

C5c is **not** a signed production Connections/TASKS service. It is still unmounted and CI-only. Reviewer process ownership is simulated, consent is not authenticated to a human, the signing root is not operator-enrolled, and the host itself is a Python process not installed with an independently protected release. The signed test client alone cannot grant credentials.

C4b Silverblue/SELinux ownership and C3e release/witness ownership are separate. Do not silently modify their files or infer their completed tests permit production release.

## CHECKLIST

- [x] Recheck Syntagma, current main, C5b merge, open PRs and adjacent C3e/C4b ownership
- [x] Reuse C3e signature primitives with purpose-specific signed TASKS client manifest
- [x] Prove running ELF bytes (not Python script name or caller-supplied string)
- [x] Add adversarial CI tests and minimal C5b test injection seam
- [ ] Exact-head CI passes (C5c/C5b/C5a/C3e/TASKS/CPU++ and grammar)
- [ ] Merge after clean verification under operator standing authority
- [ ] Independently protected release installer identity/SELinux ownership
- [ ] Genuine authenticated human reviewer and protected consent/key lifecycle
- [ ] Actual TASKS single-editor encrypted capture/recovery and native Fedora acceptance

## NEXT

Use the verified C5c code-origin test as one input, not a permission grant, when designing the protected production host. Coordinate independently pinned installed caller release identity with C3e/C4b owners. Then build an authenticated human approval path and host-owned Secret Service lifecycle. Only those gates can authorize M15e's live editor snapshot.

## DECISIONS

Keep production default-deny, one TASKS FileView writer, no automatic draft replay, no live credentials and no local changes. C5c is an incremental external test milestone; the operator retains final acceptance.
