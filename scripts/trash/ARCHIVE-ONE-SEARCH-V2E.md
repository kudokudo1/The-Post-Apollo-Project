# Trash++ // V2e One Archive Search

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal lifecycle
STAFF ROLE // External DOC-compatible development
CONNECTION // No verified live Hospital registration
ASSIGNMENT // Replace temporary V2-specific search control with the existing Archive search field
PERMISSIONS // GitHub branch/PR only; no local desktop, production activation or merge authority

## IMPLEMENTATION

- Removes the temporary FIND V2 button from Trash++ > ARCHIVE. There is exactly one user-facing Archive search input.
- Typing filters the already-indexed source and managed-copy rows without modifying the source. Pressing Enter in the existing field submits the same query to the global read-only SQLite copy index implemented in V2d. This avoids an extra search button or an extra window.
- Preserves the internal V2 database boundary and query-scoped keyset pagination, but the operator-facing pager now reads PREVIOUS/NEXT and READ-ONLY COPIES, not storage-version labels. The pager still advances **only the read-only snapshot copies**; source and managed-copy rows stay present across pages.
- Displays [SOURCE], [MANAGED COPY], and [READ-ONLY COPY] instead of V1/V2. These are permission distinctions: only already-authorized managed copies offer existing Trash/Restore/Burn flows. The immutable read-only index offers no destructive routes.
- Displays the count of rows presently visible rather than a misleading sum of inventory lengths and expands source/read-only rows into otherwise unused compact space.
- Fixes the already-merged V2d Camera handoff CI fixture by supplying its existing Archive search text property and asserting that this text survives page navigation. This is a test-harness correction, not a change to Camera cleanup operations.

## HOW TO USE

After separate operator approval of a merge and local installation:
1. Open Trash++ > ARCHIVE.
2. Type a search term in SEARCH ARCHIVE // PRESS ENTER.
3. Press Enter to search read-only copies throughout the SQLite database, as well as the source and managed-copy rows already loaded in the widget.
4. PREVIOUS/NEXT pages through the matching **read-only copies**. Source and managed-copy rows are not individually database-paged.
5. Clear the input and press Enter to restore all read-only copies. REFRESH remains the explicit inventory refresh.

## VERIFY

GitHub workflow runs are the CI source of evidence. Expect the Python Trash tests plus the three JS suites, especially Camera hosted-cleanup handoff and the Burn click/confirmation tests. This branch makes no change to V1/V2 SQLite storage schemas or deletion backends.

## WATCH OUT FOR

- There is one *search field*, but V1 source/managed rows are currently bounded inventories filtered locally while read-only SQLite snapshots are searched globally. Their pagination remains different by design. This is not yet a globally sorted, truly database-backed index of every resource.
- Searches over read-only copies are metadata-only, not payload-content search and not verified backup recovery.
- Status messages may still mention internal service states for diagnosis; user-facing labels do not expose storage version numbers.
- Automated source/CI tests do not establish compact/medium/large/full live Quickshell visual correctness.
- If an existing read-only copy search is in progress, Enter may need to be pressed again when it finishes; no overlapping subprocess is launched.

## CHECKLIST

- [x] Current main and PR ownership rechecked
- [x] Temporary version-specific button removed
- [x] One existing search field for all Archive rows, Enter submits SQLite search
- [x] Neutral navigation labels and explicit permission labels
- [x] Compact actionless-row space improvement
- [x] Merged V2d Camera test-harness omission addressed
- [ ] Final GitHub regression CI pass
- [ ] Independent review and native four-size visual acceptance
- [ ] Operator-authorized merge and desktop deployment

## NEXT

Review the full CI evidence and any failures, then perform independent security/UX assessment and native visual approval before landing. Later work can unify global paging across all source-owned indexes and introduce separately approved explicit snapshot creation, quotas, Restore and Burn receipts.

## DECISIONS

No new source writer, user-data migration, Archive copy creation, Restore, Burn or arbitrary path authority. PR must stay draft and unmerged pending review. To rollback, revert V2e UI, tests and documentation; existing V2d database search and the previous read-only snapshot backend remain unchanged.

RECOVERY BRANCH // feat/trashpp-unified-archive-search-v2e-20261110
