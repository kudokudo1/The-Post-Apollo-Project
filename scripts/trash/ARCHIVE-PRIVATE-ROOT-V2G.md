# Trash++ V2g // Private Archive Root Live Repair

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal resource lifecycle
STAFF ROLE // DOC-compatible external developer; no verified live Hospital registration
ASSIGNMENT // Fix live `COPY REFUSED // ARCHIVE_ROOT_UNSAFE` while preserving database security and snapshot visibility
PERMISSIONS // Repository-only draft PR, tests and documentation. No host writes, chmod, Quickshell reload, merge or production activation.

## IMPLEMENTATION

The live failure was produced by passing Quickshell.dataDir straight to the strict V2a SQLite writer. ArchiveStore requires its *actual database directory* to be owned by the current UID with no group/other access (0700). Quickshell.dataDir itself is a shared settings/data parent and can be 0755. The preview succeeded because it was read-only; confirmed capture was refused at ArchiveStore's directory check.

- Introduces `scripts/trash/archive_v2_location.py`, a shared location selector used by **both** the confirmed snapshot writer and the read-only search/list index.
- For a safe, owned, **non-group/world-writable** Quickshell.dataDir, the writer creates a fixed `trashpp-private-archive-v2/` child at mode 0700 on explicit, witness-verified capture only. The SQLite database and rollback journal remain inside that private directory.
- Read-only preview, Archive search and an absent index do **not** create the child or database. The reader returns `NOT_INSTALLED` until a valid private store exists.
- Group/world-writable parent directories, symlink roots/children, unexpected child modes/ownership and path traversal fail closed. Existing private directories are **not chmodded or replaced**. No arbitrary directory is taken from a source record.
- If a V2 SQLite database already exists directly under an *old, private 0700 root*, that private location stays active. If an old database exists under a less-private root, the system refuses instead of silently reading, overwriting, hiding or migrating its bytes. Two root locations simultaneously also fail closed.
- No change to existing source-owner readers, V1 managed copies, GIO/Camera Trash, Restore/Burn confirmation, Quickshell source fields, or SQLite storage schema.

## HOW TO USE

After separate authorization of merge and host installation:
1. Open Trash++ > ARCHIVE.
2. Select an approved source row and click SAVE SNAPSHOT.
3. After SOURCE CHECKED, click CONFIRM COPY. The new V2 database is placed under the private Trash++ child directory, leaving Quickshell.dataDir's own permissions unchanged.
4. The existing Archive search/index reads that same private child, and the saved read-only snapshot appears under ALL or COPIES.

Do **not** manually run chmod or alter Quickshell.dataDir to resolve this error. The parent may legitimately hold other modules' files.

## VERIFY

New synthetic tests reproduce an owned 0755 Quickshell parent, prove preview/index are noncreating, verify successful confirmed copy to a 0700 child, cross-check reader visibility, and verify source bytes and parent mode do not change. Additional tests cover private legacy continuity, unsafe legacy refusal, symlink/unsafe child, group-writable parent, path traversal and ambiguous database roots. Existing complete Trash Python and Camera/snapshot/Burn JavaScript CI must still pass.

A GitHub CI success is not a live host verification. Operator's next visual test confirms whether this fixes the actual data directory permissions and whether newly saved records appear.

## WATCH OUT FOR

- The observed refusal code alone does not reveal whether the live root is 0755, a symlink, group-writable or owned by another UID. This repair supports the *shared but owned and not group/world writable parent* case without weakening 0700 database security. If the live parent has a different unsafe property, do not bypass the refusal; inspect the exact mode, owner and real path read-only.
- No automated data migration is included. A preexisting SQLite file in an insecure parent remains untouched and intentionally blocked until a separately approved safe migration.
- Snapshot payload quota still differs from actual SQLite disk footprint and does not constitute a full backup/recovery guarantee.
- The underlying writer checks root and file permissions at process time. The same-UID hostile process and TOCTOU threat model has not been expanded in this repair.
- No native four-size Quickshell runtime verification or user visual acceptance is claimed from CI alone.

## CHECKLIST

- [x] Recovered live screenshot error and merged V2f GitHub baseline
- [x] Shared private directory placement for reader and confirmed writer
- [x] Preserve private legacy snapshots, no automatic chmod/migration
- [x] Synthetic regression for shared 0755 Quickshell parent and unsafe roots
- [ ] GitHub CI results and corrections
- [ ] Independent security/UX review and native visual test
- [ ] Operator-authorized merge and host deployment

## NEXT

Review CI, fix any failures, request independent review. After separately authorized merge/deploy, rerun the user-observed SAVE SNAPSHOT > CONFIRM COPY operation; verify receipt and Archive listing. If the refusal persists, collect owner/mode/path of Quickshell.dataDir read-only before widening scope.

## DECISIONS / RECOVERY

BRANCH // fix/trashpp-private-archive-root-v2g-20261111
PR // draft, no merge or activation authority
ROLLBACK // revert this PR. It creates no migration; any separately created private V2 SQLite file must be preserved unless the operator explicitly requests removal.
