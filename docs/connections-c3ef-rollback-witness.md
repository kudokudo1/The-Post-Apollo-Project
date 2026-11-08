# 🏥💜 Universal Connections // C3e-F witness-ledger rollback experiment

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Universal Connections · CPU++ SETTINGS · release trust / authority rollback  
STAFF ROLE // Nurse 2 · NRS-2, external Hospital-compatible; no live registration verified  
ASSIGNMENT // C3e-F bounded synthetic rollback witness for authority-owned release history  
PERMISSIONS // GitHub-only isolated tests, CI, docs and PR. No operator machine, real keys, protected server, system service, credentials or production activation.

## IMPLEMENTATION

Merged [C3e-E PR #1506](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1506), with recorded independent [post-merge security audit](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1506#issuecomment-6722835373), established that a test-only authority process signs only previously root-authorized release epochs/sequences from its own SQLite database. That audit identified the remaining gap: **restoring the authority database to an older good copy lets it sign stale, cryptographically valid history**.

C3e-F implements a **third CI-only SQLite checkpoint**, representing a separately enrolled *logical witness*. It is a synthetic threat-model experiment, not actual independently protected storage:

1. `tests/connections/c3e_release_trust/C3eRollbackWitness.py` explicitly bootstraps a private SQLite witness with a pinned authority GPG fingerprint, release signing-root fingerprint, synthetic node identity, and minimum epoch/sequence. Missing, corrupted, symlinked or world-readable witness state is denied; no automatic reenrollment/recovery.
2. A test verifier generates its **own 256-bit challenge** and obtains the C3e-E authority's C3e-D-format detached OpenPGP response, which must verify against the separately pinned synthetic authority public key. The exact release ID, challenge, node, release root and purpose remain bound by unchanged C3e-D signature checks.
3. The witness stores **the maximum previously verified signed authority floors**. It holds SQLite `BEGIN IMMEDIATE` through the comparison, existing **C3e-C root-signed release admission** on a *separate* client DB, and witness checkpoint commit. A fresh, correctly signed but LOWER floor after an authority DB restore is refused.
4. The 16-case adversarial suite uses C3e-E's genuine disposable GPG/signing-process fixture and **three distinct databases** (client, authority and witness): valid releases 8→9 advance all three; restoring the authority (or both client and authority) to 8 with witness still at 9 is blocked even though the rolled-back authority produces a valid *freshly signed* floor.
5. A deliberately explicit counterexample restores **all three** valid database files to their old versions: a stale release 8 then succeeds. This is documented and tested as a **failure of software-only rollback resistance**, not a verified security protection.
6. Additional cases reject forged anchor key, replay, mismatched pins/nodes, missing ledger, unsafe permissions/symlinks, tampered signed release, missing client ledger and silent witness bootstrap. No existing C3e-A/B/C/D/E files or production Connections broker QML are modified.

Only four new files in this PR: `C3eRollbackWitness.py`, `test_connections_c3ef_rollback_witness.py`, `.github/workflows/connections-c3ef-rollback-witness.yml`, and this report. The parallel C4 Silverblue and CPU++ Social/UI worker assignments are untouched.

## HOW TO USE

No desktop action. The workflow `.github/workflows/connections-c3ef-rollback-witness.yml` generates disposable GPG signing identities, uses separate local SQLite files and invokes the existing C3e-E authority process. There is no network or privileged remote service. All test keys disappear with the runner.

## VERIFY

On exact PR head:

- [ ] 16/16 C3e-F real GPG three-ledger tests pass.
- [ ] Old client + authority SQLite rollback is refused against newer intact witness.
- [ ] Genuine replayed, substituted, wrong-scoped or unsigned proof cannot change witness floors.
- [ ] Tampered release and missing client ledger do not advance witness.
- [ ] Damaged/missing/symlinked/unprotected witness state is refused without implicit bootstrap.
- [ ] Explicit restoring all three records admits stale signed release, demonstrating unresolved risk.
- [ ] C3e-E (15), C3e-D (15), C3e-C (16), C3e-A (18), and C2n (6) prior tests remain green.
- [ ] Existing Fedora signed-RPM verification and Meta Apollo Grammar green.
- [ ] Independent technical security review; operator merge/final acceptance recorded separately.

## WATCH OUT FOR

**A third SQLite ledger on the same disposable GitHub runner is not a hardware- or remote-backed rollback-resistant trust anchor.** The user, CI job or a privileged attacker capable of restoring all three ordinary files can restore the witness too. The test demonstrates that **restoring all three** defeats the check. A fully compromised signing authority can also sign an artificially high floor and block legitimate releases. This fixture proves *witnessed consistency only if its own history remains intact and its keys stay trusted*. It does not attest that every released version was witnessed or that there have been no unwitnessed authority advances.

The two SQLite commits (client and witness) are not a single cross-database atomic transaction. If the process crashes between them, fail-closed recovery and operator-mediated reconciliation need design before production. This is also **not** secure IPC between independent machines: the injected Python callback and trusted runner configuration are synthetic. Root custody, witness key enrollment, hardware-backed counters, secure audit-log replicas, quorum/replication, root/signer rotation, disaster-recovery ceremonies and operational authority separation all remain unimplemented. Calling the third file a witness must not be confused with proving independent physical custody.

There is **no real API grant**, production service activation, credential access, protected RPM trust-root installation, Silverblue rpm-ostree deployment, company NAS access, or modification of the operator's workstation.

## CHECKLIST

- [x] Verify current GitHub main, merged C3e-E, independent audit, current worker ownership and Syntagma/Hospital rules.
- [x] Create dedicated C3e-F GitHub branch.
- [x] Implement independent CI-only witness and 16 adversarial cases.
- [x] Create CI and this recovery document.
- [ ] Verify exact-head CI and fix demonstrated failures.
- [ ] Independent security review and operator merge decision.
- [ ] Operator decisions for genuinely separate protected history, key custody, replication and recovery.

## NEXT

After tests and review, choose a genuine **operator-managed trust boundary**: e.g. an independently administered NAS/server with separately protected signing key and rollback-resistant journal, or a hardware-backed counter plus independently stored signed checkpoints. Define root enrollment, identity authentication, quorum/restore behavior, and how a rejected/stale workstation recovers without blindly resetting trusted floors. Only then consider wiring release authorization to the actual Silverblue lifecycle with C4 ownership coordination.

## DECISIONS

All implementation and signing material remains disposable GitHub CI. User's approval to merge C3e-E is acknowledged, and GitHub confirms it was already merged; no duplicate merge. C3e-F is a new isolated reviewable assignment, not approved for live production use. No local writes, real credentials, or production authorization.
