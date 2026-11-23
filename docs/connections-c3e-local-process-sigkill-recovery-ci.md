# 🏥💜 DOC 1 // Real local writer-process SIGKILL recovery (CI only)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Connections · Protected C3e Identity  
**STAFF ROLE //** DOC 1, external Hospital-compatible; live Hospital registration not verified  
**ASSIGNMENT //** Exercise *actual operating-system termination* of the existing test SQLite signed-history writer on both sides of commit, then reopen from an independent disposable Linux process  
**PHASE //** Local Development Ledger only. Not selected/provisioned protected custody  
**PRODUCTION //** Sign-In HOLD

## IMPLEMENTATION // Concrete data and processes

The existing C3e `DevelopmentLedger.record()` validates a synthetic signed history proposal, marks the exact local challenge `consumed`, inserts one history link and advances its local SQLite head/sequence in a single `BEGIN IMMEDIATE` transaction. An earlier reference test covered simulated exceptions and lost ACK. This milestone adds **real Linux SIGKILL**, without writing any new application SQL, service, listener, key manager or native command.

A disposable GitHub-hosted Linux test allocates its existing `/run/c3er-ci-*` root-owned development SQLite ledger and fake Ed25519 signed evidence. It forks a child as the sole writer, using the original `DevelopmentLedger.record()` and its unchanged `C3eOperatorWitnessHistoryContinuity` verifier. A small child-only wrapper around the existing SQLite connection detects one exact SQL execution point:

| Actual kill point | What happened to SQLite | What is knowable |
| --- | --- | --- |
| **AFTER_META_UPDATE_BEFORE_COMMIT** | Challenge, history and meta updates executed inside the *uncommitted* transaction; Linux SIGKILL skips Python rollback/cleanup | A fresh process performs journal recovery; local test row should remain `issued` and original head/sequence unchanged |
| **AFTER_SQLITE_COMMIT_BEFORE_ACK** | Original SQLite `COMMIT` completed; child receives actual SIGKILL before it could send a normal result | A fresh reader should see `consumed`, head incremented once; parent had **no terminal ACK**, and this is still untrusted local settlement |

The test parent observes the forked writer's actual negative SIGKILL process exit code, then forks a **different** process to reopen SQLite and read the local head/sequence and exact challenge outcome. No internal in-memory response from the killed writer counts as proof.

A deliberate backup/restore attack copies the pre-commit development database, kills the writer **after** a real commit, then restores the old SQLite bytes. The *fresh* reader sees the old `issued` state, and the unchanged synthetic signed proposal can be replayed successfully after restore. This is an **expected demonstration of local-only rollback vulnerability**, never an authority claim.

Every recovery report uses `LOCAL_PROCESS_CRASH_OBSERVATION_NOT_PROTECTED_SETTLEMENT`, recommends `HOLD_NO_AUTOMATIC_RETRY_INDEPENDENT_CUSTODIAN_REQUIRED`, and requires all original C3e admission, signer, host, C5, credential, production, externally current history, terminal receipt, noncommit proof and safe retry flags to be **false**.

This test-specific wrapper is not a frozen future NAS protocol or production crash-injection hook. It is never installed or imported by a live service.

## HOW TO USE

No changes to the user desktop, installed services, NAS, credentials, kernel settings or local Git worktree. The tests run only in a root-owned disposable GitHub-hosted CI root already permitted by C3e-R; environment markers and local `/run` directory checks are **execution scoping only**, not attestation of an independent trusted issuer.

The new files are exclusively in DOC 1's C3e development/test lane:

- `tests/connections/c3e_release_trust/C3eLocalProcessSigkillRecoveryCI.py`
- `tests/connections/test_connections_c3e_local_process_sigkill_recovery.py`
- `.github/workflows/connections-c3e-local-process-sigkill-recovery-ci.yml`
- This documentation file.

No existing C3e writer, IPC, root verifier, C4b installed gateway, C5 consent, Forest/Hospital/TimeW or SwayPX code changes. Original SQLite mutation and signature-checking behavior are reused exactly.

## VERIFY

Sixteen new hostile/positive-development tests cover actual kill before/after `COMMIT`, re-opening from another process, local issued-versus-consumed observations, replay refusal after an unrolled-back commit, deliberate full-DB restore/replay despite a previously committed transaction, permanent false authority fields, hosted-CI guard and production-recovery refusal. Tests do **not** treat a locally `issued` challenge as proof that some separate protected command never ran.

The dedicated workflow also reruns the merged **30 IPC non-settlement +20 Linux peer-origin +46 local IPC +32 cutover +28 storage-independent +28 SQLite ledger +24 signed-history +22 enrollment +22 AF +20 release Z = 272 inherited tests**, plus Grammar, root-pinned admission and fake RPM guest workflows on the same exact PR head. Only after exact-head checks and independent Nurse 2 review can this test-only milestone be considered a scoped source/CI PASS.

## WATCH OUT FOR

- **Local crash durability is not independent antirollback trust.** SQLite can recover atomic transactions after process death, but the entire local DB and its backups remain in the same restore/compromise domain. A host rollback can make an old consumed challenge `issued` again.
- **A local status is not a signed protected terminal receipt.** Even after a killed process, `consumed` or `issued` is a diagnostic. The requester must not automatically retry an ambiguous protected command on that basis. DOC 6 controls signed Identity command wire ambiguity separately; C5 owns human intent.
- **Exact injected SIGKILL points are test-only.** A real power loss, file-system defect, storage controller flush or malicious admin requires later native independent-custodian recovery testing. SIGKILL after successful SQLite COMMIT does not test power-loss durability.
- **No approved protected root or real host** exists yet. C3e Identity-only witness keys/purpose must not silently become TimeW C5 consent or SwayPX native attestations; DOC 2/C4b and SwayPX retain their producer ownership.
- **Historical reviews:** Nurse 2 has retrospectively scoped-reviewed merged DOC 1 milestones through #2273. Those reviews clear retrospective source-debt, not production acceptance.

## CHECKLIST / NEXT

- [x] Inspect exact `main`, Syntagma rules, local ledger signed verifier, previous crash/restore tests and concurrent DOC 2/C5/Identity/TimeW ownership.
- [x] Build a child-only real SIGKILL trap that reuses the exact existing SQLite writer; add fresh-process recovery reads and whole-DB replay counterexample.
- [ ] Run exact-head CI and verify raw case counts and KVM RPM results.
- [ ] Nurse 2 independently reviews this PR's exact head **before merge**, operator merge disposition separate.
- [ ] Continue local-first development of a guarded service boundary only within C3e scope, not as a production authority.
- [ ] Future **operator-selected** separate hardware/admin/root, authenticated custodian, independently current history, native source/seat, C5 and Sign-In integration; production activation remains HOLD.

## DECISIONS

The operator has authorized **Local Development Ledger first → independent NAS/other-computer trust custodian later** as the development sequence. This milestone does not choose hardware, enroll roots, issue real protected challenges, write production records, change the local machine, activate Sign-In or authorize a merge. **PRODUCTION HOLD.**
