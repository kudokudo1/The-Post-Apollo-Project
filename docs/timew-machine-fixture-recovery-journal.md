# 🏥💜 MACHINE // Disposable durable-receipt crash experiment

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // External Hospital-compatible DOC, not live Hospital-registered
ASSIGNMENT // Test crash/reply-loss durability and keyed integrity of synthetic metadata receipts
SCOPE // New fixture-only SQLite module, test, isolated CI workflow and this runbook

## IMPLEMENTATION

As of the source baseline, PRs #1898 (source inventory), #1900 (protected destination simulation), #1906 (target readiness), and #1911 (offline unsigned plan/receipt contract) are **merged into main**. This experiment consumes only #1911's immutable plan hash, record IDs and structural transition table. It does NOT open the sealed vault or transfer an actual archive.

`MachineBraveFixtureRecoveryJournal.py` is a small **TEST-ONLY** SQLite receipt journal. It accepts exclusively a disposable private `/tmp/machine-ledger-ci-*/receipt.sqlite3` pathname owned by the current CI UID and mode 0600. Existing parent must be an owned 0700 directory. No arbitrary path, desktop service or production CLI exists.

- Initializes a new SQLite database exclusively with the exact plan SHA-256.
- Uses `BEGIN IMMEDIATE`, SQLite rollback journal mode and `synchronous=FULL` for a sequential fixture writer. Only synthetic UUID, encrypted-record SHA-256, planned transition, sequence and prior MAC are persisted.
- Computes HMAC-SHA256 over the canonical event with a **synthetic, process-supplied ephemeral test key**. The test key is never stored in the SQLite database.
- Validates every event's plan binding, source record digest, predecessor MAC, sequential index and allowed transition on reopen and before a new append.
- Requires the caller's previously observed head (`sequence` + `mac`) before appending. Lost replies, duplicate replays and wrong heads refuse rather than automatically retry.
- With an independently retained test head, a missing valid suffix results in `manual_reconciliation_required`. Without that head, a perfectly valid prefix cannot prove that no signed rows were removed.
- Returns **only** deny-only observations, never a migration approval, client-authentication claim, backup claim, or `restore_allowed` result.

## HOW TO USE

**No desktop control or operator command exists.** GitHub CI runs only the disposable test:

```bash
python3 -B -I tests/timew/test_machine_fixture_recovery_journal.py
```

The test creates a synthetic 0700 temporary directory under `/tmp`, uses fake public-in-repository HMAC material, and destroys the fixture afterward. Two child processes call `os._exit(91)` before commit and `os._exit(92)` after commit/before reply to model actual process death. Never run this test against user files or in a live service.

## VERIFY

Synthetic regression should verify:
- Empty ledger, sequential append, stale-head/invalid transition/conflicting-record refusal.
- Exact plan hash, key and per-entry MAC validation; rejection of edited MAC and sequence.
- A SQLite transaction interrupted **before COMMIT** is rolled back on process restart.
- A SQLite transaction interrupted **after COMMIT but before reply** remains visible, and a retry with the former head refuses.
- Valid-prefix truncation is not detectable from the database alone, but mismatches a caller-held head.
- Unsafe modes, unexpected paths and duplicate initialization refuse.
- Existing #1911 in-memory contract and merged vault/admission-intent/deadline regression pass.

## WATCH OUT FOR

**This is not an installed authenticated recovery service.** The test HMAC key is intentionally public and is not an independently protected signing identity. Anyone with that key can forge a complete ledger. An HMAC chain is not an independently anchored anti-rollback floor; a valid-prefix truncation can remain cryptographically valid without an authenticated external head.

SQLite FULL synchronous rollback journal supports an atomic *fixture transaction*, not an atomic filesystem+database transfer. No real ciphertext publication, power loss, disk failure, filesystem fsync failure, service identity, trusted path ancestry, SELinux/ACL, verified backup, or custody signing has been tested here. The fixture path constraints are an accident guard, not protection against an attacker sharing the CI UID.

The ordinary user vault remains same-UID accessible until separately authorized migration. The protected archive broker remains DENY-ONLY. C3e still owns trusted process/active-seat witnesses, C5 still owns one-use human authorization. No step supplies either, and no production archive access is granted.

## CHECKLIST

- [x] Reconcile Syntagma, current `main`, merged MACHINE predecessors and concurrent PR ownership
- [x] Add disposable SQLite receipt journal and fixture-only keyed chain
- [x] Test process crashes before/after commit, stale head, tamper and unsigned floor limitation
- [ ] Verify exact-head GitHub CI and independent Nurse 2 review
- [ ] Operator merge/acceptance decision
- [ ] Independent protected signing authority, durable external revocation/rollback floor
- [ ] Transactional protected transfer custody, backups, C3e/C5 integration and safe Brave restore

## NEXT / DECISIONS

Keep this as a separate **DRAFT** PR for review. No merge or local activation without approval. A future, separately authorized design would need a protected release witness/key enrollment, externally anchored high-water mark and coordinated filesystem+DB recovery; no production migrator should be inferred from a synthetic SQLite fixture. No local machine files, services, Brave profiles, Quickshell or user archives changed.
