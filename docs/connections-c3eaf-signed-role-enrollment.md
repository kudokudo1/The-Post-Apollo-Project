# 🏥💜 Universal Connections // C3e-AF signed key-role enrollment

PATIENT // The-Post-Apollo-Project
ROOM // Universal Connections · protected C3e issuer / host evidence
STAFF ROLE // DOC · external Hospital-compatible, live Hospital registration unverified
ASSIGNMENT // Remove freely caller-supplied C3e-Z test signer keys from a future owner-coordinated acceptance seam
OWNERSHIP // C3e-only additive code, tests, workflow and this document; no C4b / Identity / C5 changes
PRODUCTION // HOLD

## IMPLEMENTATION

Merged C3e-Z already verifies an Ed25519-signed Identity release, separate signed full runtime evidence, four denial receipts, and one-use root-local CI challenge. However its expected release-root, witness and receipt public keys are independent **caller arguments**, which test their signatures but do NOT prove who enrolled or authorized these keys. In genuine host admission, a self-supplied key would be insufficient.

C3e-AF creates a narrow **CI-only** signed role-enrollment preflight, then calls the existing C3e-Z verifier without changing it. A separately caller-pinned Ed25519 enrollment-root public key verifies a domain-separated, canonical signed enrollment that binds:

- Fixed Identity CI role, protocol schema and purpose
- Exact expected Identity host scope identifier, release epoch and sequence, plus the SHA-256 of the full expected canonical C3e-X runtime snapshot
- The public release-root, host-witness and denial-receipt signing keys in distinct roles
- Exclusion of key aliasing among the enrollment root and all three consumer roles

Only after the enrollment signature, key-role separation, exact scope and full runtime-snapshot digest match does C3e-AF pass the derived public keys into unchanged C3e-Z. The caller-supplied expected snapshot is frozen first and the same immutable value is reused throughout enrollment and C3e-Z consumption. C3e-Z still checks the signed release, full witness record, four real Ed25519 denial receipts, root-local one-time challenge and source/host consistency. A forged/wrong signed enrollment is refused before consuming the challenge.

All positive indicators are explicitly suffixed **InCI** or **RootLocalCI**. All returned flags for operator-owned root custody, independent installed-host attestation, external challenge issuer, external rollback resistance, C5 consent, sign-in, credentials and production authority remain **FALSE**.

## HOW TO USE

GitHub-only source, tests and workflow. No Post-Apollo UI action, local software, real key, credential, provider account or system service is modified.

Workflow: .github/workflows/connections-c3eaf-signed-role-enrollment.yml

It uses a disposable Ubuntu runner with a pinned cryptography dependency and root-local CI ledger. It runs 22 new positive/adversarial signed role-enrollment and snapshot-binding tests, the already-merged C3e-Z regressions and a static broker no-grant check.

The four test signing identities are minted within the same disposable runner. This is a signed-key-role **format and composition experiment**, NOT proof that an independent real organization or external authority controls the enrollment signer.

## VERIFY

- [ ] Exact-head 22 C3e-AF adversarial regression tests PASS
- [ ] Existing C3e-Z signed release / signed host / one-use challenge suite PASS
- [ ] Grammar and other triggered root-signed release regressions
- [ ] Independent NRS-2 security review and operator-controlled merge
- [ ] Later real independently protected witness producer, external enrollment signer and issuer custody approval

Adversarial suite refuses a wrong enrollment root, tampered signature, substituted key after signing, valid enrollment for wrong keys, wrong host ID, wrong release epoch/sequence, aliased key roles, malformed key hex, duplicate/noncanonical/partial JSON, CI marker text passed as enrollment, invalid signed release, challenge replay, changed PID/cgroup snapshot after enrollment, a root-signed false replacement snapshot, and attempts to claim production authority.

## WATCH OUT FOR

**Real root enrollment is not implemented.** A signature is authentic only relative to the **separately trusted public key**. In these tests that key is a throwaway CI fixture. Nothing here provisions a root through a protected out-of-band channel, records operator acceptance, protects a signing private key, rotates or revokes that root, or supplies externally rollback-resistant monotonic release history. A hostile caller choosing both the enrollment root and the signed enrollment can still make this CI parser report test consistency. This must never be treated as a production authentication result.

**The host scope ID and signed snapshot digest identify only the expected CI record, not actual Linux host origin.** C3e-AF now binds the exact C3e-X expected process snapshot digest to the enrollment, but that expected snapshot is still provided by the disposable test harness, not independently observed from a real Silverblue installed process. Matching it does not prove kernel /proc observations, systemd cgroup, SELinux enforcing label, active logind seat or C5 user gesture. C4b still owns the real producer and independently controlled witness channel; Identity DOC still owns its consumer. C3e should accept externally independently authenticated evidence only after an approved trust/enrollment and custody decision. Existing C4b real Silverblue CI results and C3e-AD/AE artifact hashes cannot be used as substitutes.

**External challenge custody is not implemented.** The unchanged C3e-Z one-use ledger is root-local CI SQLite. Its entire state can be rolled back by an administrator. No real production key grants, token retrieval, browser sign-in or live native commands are enabled.

## CHECKLIST

- [x] Recheck C3e-AE merge, current main, C4b evidence contract, existing C3e-Z/X/Y source and Syntagma role boundaries
- [x] Implement isolated read-only C3e key-role enrollment wrapper
- [x] Add 22 adversarial tests and dedicated CI workflow
- [ ] Exact-head GitHub test verification and independent reviewer audit
- [ ] Operator acceptance / authorized merge
- [ ] Separately enrolled real signing authority, signed kernel-observed host evidence, external replay authority, C5 one-use consent

## NEXT

Finish exact-head CI and independent review without broadening the authority flags. Next practical integration requires an owner-approved enrollment authority and source-of-truth key rotation/revocation process, plus signed real host/process/seat observations from C4b and external challenge custody from the protected issuer. Record operator decisions on custody and recovery before attempting real host authentication or production sign-in.

## DECISIONS

No local machine mutations, production root/key enrollment, C4b or Identity or C5 source ownership transfer, automatic merge, or live sign-in.
