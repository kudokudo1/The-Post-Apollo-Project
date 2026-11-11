# Trash++ // V2h Archive Capacity & Write Limits

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // DOC-compatible development, external; no verified live Hospital session  
ASSIGNMENT // Monitor the V2 SQLite archive's real storage footprint and refuse excessive growth without deleting anything  
PERMISSIONS // GitHub-only branch, draft PR and CI. No host edits, merge, activation or new Burn/Restore permissions.

## IMPLEMENTATION

- Adds `archive_v2_capacity.py`, a **read-only** collector for the private V2 Archive's SQLite database and rollback journal. It reports logical file bytes, allocated disk blocks, the larger (conservative) charged footprint, journal/database breakdown, budget, remaining capacity and current filesystem-available bytes. It refuses symlinks, disallowed ownership/modes, hard links and unexpected WAL/SHM sidecars.
- Preserves the V2a payload quota (512 MiB by default) **and** adds a distinct V2h total charged-footprint budget (768 MiB by default). The policy is fixed and not editable from individual source records, notifications or the Trash widget.
- On a new copy, ArchiveStore applies SQLite `max_page_count` to the **main database** for the writer connection, checks current database/journal footprint and available filesystem headroom before writing, and checks the database/journal footprint again **before commit**. A budget refusal rolls back the copy with `ARCHIVE_DISK_QUOTA`; SQLite `SQLITE_FULL` maps to the same error. No automatic eviction, deletion, compaction or source modification.
- The existing read-only V2 index includes capacity metadata with every page, without reading snapshot payloads or initializing a database when it is absent. The existing Archive UI shows a small `ARCHIVE STORAGE // used / limit MiB // remaining` line. No extra storage button or new window. A full state is colored as an attention condition, not a Delete command.
- Source snapshots retain their exact copy/owner witness checks. V1 managed records, GIO Trash, Camera Cleanup and the two-click Burn system are unchanged.

## HOW TO USE

After separately authorized merge and desktop installation:
1. Open Trash++ > ARCHIVE.
2. Read the storage line below the copy-page navigation: current charged footprint, the 768 MiB default budget, and remaining allowance.
3. SAVE SNAPSHOT / CONFIRM COPY uses the same approved Weather/demo source process. A copy exceeding a budget is refused; prior snapshots remain readable.
4. Use the existing REFRESH to recompute the capacity figures. There is no automatic cleanup or capacity override control.

## VERIFY

Synthetic Python tests cover logical + allocated database/journal bytes; missing database non-creation; full-state reporting; unsafe symlinks/modes; new-copy refusal under a smaller test budget; unchanged previously verified snapshot after refusal; and preexisting over-budget archives remaining readable. Existing read-only page and UI contracts, Camera handoff, preview/confirm snapshot, two-click Burn and managed-bin Burn All must pass CI. No live host writes or destructive operations are performed by this development work.

## WATCH OUT FOR

- The default 768 MiB is an **Archive-specific committed-copy budget**, not an OS-level filesystem quota. SQLite's main database has a page-count ceiling; the journal is checked as part of the measured footprint before commit. SQLite may temporarily allocate journal space *during* a transaction before that check, and unrelated processes can consume disk space concurrently. The filesystem availability check is a conservative preflight, not a reservation against other processes. Do not call this a hard guarantee on every transient filesystem allocation.
- The capacity line measures file footprint, not verified backup recoverability, authenticated metadata provenance or all space consumed by other Post-Apollo services.
- When a store is absent, the reader returns `NOT_INSTALLED` and no capacity data; its absence should not trigger DB creation or repair.
- `max_page_count` protects the SQLite main database for this writer connection only. Any future writer must use the same quota policy; owner-protected APIs cannot silently bypass it.
- No retention/deletion policy is introduced. Even an over-budget archive stays readable; operators must explicitly authorize any later pruning or migration.
- Native Quickshell display at all four chassis sizes and independent security review remain separate acceptance gates.

## CHECKLIST

- [x] V2g merged baseline, GitHub HEAD and competing Trash++ ownership checked
- [x] Shared read-only capacity accounting, owner/link/mode safety checks
- [x] Main database page ceiling plus precommit combined-footprint refusal
- [x] Read-only Archive capacity telemetry and compact UI line
- [x] Synthetic tests for quotas, nonmutation and missing/corrupt cases
- [ ] GitHub CI and any corrections
- [ ] Independent security/native UI review
- [ ] Operator-authorized merge and host deployment

## NEXT

**V2i // Snapshot provenance and integrity metadata.** Define source-owner provenance, snapshot witness and append-only evidence strong enough to explain what was copied and when without claiming full signed authority. Keep actual Restore permissions and retention/Burn authorization separate until source-specific consent contracts exist.

## DECISIONS // RECOVERY

RECOVERY BRANCH // feat/trashpp-archive-capacity-v2h-20261111  
STATE // GitHub draft review, not operator-accepted  
ROLLBACK // Revert only this PR. Existing SQLite snapshots remain; no schema migration, deleted records or chmod. Rolling back the quota policy removes the new write safeguard, so treat rollback as a code decision, not a cleanup operation.
