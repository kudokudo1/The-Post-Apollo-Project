# 🏥💜 Connections C3e // Purpose-separated TimeW and Hospital signatures

**PATIENT:** The-Post-Apollo-Project · **ROOM:** protected C3e Connections joint TimeW/Hospital trust boundary · **ROLE:** DOC external Hospital-compatible (live registration unverified).
**BASE:** Merged [TimeW C3e #2105](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2105), [Hospital RECOVER #2103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2103), and existing [C3e-AF signed role enrollment](https://github.com/kudokudo1/The-Post-Apollo-Project/blob/main/tests/connections/c3e_release_trust/C3eAFSignedRoleEnrollment.py).
**STATUS:** CI-only proof validation. No signing service, installed root, real compositor, protected Hospital receipt or production authority.

## IMPLEMENTATION

Ed25519 signatures authenticate message bytes **relative to a public key trusted by the verifier**. The public key must be independently pinned to an issuer, and the exact message purpose must be signed. Otherwise a signer for an Identity diagnostic, Hospital writer receipt or TimeW selected window could have its messages wrongly accepted for another action.

This new source-only composition explicitly rejects such cross-domain substitution. It uses different fixed domain separators, audiences and CI key roles for:

- **TimeW Scope A:** Proof input is the existing `TimeWSelectedSurfacePacketPreflight.make_packet_ci_only` canonical fixture packet. The document binds its hash, original selected live-surface lifetime/epoch, seat/session and 32-byte challenge. It still does not prove that SwayPX originated or protected the selection.
- **Hospital RECOVER:** Proof input is the exact existing `StaffingRecoveryQueryPreflight.inspect_candidate_query_ci_only` outcome-UNKNOWN query, including the original PREPARE/PREPARED/COMMIT hashes and 32-byte challenge. It cannot become a Hospital writer COMMITTED/REFUSED/ALREADY_APPLIED result and never resends a grant.

An independently supplied **CI-only** Ed25519 public key, separate expected SHA-256 fingerprint and *different other-role fingerprint*, revocation list, host, release floor and current time are checked. The proof uses exact canonical JSON, domain-separated signature verification, no unknown fields, bounded expiry and no authority claims. A signature made for one domain cannot be reinterpreted under the other, including if the same raw message is signed again.

**Critical limitation:** The signer keys and every independent-looking pin are generated/supplied in the same test runner. Even a valid signature + process-kernel evidence + TimeW fixture or Hospital query is **not** proof that an independent operator enrolled the root, that SwayPX produced the selected surface, or that the protected Hospital writer committed anything. C3e-AF's current signed enrollment has an **Identity-specific** role/purpose; this test must never reuse the same private key or quietly promote that purpose into either TimeW or Hospital.

Every signer custody, installed origin, active-seat provenance, challenge replay/spend, C5 consent, native TimeW move, Hospital RECOVER/COMMIT, Session/Doctor mutation and production flag remains hard FALSE. `run_native_purpose_proof_verifier` always refuses. The only positive claim is that a **caller-pinned disposable CI signature and expected source bytes match**.

## HOW TO USE

The dedicated GitHub CI workflow uses disposable Ed25519 test keys under `RUNNER_TEMP`, checks out Hospital #133 exact fixture source at `dae46d2a8752399dd18162845379ac847065a32c`, tests both domains with hostile source/role/replay substitution and reruns existing TimeW Scope A kernel and Hospital RECOVER tests. No local computer commands or credentials.

## VERIFY

- [ ] 25 cross-domain hostile/positive-format CI test cases pass on exact commit
- [ ] Existing 20 Scope A Linux kernel and Hospital RECOVER regressions pass
- [ ] Static no-signing/no-authority checks and Grammar pass
- [ ] Exactly four new C3e-owned source/test/workflow/doc files
- [ ] Nurse 2 independently reviews exact head and separate TimeW/Hospital custodians respond

## WATCH OUT FOR

Nothing here decides the **real** signer key custody. Two different temporary keys created in one CI process are not two independent trust authorities. A caller can pin its own key and sign its own evidence. The proposed 5-second fixture lease is not an approved production grant duration. Stateless validation accepts the same signed fixture twice; actual one-use replay protection requires a separately protected ledger/issuer. Installation must attest the exact signed release, running process, native packet sender, active unlocked seat, compositor per-surface selection or Hospital durable journal, as appropriate.

**Hospital D1/D2:** PX writer owner chooses real same-transaction journal/REFUSED fence, with backup and migration. **Connections D3/D4:** reject arbitrary caller roots, identify separately approved protected root/release/receipt custody and actual one-use challenge history. **TimeW Scope A:** independently protected SwayPX source and C5 exact-operation one-use consent. Keep all pending owner decisions and final operator acceptance explicit.

## NEXT

Have Nurse 2 and distinct owners evaluate the exact purpose/audience separation and source-type contract. After the PX/SwayPX/C5 owners accept real protected sources, replace caller-controlled test pins with an independently enrolled installed issuer and accepted versioned response, in a separate authorized production increment. Do not treat this fixture as native release proof.

## DECISIONS

Proposal-only source and test. No production signer, root enrollment, real Sway command, Hospital writer command, database migration, C5 grant, local host mutation, merge authorization or final operator acceptance.