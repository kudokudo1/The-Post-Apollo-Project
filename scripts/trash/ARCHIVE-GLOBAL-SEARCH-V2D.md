# Trash++ // V2d Global V2 Archive Search

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
ROLE // DOC-compatible external worker, not verified live Hospital-registered
ASSIGNMENT // Search all immutable V2 snapshot metadata, not only current page
PERMISSIONS // Repository source/test only; no local desktop writes, merges, activation, or destructive authority

## IMPLEMENTATION

- Extended existing fixed-path, read-only `archive_v2_index.py` with a bounded 80-character metadata search parameter, rather than introducing another database or scanner.
- The search spans all V2 stored snapshot records, not just the current 25-row page. It searches display labels, owner IDs and resource IDs using SQL parameter binding and a literal substring comparison. Search input never becomes SQL syntax or an arbitrary filesystem path.
- Matching results are counted across the V2 database and returned in existing 25-row keyset pages. Count and page are read under one SQLite read transaction for consistency within each request.
- Existing `mode=ro`, `query_only=ON`, missing-DB refusal, metadata-only results and disabled V2 destructive actions are unchanged.
- The existing Archive header gains a compact `FIND V2` action; pressing Enter in Archive search does the same. Typing without pressing Find continues to filter V1/current-source records locally but hides previously loaded V2 results until the new V2 query is explicitly applied.
- V2 PREV/NEXT carry the applied query. Editing the search field disables V2 pagination until the next Find, preventing a previous search's cursor from being used for a different query.
- Existing Archive seven category filters remain. V2 data remains eligible for ALL and COPIES only, never Trash/Burn.
- No V2 snapshots are created by viewing or searching. V1 records, Camera, GIO Trash, owner writers and all Burn controls remain unchanged.

## HOW TO USE

Once independently approved, merged, installed, and tested on the host:
1. Open Trash++ > ARCHIVE.
2. Enter a keyword in the existing search field, then click FIND V2 or press Enter. This searches *all stored V2 metadata*.
3. Use V2 PREV / V2 NEXT to navigate matched pages of up to 25 records.
4. Clear the field and click FIND V2 to return to all V2 copies.
5. The existing REFRESH also applies the current V2 search while refreshing the legacy inventories.

The search is metadata-only. It does not search contents of archived payloads, original files, or protected Hospital/Finance/Identity records. SQLite built-in lower() provides ASCII case-insensitivity only; search is not full-text indexed and may scan metadata rows as the database grows.

## VERIFY

Synthetic tests cover many-page matches across owners, literal percent and underscore, SQL injection strings, query-length and control-character refusal, read-only CLI, source-byte non-mutation, and query-scoped page navigation. Re-run existing Python Trash, Camera Cleanup, Burn confirmation and grammar CI.

## WATCH OUT FOR

- V2 metadata listings explicitly mark payload integrity as unverified. Content checksums are verified only by the separate owner-approved verification API, not by a search.
- A query is a *visibility filter*, not retention or deletion permission.
- Pagination is consistent within one database read transaction, not across consecutive page requests while new records are inserted. Re-run FIND V2 to obtain a fresh count.
- Matching uses a simple SQLite substring scan, not FTS. Before supporting truly huge archives, add a reviewed search index and query-rate limits. Retain source owner privacy checks.
- Native compact/medium/large/full Quickshell acceptance and independent security review are required before relying on the UI.

## CHECKLIST

- [x] Re-check merged V2c and concurrent Trash++ PR ownership.
- [x] Parameterized, bounded global metadata search.
- [x] Explicit FIND V2 interaction and query-scoped paging.
- [x] Existing read-only/destructive boundaries preserved.
- [ ] GitHub CI and correction of any failures.
- [ ] Independent security and native UI review.
- [ ] Operator-authorized merge, local installation, and runtime acceptance.

## NEXT

After CI and independent review, implement trusted owner-mediated *explicit*
snapshot creation into V2 (first Weather/demo only), storage footprint quota
assessment, and protected metadata policy. Restore, retention, full Burn
receipts and protected owners remain separate assignments and approvals.

## DECISIONS / RECOVERY

Branch: `feat/trashpp-archive-v2d-global-search-20261110`.
Rollback: revert only this PR's changes to the read-only index, Archive QML,
tests and documentation. V2a snapshots and V1/GIO stores remain untouched.
No merge or live host action performed by this assignment.
