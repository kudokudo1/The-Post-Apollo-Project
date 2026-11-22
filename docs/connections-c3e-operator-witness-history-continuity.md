# 🏥💜 Universal Connections // Protected C3e witness history continuity

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected C3e/Identity witness integration  
STAFF ROLE // DOC · explicitly assigned successor; previous C3e/Identity worker PAUSED  
ASSIGNMENT // Source-only independently signed witness history **continuity preflight**, following signed enrollment #2075  
OWNERSHIP // C3e additive files only; no merged C3e source replaced, no C4b/C5/PX or native Identity edits  
ORIGINAL BASE // Phase 1 #2075 exact head `f36440ec957d2f95e02356cf1d406be8fcac4e42`; now recovered separately onto application `main`  
PRODUCTION // HOLD

## IMPLEMENTATION

The accepted C4b official Silverblue tests prove guest-local receipt signer ↔ guest-local signed release correspondence. The existing protected C3e-Z and C3e-AF format verifies signed release, separate witness and denial receipt role keys plus one-use root-local CI challenge. Operator preflight #2075 adds a separately supplied root fingerprint, strict revoked role lists, and minimum release floor, but cannot authenticate the operator-controlled source of those inputs.

**New Phase 2** adds `C3eOperatorWitnessHistoryContinuity.py`, a read-only proposal verifier that calls the **existing Phase 1 preflight unchanged**. It requires a **fourth separately pinned history-authority signer role**, different from enrollment/release/witness/receipt keys, and verifies an exact canonical, domain-separated Ed25519 signed history proposal with:

- The exact previously checked enrollment digest, full expected runtime snapshot digest, host identifier, release epoch/sequence, and all three enrolled role fingerprints
- Independently caller-pinned history signer and exact SHA-256 of its public key, plus explicit revocation input
- The exact independently caller-pinned previous history head SHA-256 and previous sequence; the next sequence must be **previous + 1**
- The SHA-256 of a fresh separately issued 32-byte challenge, not a self-generated challenge
- No extra fields, alias roles, Boolean masquerading as integer counters, duplicate keys, altered signed bytes, or noncanonical encodings

The digest of the domain-separated signed record and signature is a **candidate next history head**. Its acceptance remains **read-only**. The verifier cannot store or independently custody the prior head, burn the nonce, commit the next head, establish trusted process/seat provenance, or enable production identity. It returns `signedNextHistoryRecordMatchesCallerPinsInCI` and `signedHistoryExtendsOneExactCallerPinnedHeadInCI` as test-only observations; every authority/consent/credentials/sign-in flag is **false**.

## HOW TO USE

GitHub CI only. No local operator action, workstation installation, production key, provider login or machine enrollment. This source intentionally lives under `tests/connections/c3e_release_trust/`. Run the isolated workflow `.github/workflows/connections-c3e-operator-witness-history-continuity-ci.yml` on the mainline reconciliation draft.

The 24 new adversarial tests reuse the Phase 1 #2075 fixture and disposable Ed25519 keys. They cover exact next-head construction, signed forged grant fields, key/authority substitution, revoked signer, wrong signed host/release/role/snapshot, skipped or replayed sequence, changed previous head, nonce replay, malformed and duplicate signed JSON, signed numeric boolean coercion, parent enrollment changes, and repeated verification without consuming a challenge.

Inherited regressions: 22 Phase 1 enrollment preflight + 22 existing C3e-AF + 20 existing C3e-Z. **Expected total 88 tests**, before independent verification. CI also asserts no production grant, SQLite writer, socket, subprocess or signing private key in the verification module.

## VERIFY

- [ ] 24/24 new hostile signed-history tests pass on exact PR head
- [ ] 64/64 Phase 1/C3e-AF/C3e-Z inherited tests pass
- [ ] Grammar, other triggered jobs, source-scope/diff inspection pass
- [ ] Independent Nurse 2 exact-head review of new source, history signer's separation and signed-field binding
- [ ] Operator merge disposition after independent review; no auto-merge

## WATCH OUT FOR

**Signed-history consistency is not externally rollback-resistant custody.** In these CI tests the supposedly independent signing authority, previous head, revocations and fresh challenge are all synthetic inputs from one runner. A malicious caller can roll back BOTH the previous head and proof; the positive result does **not** mean the system remembers the latest real history, survives privileged file replacement, or has a trusted operator root. An actual owner-controlled witness process/storage service must hold the previous head and nonce ledger outside the untrusted client/gateway domain and atomically consume a challenge/commit the next history head. Off-host/TPM/HSM/journal architecture, signer rotation/revocation/recovery and backup trust are **decisions requiring separate operator authorization**.

**No origin attestation.** A correctly signed record saying `hostId` or `receiptKeySha256` matches enrollment does not prove its real Silverblue `SO_PEERCRED`/PID/start/SELinux/active logind seat. It must later be joined to owner-approved live kernel-origin evidence with a fresh external issuer challenge. The C4b source already verifies guest-local evidence and is accepted; do not rewrite it.

**No implicit signer enrollment.** Phase 1 #2075 is already merged into application `main`. Phase 2 #2076 was merged only into Phase 1's feature branch; its four source files were absent from `main` at recovery. This isolated reconciliation ports those same four files onto current `main`, subject to fresh CI, independent Nurse 2 review, and separate operator merge approval. Nothing enables provider credential operations or sign-in.

## CHECKLIST

- [x] Nurse 2 scoped PASS for Phase 1 #2075; 64 tests and 4 workflows on exact head
- [x] Verify Phase 1 #2075 merged into `main`
- [x] Recover the Phase 2 #2076 exact source head `7c0266709290` onto a separate `main`-based branch
- [x] Add deny-only signed history candidate and adversarial tests/workflow/docs
- [ ] Exact head CI pass
- [ ] Independent scoped review and separate operator merge decision
- [ ] Independently custodied real signer, prior-head storage, nonce consumption and native witness state machine
- [ ] C5 active-human consent, PX protected writer, native sign-in/recovery acceptance

## NEXT

For this mainline reconciliation, rerun exact-head CI and obtain an independent adversarial review before requesting an operator merge decision. The actual next production integration requires an **operator-chosen custodian and recovery architecture** for (1) trust roots, (2) signed revocation/rotation, (3) externally durable witness-history head/sequence and one-use nonce ledger, and (4) OS/seat isolation. After these authority choices, implement an OS-isolated witness-service writer that admits the exact reviewed proof and persists it atomically with one-time challenge consumption. A source-only format test cannot stand in for that service.

## DECISIONS

No production trust claimed, no real signing key, no installed/native service, no local machine mutation, no C4b/C5/PX/Identity ownership expansion, no PR auto-merge, no recovery reset. The operator has final acceptance; live Hospital registration remains unverified.

## RECOVERY PROVENANCE // DOC 1, 2026-11-22

Original PR [#2076](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2076) was merged into `feat/c3e-protected-witness-enrollment-preflight-20261119`, **not** `main`, on 2026-11-20. The original source head `7c02667092908cd3b9db1f357b861255beabb941` passed four GitHub workflows, but had no recorded independent Nurse 2 review. Its 4 files are independently recovered here without altering the original feature branch. This recovery documentation corrects historical merge-status references only; it does not grant any trusted custody or native authority.
