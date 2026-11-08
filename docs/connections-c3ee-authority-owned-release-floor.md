# 🏥💜 Universal Connections // C3e-E authority-owned release history fixture

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release authorization and independent history  
STAFF ROLE // Nurse 2 · NRS-2 (operator-assigned, external Hospital-compatible; live registration not verified)  
ASSIGNMENT // C3e-E separate-process, authority-owned *synthetic* release history and signed freshness statements  
BASE // `2f10c4942e3974a07c982800930379289b9f89cc`  
PERMISSIONS // GitHub-only disposable test processes, fixtures, docs and PR; no workstation, real keys, RPM install, privileged host, user credentials, production activation or automatic merge

## IMPLEMENTATION

C3e-D PR #1494 is merged, and the independently recorded post-merge Nurse 2 security audit [#6720783928](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1494#issuecomment-6720783928) gives a narrow PASS to real OpenPGP challenge binding. It specifically cautions that a valid detached signature does not make the supplied release floor **true** or protected. C3e-D's callback could sign any syntactically valid floors supplied by its test logic.

C3e-E advances the **test fixture**, not the production trust root:

1. `tests/connections/c3e_release_trust/C3eAuthorityOwnedFloor.py` is a **separate Python process** communicating through bounded JSON on stdin/stdout. Its command arguments (from the trusted disposable CI harness) choose a *separate authority-owned* private SQLite ledger, an independently pinned release-policy root and the synthetic external signing identity. The untrusted JSON request never selects the state path, signing home, signing key, trusted root, or floor.
2. The authority's `advance` request accepts only paths for a signed release policy, delegated public signer, exact manifest, detached signatures and artifact. It reads its own last committed floor, invokes **unchanged C3e-C** `admit_and_record`, and verifies the release through **unchanged C3e-A** root/delegated OpenPGP signatures before advancing the authority's own SQLite history. The request cannot supply an epoch or sequence number.
3. `attest` accepts only the intended CI node identity, previously pinned release root and a verifier-generated challenge. The authority reads its own committed epoch and sequence, refuses to sign when there has been no verified release, and uses its separate synthetic private key to sign the exact C3e-D statement. This does **not** change C3e-D's signature verifier.
4. The disposable caller opens a **different client-owned SQLite checkpoint**. The caller obtains the authority's signed proof through a test callback invoking the separate process, then uses the unchanged C3e-D verifier to authenticate the proof and feed the authority-owned floors into the unchanged client C3e-C admission. The authority's private signing identity is not included in the candidate release input, the returned proof, or production source.
5. The adversarial test suite covers a valid root-authorized release, a valid monotonic advance, attacker-supplied floor fields rejected by exact request schema, forged/tampered releases rejected before authority state can advance, node and release root substitution, malformed nonce, replay, missing signing key, deleted authority ledger, prohibited RPC operations, and **client database restoration** while the authority still remembers a newer release.
6. An intentionally explicit negative demonstration restores an old **authority** ledger as well, showing this fixture can then sign old release floors. This is a known threat-model failure, not a successful production anti-rollback guarantee.

Scope is exactly four additive CI/test/docs files. Existing C3e-A/B/C/D code, signed-RPM guest tests, C4b Silverblue ownership, systemd/SELinux packaging and live QML/JS/Connections grants are untouched.

## HOW TO USE

No operator workstation action. The dedicated workflow `.github/workflows/connections-c3ee-authority-owned-release-floor.yml` generates all test keys only in temporary GitHub Actions directories and executes each authority call in a new Python process with its own state path. The client and authority storage filenames are distinct. This is not an installed service, background daemon or remote connection.

## VERIFY

Require exact PR-head evidence:

- [ ] New C3e-E separate-process suite passes real GnuPG root/delegated/authority signing checks.
- [ ] Authority refuses `attest` before a root-approved release has been admitted.
- [ ] The untrusted request cannot select/replace a signing home or ledger, nor supply floors.
- [ ] Root-signed release 8 followed by 9 raises authority history monotonically across process restarts.
- [ ] An old client SQLite backup plus newer independent authority history causes old signed release to be rejected; current signed release can be admitted.
- [ ] Forged release, changed signature, replayed signed statement, substituted node/root and missing authority ledger fail closed.
- [ ] Test explicitly demonstrates authority-ledger rollback vulnerability under privileged database replacement.
- [ ] Existing C3e-D 15/15, C3e-C 16/16, C3e-A 18/18 and C2n 6/6 deny-only checks pass.
- [ ] Meta Apollo Grammar; independent technical security audit and operator review timing recorded.

## WATCH OUT FOR

**A separate process on a disposable GitHub runner is not a protected independently administered authority.** Both ledgers and all test signing identities remain accessible to the same CI job/account. A privileged actor who restores the **authority** database can make it sign stale but cryptographically valid floors. No TPM monotonic counter, HSM, immutable audit log, secure remote attestation, protected OS identity, independent administrator, production signing/root custody, key enrollment, key rotation or cross-machine trust distribution exists in this prototype.

This is a CI-only model of the **information flow**: requesting clients do not pick which version is signed, and a client DB rollback is detectable **if** a separate unrolled-back authority remains trustworthy. It is **not** yet release-history anti-rollback for a real compromised/restored system. The authority's command-line config and test callback are trusted harness inputs and are not authenticated operating-system IPC. Candidate files are paths whose bytes are internally snapshotted for cryptographic verification, but no immutable installer/file-descriptor binding or in-memory Python attestation is implemented.

No real provider credentials, user or app identity, NAS/cloud deployment, local Fedora rpm-ostree transactions, production keyring enrollment, automatic workstation changes, authorization, or user consent is enabled.

## CHECKLIST

- [x] Reacquire Syntagma AGENTS/OPERATE, GitHub main, C3e-D merge, independent post-merge audit and concurrent PR ownership.
- [x] New isolated C3e-E branch from current main.
- [x] Add standalone separate-process CI authority and release-signature guarded advances.
- [x] Add 13 adversarial tests covering client restore, authority rollback and untrusted request fields.
- [x] Add dedicated GitHub CI workflow and this recovery handoff.
- [ ] Exact-head CI completion and corrections if needed.
- [ ] Independent security audit and operator acceptance; any merge timing reported accurately.
- [ ] Real operator decision for remote vs hardware-backed independently protected authority, governance and disaster recovery.

## NEXT

Run and inspect exact-head CI. Only fix concrete test failures without changing the production broker or the concurrently owned C4b Silverblue files. After review, the next architecture decision is how to secure the **authority's own signing key and monotonic release history** across server loss, backup restore and compromised workstation, before making any production trust claims.

## DECISIONS

NRS-2 continues the GitHub-only release-trust lane under prior bounded development authorization. User approved C3e-D merge, which was already complete and has no duplicate merge work. C3e-E remains a distinct, independently reviewable development experiment; no workstation writes, production activation, release keys, real credentials, or merge by this handoff.
