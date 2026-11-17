# 🏥💜 Trash++ // V3c Separate-UID Synthetic High-Water Fixture

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · Archive Source Authorization
STAFF ROLE // External Hospital-compatible DOC; live Hospital attachment not verified
ASSIGNMENT // Test a distinct Linux owner and SQLite monotonic receipt history with no production authority
SCOPE // Stacked TEST-ONLY PR on V3b, two source/test files plus a dedicated workflow and this runbook

## IMPLEMENTATION

V3b (#1949) remains DRAFT / UNMERGED on its own branch while V3c is created. This V3c PR is intentionally **stacked on V3b** to import its strict verify-only Ed25519 witness contract without duplicating code or altering the unreconciled V3b source. Nothing modifies other Trash U1, V2w/V3a, MACHINE, Connections/C3e or C5 owners.

V3c adds a test-specific SQLite journal owned by synthetic Linux UID `65031` under a disposable private `/tmp/trashpp-v3c-ci-*/authority` directory. The test parent is root-owned, mode 0711; authority directory is owned by `65031`, mode 0700; the SQLite database is single-link 0600 and symlinks or wrong ownership refuse. Synthetic broker UID `65032` cannot access the authority directory or database; a separate process demonstrates the actual kernel denial. Both UIDs must be unassigned; if already in use the test refuses/skip rather than overriding system users.

The authority child verifies signed V3b test witness claims against an independently supplied TEST public root, the **already existing** signed V2w/V2s *fixture observation*, source owner and grant hash. It serializes append under SQLite `BEGIN IMMEDIATE` with `synchronous=FULL`, and atomically records both event history and the latest head. It refuses an incorrect predecessor, a same-counter signed fork, missing/gapped witness sequence, source/grant mismatch, release downgrade, and attempted unrevocation. A repeated **identical** already committed witness is reported idempotently, without consuming a new sequence or granting capture.

Crash hooks force actual `os._exit(93)` before COMMIT and `os._exit(94)` after COMMIT, before a reply. The parent process reopens and inspects the resulting file to verify uncommitted data is absent, committed data survived and a duplicate lost-reply retry is harmless.

**Important limitation deliberately tested:** the fixture's authority/root UID can still replace its OWN SQLite database with a valid older copy. On reinspection this older, internally valid history is accepted by the isolated reader. This is not a secure external monotonic high-water mark. A production design still requires an independent trust domain, tamper-resistant or remotely anchored monotonic storage and a trusted recovery protocol. The test explicitly asserts `authorityOwnerRollbackDetectable=false` and `externallyProtectedMonotonicAuthorityVerified=false` even after successful UID isolation, signature verification and SQLite commit.

Every returned result is `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`, `automaticRetryAllowed=false`, `deleteOriginalAllowed=false`, `safeActions=[]`. No operational ArchiveStore, Quickshell, actual source owner, installed Linux service, human consent, keys or restored records are involved.

## HOW TO USE

No desktop, host or account action. Root-only CI **on an ephemeral Ubuntu GitHub runner**:

```bash
sudo -n python3 -B -I tests/trash/test_archive_v3c_separate_uid_highwater_fixture.py
```

The script creates only disposable synthetic UID directories. **DO NOT RUN ON THE USER'S WORKSTATION**: this requires root and intentionally exercises Linux credentials, intentional process crashes and destructive cleanup of named CI fixtures. The module has no CLI and intentionally requires the exact numeric CI test owner.

The normal all-Trash regression job runs as nonroot, so the V3c UID tests are skipped in that job; dedicated workflow runs them as root and must be checked separately.

## VERIFY

The exact V3c PR head must show its root-only dedicated workflow passing, plus V3b signed witness, V2w floor, V3a readiness and full Trash contracts / grammar. Raw logs should prove actual `os.setuid` kernel broker denial, pre/post COMMIT termination, saved last head, signed replay/fork refusal, refusal of insecure paths, and deliberate old-backup rollback limitation. An unexecuted/skipped root test is NOT a technical pass. Independent NRS-2 review and source-owner approval are still required.

## WATCH OUT FOR

- These are disposable test UIDs and **public test witnesses**. No real operator-controlled separate-UID release authority is installed, no keys are provisioned or stored, and no live signature is accepted.
- SQLite atomic transactions protect against process failure, not rollback of the entire database by the trusted filesystem owner, root, a snapshot restore, or offline storage tampering. V3c cannot claim a protected monotonic release floor.
- V2w Ed25519 signature proves integrity relative to a supplied key, not independently rooted organizational authority. V3b's pinned predecessor is authenticated only within a test instance.
- Power failure, fsync-error injection, independent off-host/worm custody, trusted time, SELinux/ACL, live source-owner permissions, C3e host identity, C5 human consent, production writer freeze, backup and recovery remain untested.
- Production Capture, Restore and Burn remain separately scoped and disabled. Do not modify any live Archive database or wire this fixture as an authorization service.

## CHECKLIST

- [x] Reconcile main, V3b draft, Syntagma and active neighboring owners
- [x] Add isolated, root-only private high-water SQLite test authority under a synthetic Linux UID
- [x] Test real kernel cross-UID denial, signed witness advance/revocation, crash windows and DB owner rollback
- [x] Dedicated workflow and recovery runbook
- [ ] Exact-head CI and raw log inspection
- [ ] Independent Nurse 2 review and source-owner infrastructure design
- [ ] Operator acceptance and stacked PR merge sequencing (V3b before V3c)
- [ ] Real independently controlled monotonic authority, secure key/time custody, C3e/C5 and production approval

## NEXT / DECISIONS

Keep V3c DRAFT and stacked on V3b for independent review. The next REAL authority milestone is not another local SQLite copy: it must establish source-owner-approved separately administered immutable/monotonic witness storage with trusted clock, key management, rollback detection across the authority-owner compromise boundary, and a fail-closed recovery process. That belongs to the actual source/Connections infrastructure owner with explicit operator approval.

Revert the four new V3c files to remove this fixture without modifying V3b, V3a, the existing ArchiveStore, Trash UI, source records or real machine configuration.
