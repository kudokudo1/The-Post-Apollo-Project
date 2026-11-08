# 🏥💜 Universal Connections // C3e-C durable release admission checkpoint

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release trust / rollback protection  
STAFF ROLE // Nurse 2 · NRS-2, external Hospital-compatible; live registration not verified  
ASSIGNMENT // C3e-C crash-durable test release state with externally asserted freshness and independently pinned signer  
BASE // `d9e52f49abe8ffb7dc9343d9f04f1177e5574317`  
SCOPE // GitHub-only isolated tests, disposable CI, documentation and review; no real keys, workstation changes, service activation, credentials or production installation

## IMPLEMENTATION

Merged C3e-A #1461 verifies a detached root-signed policy authorizing exact artifact digest, delegated signing key and external policy/release floors. Merged C3e-B #1465 proves the policy-admitted digest can reach an offline Fedora guest before its fake status RPM is installed. **Those external floors were caller arguments; neither milestone persisted a coherent local release checkpoint across process restart or a crash.**

C3e-C introduces a **CI-only, SQLite-backed checkpoint**, not a production trust store:

- `tests/connections/c3e_release_trust/C3eDurableFloor.py`: explicit one-time synthetic `bootstrap` with externally supplied pinned root and minimum policy/release floors. No implicit database recreation after loss or corruption; no key/certificate generation and no package management.
- Stable input snapshots: bounded regular release files are copied using `O_NOFOLLOW` before GnuPG verification, with file identity and modification checks. The existing C3e-A verifier authenticates the snapshots against the external root fingerprint and minimum epoch/sequence, then the checkpoint stores hashes of exactly those verified policy and artifact bytes.
- Crash-durable, serialized SQLite transaction: `BEGIN IMMEDIATE`, `synchronous=FULL`, `journal_mode=DELETE`, root-pin comparison, monotonic policy epoch/release sequence, same-epoch policy collision denial and same-sequence artifact collision denial. No credential/user-service action follows the commit.
- The latest committed floors survive a new process and are enforced against valid-but-stale root-signed material. A child process killed after an uncommitted update must leave the last committed checkpoint intact. Concurrent admissions cannot lower the stored floors.
- `tests/connections/test_connections_c3ec_durable_floor.py`: disposable root/signer A/signer B OpenPGP fixtures and adversarial cases for missing bootstrap, restart, downgrade, same-epoch or same-sequence equivocation, signer revocation/rotation, wrong root, tampered signed policy, symlinked candidate, corrupted database, rollback of a valid database snapshot, external-floor absence, crash and concurrent updates.
- `.github/workflows/connections-c3ec-durable-release-floor.yml`: invokes the C3e-C suite, existing C3e-A real signature tests, and C2n deny-only contract. No QEMU, host install or production API.

Previous C3e-A/B, C3d RPM, C2r/C2s and the successor-owned C4b Silverblue recovery PR are not modified. No production QML/JS is imported into this new module or enabled.

## HOW TO USE

No workstation actions. This code lives **only in `tests/connections/`** and is exercised on the disposable GitHub runner. `bootstrap()` is an explicit synthetic initialization call, not an installer. `admit_and_record()` snapshots the release inputs, calls the existing C3e-A cryptographic verifier and commits monotonic test state; it cannot approve an API grant, install an RPM or start a service.

## VERIFY

On the exact PR head:

- [ ] C3e-C real GnuPG/SQLite unit tests pass, including separate subprocess crash and restart checks.
- [ ] Valid root-signed release 8 commits, valid release 9 advances, valid old policy/release cannot roll back.
- [ ] Same-epoch different signed policy and same-sequence different signed artifact refuse.
- [ ] Root-signed signer rotation and revocation remain enforced.
- [ ] Failed verification, missing bootstrap or corrupted state never silently recreate trust.
- [ ] Restored older database + *newer external trusted floor* refuses old release.
- [ ] Concurrent valid commits cannot reduce stored floors.
- [ ] Existing C3e-A real GPG tests and C2n production deny-only checks remain green.
- [ ] Independent security review and operator decision, separate from developer CI evidence.

## WATCH OUT FOR

**SQLite durability is NOT rollback resistance against an attacker or administrator who can replace the database with an older valid copy.** The test explicitly demonstrates this risk. An independently protected, sufficiently recent **external policy-epoch/release-sequence floor is required at every admission**; in this pilot, the floor is merely a test parameter. An operator-approved and rollback-resistant authority is not yet chosen or enrolled. Full-device backup restore, root compromise, supply-chain substitution, database/parent-directory privilege separation, authenticated checkpoints, hardware counters, TPM policy, and operator recovery ceremonies remain outside this scope.

This prototype copies checked input files into a temporary directory to reduce verifier input races, but does not bind those snapshots to a real OS installer or make an immutable runtime package. File identity observation does not cryptographically attest loaded Python memory. A successful database commit is **not** authorization to activate the service; it merely records successful CI-only cryptographic admission.

No production root/private key, HSM/TPM enrollment, actual Silverblue `rpm-ostree` layer, real provider account, app caller identity, consent, revocation of credential grants, NAS/company sync or operator native acceptance has been implemented.

## CHECKLIST

- [x] Read current Syntagma AGENTS and Hospital protocols; verify current main, C3e-B merge and neighbor C4b owner.
- [x] Create isolated C3e-C GitHub branch; preserve every production deny-only contract.
- [x] Implement explicit-bootstrap SQLite release floor and real GPG snapshot verification.
- [x] Add restart, crash, conflict, forgery, revocation and file/database rollback tests.
- [x] Add GitHub workflow and this recovery report.
- [ ] Exact-head CI complete, log verification, fix only evidence-supported issues.
- [ ] Independent security review and operator acceptance/merge.
- [ ] Future: operator-approved release-trust custody, durable external freshness anchor, protected store permissions and realistic signed `rpm-ostree` recovery.

## NEXT

Run CI. Investigate any failures without disabling root pinning, rollback floors, signature checks or transaction durability. Once verified, submit independent review and report precise CI head, paths, exception cases and rollback limitation. **Do not claim production trust enrollment or native acceptance** from these fixtures.

## DECISIONS

GitHub-only fake release-state development. No live Hospital registration, workstation modifications, production key import, real credentials, service installation/activation, changes to concurrent C4b files or PR merge by this report. User supplied standing merge authorization for suitable reviewed work, but developer verification and operator final acceptance remain separate.
