# 🏥💜 Connections C3e-W // Durable CI challenge after guest-pair comparison

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected C3e receiving and replay trust  
STAFF ROLE // DOC · original protected Connections developer  
ASSIGNMENT // Join existing C3e-V signed-vs-plain format check to C3e-R's root-local disposable one-use ledger  
CONCURRENT OWNERS // C4b/C4d guest evidence and C4b Identity Silverblue; Identity DOC; C5 human consent  
PRODUCTION // HOLD

## IMPLEMENTATION

Previously merged [C3e-V #1792](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1792) compared 11 fields between a separately CI-signed Q statement and the plaintext C4d guest diagnostic. It used Q's *volatile* one-use challenge, but did not update C3e-R's durable challenge ledger. A successful comparison could therefore be replayed by a new process with the same token. The root-local R ledger already protects challenge consumption across process restarts in disposable CI.

**C3e-W is a narrow, test-only composition**, without changing V, R, Q, U or the C4b producer:

1. The isolated, privileged GitHub runner explicitly creates the existing protected /run/c3er-ci-* SQLite ledger; R itself issues a random 32-byte challenge, recording its digest *before* the test report is signed. Missing/unsafe ledger refuses and never bootstraps automatically inside the receiver.
2. The receiver snapshots a bounded Q evidence document, detached GPG signature and test public key once, using the existing nofollow and ownership checks. It copies them into a new root-owned mode-0700 private directory inside R's root, with each file mode 0600. Both V and R read **those same private snapshots**, not the mutable original caller path.
3. V must first check the plaintext C4d report against caller-supplied expected RPM/script/interpreter/PID/start/UID/GID and verify a pinned test-signed Q statement for the challenge. V must match all 11 shared fields and require its pre-verification evidence digest to match the bytes Q actually verified. A mismatch or invalid signature/refusal **does not consume** R's issued challenge.
4. Only after a passing V report does the existing R verifier independently reverify the same immutable snapshot and conditionally commit its **one** transition from issued to consumed in SQLite. Duplicate threads and a fresh verifier process are refused. The return value is only a CI receipt with all externally trusted authentication, production, consent and credential flags false.

C3e-W does **not** claim that the two verifications plus SQLite constitute one cross-process/distributed atomic transaction. The protected directory and DB belong to the same disposable runner root. The durable commit applies to the one-use test challenge; it cannot prove the signed *content* is true or stop a privileged snapshot/ledger rollback. Snapshot files are deleted when verification finishes.

No separate signer, new cryptographic protocol, actual C4b guest RPC, C5 consent call, Identity Gateway adapter, QML credential action, service process, or workstation change is introduced.

## HOW TO USE

The dedicated workflow .github/workflows/connections-c3ew-durable-pair-consumption.yml runs on a disposable Ubuntu 24.04 GitHub runner. Only the W test subprocess and existing R regression tests are run as isolated CI root. Do not run the ledger fixture on a workstation or try to use this as an Identity login gate.

The tests create ephemeral OpenPGP signatures, strict C4d diagnostic lines and root-local issued challenges. They exercise valid consumption, verifier restart, mismatch leaving an issued challenge, bad signer, false authority, unknown nonce, missing ledger, original input replacement after snapshot, concurrent consumption, invalid expected pins and Identity service role refusal.

## VERIFY

- [ ] Exact-head C3e-W root-only positive/adversarial tests.
- [ ] Existing C3e-V 13, C3e-Q 23, C3e-U 21, C3e-R 21 tests and root-pinned release and signed RPM regressions.
- [ ] Meta Apollo Grammar and independent NRS-2 security review of this narrowly scoped CI-only change.
- [ ] Owner-controlled merge under previous explicit operator authorization only after independent review.

## WATCH OUT FOR

The root-owned /run SQLite is durable across a **process restart**, but **not independently rollback-resistant**. A privileged actor restoring the full DB can restore consumed challenges. There is no independently enrolled real issuer, fresh remote attestation, verified C4b operating system measurement, trusted signed RPM/interpreter/PID/start source, or external transport. A malicious source may supply two matching but false records. The *full UART line is not signed* by Q; V checks only the 11 overlapping fields. C4b Identity Silverblue is a different service, not authenticated by this C4d test.

C3e-W's positive test receipt contains signedAndDiagnosticPairMatchedInCI and challengeConsumedDurablyInCI as **CI-only facts**, while externalIssuerCustodyVerified, externalRollbackResistanceVerified, signedGuestOriginAuthenticated, evidenceCryptographicallyAttested, installedGuestMeasured, hostAuthenticated, canApprove, credentialActionsEnabled and productionAuthority are **always false**.

The next real integration requires C4b's independently established signer/root enrollment, installed RPM and kernel process/SELinux/seat evidence, release/host revocation and rollback, a challenge-bound full signed record, protected external nonce/rollback custody and separate C5 one-use human intent. Never promote C4d guest self-report or disposable signature into production authority.

## CHECKLIST

- [x] Verified merged V/Q/R/U and current C4b/Identity ownership; role remains DOC.
- [x] Composed W root-only CI test receiver + adversarial tests, workflow, and recovery doc.
- [ ] Verify exact-head CI results and fix any bounded failures.
- [ ] Independent Nurse 2 review before applying prior operator merge authorization.
- [ ] C4b separately verified installed host/issuer and C5 one-use consent before real Identity or Connections login.

## NEXT / DECISIONS

Use the new negative gate to demonstrate **pair mismatch does not consume**, **correct test pair consumes once**, **replay after process restart cannot reuse it**. Recover from [protected handoff #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606) and this PR's branch. The production host evidence protocol cannot be inferred or implemented in the C4b owner's files by the protected DOC worker.

No production activation, local machine changes, signer installation, credentials, external Hospital registration, C4b/C5 ownership transfer or unchecked PR merge.
