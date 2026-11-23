# 🏥💜 DOC 1 // Local SQLite history development ledger (CI-only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Protected C3e Identity  
**STAFF ROLE:** DOC 1, external Hospital-compatible; live Room/session registration unverified  
**ASSIGNMENT:** First bounded source milestone under [the operator's local-development → future independent-custodian roadmap (reviewed draft PR #2217)](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2217) (in separately reviewed draft #2217 at time of this milestone).  
**STATE:** Source/CI experiment only; no installed signer, native service, machine changes, provider secrets, real Sign-In or production trust. **PRODUCTION HOLD.**

## IMPLEMENTATION // Concrete storage and process behavior

The new `tests/connections/c3e_release_trust/C3eLocalDevelopmentHistoryLedger.py` is deliberately inside `tests/`, not `services/`. It **reuses** the existing root-only disposable GitHub CI directory/file validation from `C3eRDurableChallengeLedger.py` and the unchanged signature/role/domain/canonical/history preflight from `C3eOperatorWitnessHistoryContinuity.py` (merged #2192). Neither existing source is modified.

A new **separate disposable SQLite file** inside a `/run/c3er-ci-...` test directory stores three tables:

| Table | Bytes and purpose | Not evidence of |
| --- | --- | --- |
| `meta` | Test schema/epoch, current test history-head SHA-256, test sequence | Operator-approved latest head or rollback resistance |
| `challenges` | SHA-256 of locally generated 32-byte challenge, test audience, host/release pins, previous head, deadline, state, test committed head | Independently issued/consumed production nonce |
| `history` | Test sequence, previous/next history-head digests, challenge digest, signed-record digest | Trusted external immutable log or authorized grant |

**Actual transaction:** an explicit test-only issuer first commits the challenge's hash, expected local head and deadline before returning the challenge. `record(...)` obtains `BEGIN IMMEDIATE`, refuses unknown/spent/expired/wrong host or release/stale-head challenge, calls the existing #2192 Ed25519 signed-history verifier with the *currently stored* previous head/sequence and exact issued challenge, and conditionally marks the challenge consumed while inserting the next history record and updating the head inside the **same SQLite transaction**. An internal test fault before commit rolls back the entire transaction. A simulated missing ACK **after** commit requires outcome query rather than automatic replay.

The entire result remains labeled `C3E_LOCAL_HISTORY_DEVELOPMENT_ONLY_ROLLBACKABLE`, and every authority flag remains literal `false`. No public API adapter, socket, production signin, C5 human consent, native root enrollment or provider credential route is added.

## VERIFY // Adversarial tests

The new dedicated workflow runs **28 isolated cases** around:
- exact signed continuity + local one-use consumption; refusal of tampering, wrong role pin, revoked signer, signed wrong head/sequence/challenge/release and forged authority field;
- missing database never implicitly created; explicit-only bootstrap; wrong file mode and symlink; non-GitHub and non-hosted refusal;
- expired, unknown, replayed and stale concurrent challenges; simultaneous commits on one nonce permit only one local success; issue after a successful head advance;
- crash *before* commit leaves both nonce and head unchanged; lost ACK *after* commit has queryable consumed result, not automatic retry;
- **the deliberately demonstrated local security failure**: same-UID fixture actor copies an old SQLite image, commits, restores that old image, then uses the same originally valid signature/challenge again. This is an **expected negative observation about A-style local trust**, not a failed test or an acceptable production behavior.

Existing #2192 signed-history, #2075 enrollment, C3e-AF/Z tests are rerun unchanged. The workflow also checks that `ConnectionsBroker.qml` still has `credentialActionsEnabled: false`.

## HOW TO USE

This is **GitHub-hosted disposable Linux CI only**. No operator desktop command, package installation, NAS setup or user credential action exists. Do **not** copy the test DB to the eventual independent custodian and call it current trusted history. Development keys and test challenge digests are never eligible for production enrollment.

The future storage-neutral client interface is not frozen by this proof. An independently administered custodian must later establish fresh out-of-band approved roots, its *own* reliable current head/nonce ledger, authenticated receipt semantics, anti-fork durable updates, backups/recovery and no stale-local fallback. A developer-owned SQLite file will remain untrusted.

## WATCH OUT FOR

The existing C3e-R module already has local one-use challenge consumption. This new module is *not* a replacement: its narrow experiment is making **the verified signed-history next-head advance and the nonce consume atomic in one local database** and then showing that whole-database rollback can defeat both. A machine or root-capable actor may restore the DB, its revoked-keys state and old proof together; neither POSIX permissions nor signed fixture data establish independent current-history custody.

Host process release/seat origin is still the separately owned DOC 2/C4b producer. C5 consent, Hospital D4, Forest and TimeW retain separate purpose keys and authority. A later self-hosted NAS must not simply export a writable share to the desktop.

## CHECKLIST / NEXT

- [x] Confirm #2217 is in independent Nurse 2 reviewed draft state, and that #2192 signed-history source and C3e-R test ledger already exist.
- [x] Keep original C3e-R and signed-history files unchanged; add one test-only combined ledger and new adversarial tests/workflow.
- [ ] Exact-head 28 cases and inherited regression CI all pass.
- [ ] Independent Nurse 2 security review of source/diff and same-UID rollback evidence **before any authorized merge**.
- [ ] Operator decides merge separately; no workstation/source deployment via this milestone.
- [ ] Distinct future custodian enrollment, authentic DOC 2 running gateway evidence, rollback/fork/crash/restore, C5 and Identity user authorization are still production HOLD.

## DECISIONS

The **Local Development Ledger first → Independent Trust Custodian later** development sequence is operator-directed. This implementation supplies only CI evidence on the *local* half, not a trusted issuer, final key-storage selection, production cutoff, or promotion of local SQLite data.
