# Trash++ // V2c Read-Only Archive UI

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal lifecycle
ROLE // External DOC-compatible developer; no verified live Hospital registration
ASSIGNMENT // Surface V2 copies safely in the existing Archive menu
PERMISSIONS // GitHub-only code/tests. No merge, host write, live reload or activation.

## IMPLEMENTATION

The existing Archive page remains the central Trash++ inventory. The original
seven filters and legacy GIO/managed-copy writer paths are unchanged.

- archive_v2_index.py reads the fixed V2a SQLite database name **only** inside
  the Quickshell-owned data directory supplied by the caller. It has a single
  index verb, no writer or Burn verbs, and opens SQLite with mode=ro and
  query_only=ON. Missing database returns NOT_INSTALLED without creating it.
- The index returns at most 25 metadata rows per page, with a keyset next
  cursor, total count, and read-only capability envelope. Every V2 row is
  a *copy*, not an original source record. The payload itself is never
  returned or used for discovery.
- Rows are displayed in Archive ALL and COPIES with a V2 COPY prefix.
  Original source rows have a SOURCE prefix; existing V1 managed snapshots
  have a V1 COPY prefix. Current V2 pages are never listed in the Trash
  or Burn modes.
- A small V2 PREV / V2 NEXT rail reuses the existing menu rather than
  opening another window. A stale/malformed index response clears V2 rows
  and displays an error rather than masquerading as a healthy copy.
- The existing record list remains scrollable and clipped. Its viewport
  height is adjusted so the new page rail fits in compact mode.
- Neither the V1 managed-copy backend nor V2a/V2b snapshot writers are called
  from these new controls. V2 snapshot rows offer **no Archive/Trash/Restore/
  Burn buttons**. The existing V1 buttons remain strictly kind-limited.
- V2 data will normally show NOT INSTALLED or zero records until an authorized
  source-specific workflow actually creates separate V2 snapshots. This PR
  does not create a live background copy process or migrate old records.

## HOW TO USE

After separately authorized merge, host synchronization and Quickshell reload:
1. Open Trash++ > ARCHIVE.
2. Existing ALL/SOURCE/HUB filters keep their original behavior.
3. V2 snapshots, if present, appear in ALL or COPIES as [V2 COPY].
4. Use V2 PREV / V2 NEXT to traverse the immutable snapshot metadata pages.
5. The V2 reader never exposes source-delete, restore or burn controls.

The search field filters the V2 rows *on the currently loaded page only*;
a global indexed database search is not yet implemented.

## VERIFY

GitHub CI: Trash regression suite and Meta Apollo Grammar. Synthetic tests:
no-DB non-creation, duplicate-timestamp pagination, private directory and
symlink refusal, corrupted metadata and schema rejection, read-only CLI,
unchanged snapshot database bytes, V2 labels and disabled destructive actions.
Native Quickshell validation at all four chassis sizes is still pending.

## WATCH OUT FOR

- The V2 index is **metadata-only** and explicitly marks payload integrity
  as NOT VERIFIED. A database index read is not equivalent to a verified
  recovery backup.
- V2a's storage design tracks payload quota, not full SQLite disk footprint;
  metadata authenticity and same-user path-race risks need separate review.
- SQLite mode=ro refuses database writes. Hot journal recovery that requires
  writes may fail closed and display a stale error until a trusted owner
  performs recovery. This UI does not perform that recovery.
- The data root is trusted host-provided Quickshell.dataDir, not a directory
  selected by a source row or notification. The Python function is a developer
  interface and is not an independent OS authentication service.
- Newly created archive snapshots may change the source list while paging.
  A full REFRESH restarts V2 pagination from page 1; this is not a frozen
  cross-process snapshot transaction.
- Search is page-local for V2; do not treat a no-match as universal absence.

## CHECKLIST

- [x] V2a merged, V2b merged, current main and open PR owners checked
- [x] Fixed-path read-only SQLite V2 index
- [x] Bounded metadata-only keyset paging
- [x] One-window Archive UI integration and explicit labels
- [x] No new destructive routes
- [ ] GitHub CI and any corrections
- [ ] Independent security/UX review
- [ ] Operator-authorized merge and local install
- [ ] Quickshell native acceptance at compact/medium/large/full sizes

## NEXT

After CI and independent review, native visual testing is required before a
merge/host gate. The next bounded Archive milestones are global indexed search,
trusted production installation of a source-owned V2 copy path (explicit
operator action only), disk-footprint quota monitoring, protected metadata
policies and owner-approved Restore mechanisms. Retention and permanent Burn
receipts must be separate later stages, not a default property of this index.

## DECISIONS / ROLLBACK

No new files get deleted. Reverting this PR removes the V2 read-only index
and UI affordance; the V2a SQLite database and V2b pilot API remain intact.
The old GIO Trash, V1 managed-copy store and Camera Cleanup persist unchanged.
No production activation or merge is authorized by this document.

RECOVERY BRANCH // feat/trashpp-archive-v2c-readonly-ui-20261110
