# Social Organization Manager / Deferred Live UI Acceptance Register v1

STATE: MIXED. Controls 1–5 remain operator-deferred; backup create/list/validate were operator-confirmed working on 2026-11-04. Preserve this register for consolidated remaining acceptance.
PATIENT: kudokudo1/The-Post-Apollo-Project

## Later operator test session

Confirm which exact commit is deployed. Use safe fictional/test company records where changes are needed; do not rewrite real organizations just to test buttons. Observe status, reopen records, and capture any precise errors. Do not restart a live shell without separate approval.

| Control | Later manual test | Expected | Status |
| --- | --- | --- | --- |
| 1. Shared local selection | Switch between two local organizations | Structure and Modifier follow, portfolios remain cross-company | DEFERRED |
| 2. Local search | Search company, branch, portfolio, team, location, link; clear | Same-page record matches and filters, no new menus | DEFERRED |
| 3. Record actions | Show/hide archived and restore a safe test record | Archived records display consistently, confirmations clear | DEFERRED |
| 3b. Archive discovery | Open Organizations, locate ARCHIVE TRAY and its archived count, view archived-only rows | Obvious destination before Search; company, branch, portfolio and unit types clearly named | OPERATOR-REPORTED PROBLEM (2026-11-04), RECHECK AFTER FIX |
| 3c. Red permanent remove | **Only on a disposable archived test record with fresh private backup**, click Remove then Confirm Remove | Red control; two-stage confirmation; linked/child/unbacked records refused; confirmed safe removal persists after Refresh All | DEFERRED, NEVER TEST ON LIVE IMPORTANT DATA |
| 4. Save feedback | Save a harmless test record and reopen | Saving then revision-confirmed Saved, truthful failures | DEFERRED |
| 5. Refresh All | Click once and repeatedly while busy | Seven stores reload, busy protects in-progress writes, results remain | DEFERRED |
| 6a. Backup Now / List Backups | Operator created a backup and viewed the list in the live UI | Buttons created and listed a backup as observed by operator; private file mode not manually inspected | OPERATOR-PASSED (2026-11-04) |
| 6b. Validate Backup | Operator selected the backup and validated it in the live UI | UI completed validation successfully; underlying checksum checks covered by automated tests | OPERATOR-PASSED (2026-11-04) |
| 6c. Restore | Only after separately reviewed crash-safe transaction | Verified rollback/recovery and revision checks | NOT IMPLEMENTED |
| 7. Current Session Activity | Inspect the inline view after save, refresh and backup operations | New events only; no fabricated prior timeline, actor attribution or server audit claims | NOT YET OPERATOR-TESTED |
| 8. Semantic color pass | Scan Close, Cancel, Save, Refresh, typing, navigation, focus | Roles distinguishable by color/glow, unchanged geometry | NOT IMPLEMENTED |

## Status rules

Operator explicitly reported successful live BACK UP NOW, LIST BACKUPS and VALIDATE FOR RESTORE on 2026-11-04. Do not interpret this as a verified data restore, backup decryption, manual Unix-permission inspection, or proof of disaster recovery.

GitHub CI green is technical evidence, not live user acceptance. Do not silently convert a deferred test to accepted. Destructive restore must pass synthetic rollback and collision tests before enabling. Button geometry and pixel normalization remain future independent tasks.

## NEXT

Proceed with bounded functional controls. When the operator elects to test, use this register as a batch without repeated interruptions.

## Archive Tray user evidence // 2026-11-04

The operator provided two live desktop screenshots and reported archived records were difficult to locate. The operator explicitly requested **red permanent removal as distinct from Archive**. The new tray/archived deletion path is a corrective implementation proposal until merged and live-accepted. Do not mark it personally accepted based on source tests. Never use important production company records for a destructive UI test.
