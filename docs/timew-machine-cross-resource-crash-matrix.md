# 🏥💜 MACHINE // Synthetic Cross-Resource Crash Matrix

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // Hospital-compatible external DOC; live Hospital registration unverified
ASSIGNMENT // Exercise the interrupted boundary between ciphertext publication and durable recovery evidence
SCOPE // New TEST-only integration script + standalone workflow + runbook; no production migration code

## IMPLEMENTATION

MACHINE PRs #1898, #1900, #1906, #1911 and #1915 are merged to main, but the **exact-head GitHub Actions for #1915 remain queued without results** as of this branch's creation. A repository-wide Actions query showed 123 queued runs. This change is isolated in a new DRAFT PR; it does not treat #1915 as technically certified or modify its merged implementation.

The test imports the **existing** #1900 disposable `fixture_transfer`, #1911 read-only source/target metadata contract, and #1915 SQLite fixture receipt journal. Under sudo on an ephemeral GitHub Ubuntu runner, root creates private source/destination directories with three unassigned synthetic numeric UIDs and a separate private fixture SQLite database. All records have STRUCTURALLY VALID **FAKE** AES-GCM envelopes; no live keys, browser history or user files are involved.

For each scenario, the child process is genuinely terminated (`os._exit`) or an existing injected rollback is exercised. The parent reopens the SQLite journal and inspects filesystem state:

| Boundary | Published record | Leftover staged file | Committed fixture receipts | Classification |
| --- | --- | --- | --- | --- |
| Crash before transfer | No | 0 | 0 | Manual hold |
| Crash after staged bytes | No | 1 | 0 | Manual hold |
| Crash immediately after hardlink publish | Yes (link count 2) | 1 | 0 | Manual hold |
| Crash after complete copy, before journal | Yes | 0 | 0 | Manual hold |
| Handled injected failure after publish | No (rolled back) | 0 | 0 | Manual hold |
| Crash before SQLite COMMIT | Yes | 0 | 0 | Manual hold |
| Crash after SQLite COMMIT, before response | Yes | 0 | 1 (staged) | Manual hold |
| Completed synthetic phases | Yes | 0 | 3 (observed) | Synthetic consistency only |

Source file bytes, inode, ownership and mode and the preexisting destination sentinel are verified unchanged in every scenario. One scenario reruns #1900's real kernel denied-access checks for browser and unrelated UIDs. A committed-but-unanswered stage cannot be silently retried from the old journal head.

Critically, an independently valid destination record can cause #1911's `all_records_observed` even with **zero committed journal receipts**. The new CI fixture explicitly captures this gap. It requires a manual hold and never treats such an inventory observation as an authorized transfer. After complete synthetic phases, the fixture additionally deletes the published record and verifies a manual hold instead of continuing.

The result does not upgrade or weaken existing production code. The cross-boundary classifier exists **only in the disposable test**, as a future recovery design requirement. No code copies personal archives or grants a protected host access.

## HOW TO USE

**No TimeW UI or workstation action.** GitHub CI tests the isolated synthetic script only:

```bash
sudo -n python3 -B -I tests/timew/test_machine_cross_resource_crash_matrix.py
```

Do not run this on the workstation; it deliberately uses root, numeric Linux UIDs and destructive cleanup restricted to disposable CI directories. The CI workflow also reruns the independent transfer, journal, metadata and deny-only request tests. Do not move the test's internal `fixture_transfer` into production.

## VERIFY

Checks must pass on the **exact PR head** before technical success is reported. A GitHub queue delay is neither success nor failure. Independent Nurse 2 review is also required.

This is a **process-exit** experiment, not a full host power-failure, fsync-error, storage corruption or concurrent attacker test. Child exits occur at deterministic boundaries; crash-uncertain outcomes are held for manual investigation. GitHub CI in an ephemeral runner is the only intended execution environment.

## WATCH OUT FOR

- #1915 merged without exact-head workflow completion. The three original runs are still queued as of this checkpoint; independent Nurse 2 post-merge audit is not recorded.
- SQLite COMMIT and `link` publication are two **independent durability domains**. No single atomic operation combines them. An external durable authority/floor and strictly reviewed recovery procedure are still required.
- The synthetic journal uses a source-visible HMAC key. It proves test-level integrity only, not an independently trusted signer, client identity or audit authority.
- Filesystem mode/isolation does not prove SELinux/ACL policy, independently signed custody, encrypted backup validity or user approval.
- C3e owns live signed host/process/seat evidence. C5 owns one-use human consent. This test supplies neither and keeps the protected metadata broker DENY-ONLY.
- Final user acceptance is distinct from technical CI completion. This PR is not an authorization to install a service, migrate/delete archives or restore Brave windows.

## CHECKLIST

- [x] Reconcile Syntagma, current main and prior merged MACHINE ownership
- [x] Add isolated eight-window process crash matrix against the existing test fixture
- [x] Assert source and preexisting sentinel preservation, ledger states and explicit manual holds
- [x] Add standalone dedicated workflow without editing any other worker's CI
- [ ] Exact-head CI on this PR and #1915; investigate failures
- [ ] Independent Nurse 2 security review and operator merge decision
- [ ] Design externally anchored, signed service custody and crash-safe real migration with backup
- [ ] Integrate C3e live host/seat, C5 one-use consent and authorized multi-monitor Brave restore

## NEXT / DECISIONS

Keep this as an independently reviewable **DRAFT** PR. When GitHub runners resume, resolve any test failures before merge review. The next implementation after technical acceptance should be a reviewed **fail-closed cross-resource recovery contract** that represents inconsistent or orphaned states without deleting or retrying them. This test is not the authority granting any action.

No production authorization, installed service, user archive, Brave profile, Quickshell, local checkout or live Hospital attachment was modified.
