# 🏥💜 Trash++ U10 // GIO Restore Identity and Late-Collision Hardening

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration unverified  
ASSIGNMENT // Harden **Trash-owned** GIO Restore's stale-item/metadata check and prove real no-force destination behavior with disposable runner files  
BASE // `707ab22341303544d512a34ef3728bfd556d70ba`  
SCOPE // `scripts/trash/trash_cli.py`, Trash unit tests, U9 disposable-runner fixture, this document. No Camera/Media/Archive/Clock changes.

## IMPLEMENTATION

The existing `trash_cli.py restore URI ORIGINAL` action already reindexes GIO using `gio trash --list`, requires exact `[trash URI, original path]` match and refuses `os.path.lexists(original)`. However `gio trash --list` does **not** disclose a second timestamp or inode witness. A previously displayed URI/name could be reused, or the entry could change between the index and actual move.

U10 adds a **deny-only preflight** to the existing file Restore path:
1. After the original exact-item GIO inventory match, reject an occupied original destination immediately.
2. Query the selected GIO item directly with `gio info --attributes=trash::orig-path,trash::deletion-date,id::file,standard::type,standard::size URI`. Require `trash::orig-path` to agree with the indexed source tuple and at least one secondary identity witness (`trash::deletion-date` or `id::file`). Duplicate, oversized, invalid or unreadable metadata fails closed; no restoration action is attempted.
3. Read the GIO listing **again**, requiring the exact item tuple remains present. Query its metadata **again** and compare the entire collected witness tuple. Changed details refuse with `RESTORE_SOURCE_IDENTITY_CHANGED`.
4. Recheck destination occupancy immediately before the original `gio trash --restore URI` command. No `--force`, no direct path-based move, no raw Trash directory scan.
5. The existing GIO command performs the final move. Its upstream implementation calls `g_file_move(..., G_FILE_COPY_NONE)` when `--force` is omitted. This is the *actual* last-moment no-overwrite behavior; Python's pre-check does not claim atomicity. Source: https://fuchsia.googlesource.com/third_party/github.com/GNOME/glib/+/refs/tags/2.80.3/gio/gio-tool-trash.c

The existing cross-widget `reviewId` and index revision stay unchanged, as do all Camera one-use plans, managed-copy Restore, file Burn, Burn All, Archive and source-owner state. The metadata fields are **not** exposed as a new authorization token; they are only checked inside the Trash backend. No broad filesystem authority is added.

## HOW TO USE

After a separately approved review/merge and authorized local code update, the existing UI remains unchanged:

**Trash++ → TRASH → FILES → RESTORE**.

Stale/reused GIO source entries or missing mandatory metadata now return an explicit error and require a new fresh review; neither source nor destination is deleted by a refused operation. The existing no-force GIO backend retains the final no-overwrite boundary.

## VERIFY

- `tests/trash/test_gio_restore_identity_u10.py` supplies synthetic changed-source metadata, missing/duplicate/oversized attributes, stale second inventory, late destination appearance and no-`--force` command sequence.
- The U9 real-GIO runner fixture is extended to inject one disposable sentinel **after** `trash_cli.item_action()`'s final destination check, immediately before the actual `gio trash --restore` subprocess call. The runner must observe a failed no-force move and unchanged sentinel, plus the same still-trashed item, before removing **only the disposable sentinel** and completing byte-identical Restore and stale replay verification.
- All existing Trash Python and Node tests, real GIO U9 step and Meta Apollo Grammar must be green at exact PR HEAD. Report exact counts only after raw CI inspection.
- CI uses private GitHub runner HOME/XDG and GVfs/D-Bus; no host/Camera operation or user data touched.

## WATCH OUT FOR

**This is not an atomic source identity proof.** Another actor could replace the URI/metadata after the final check. The observed `id::file` and `trash::deletion-date` are provider-supplied data, not cryptographic identity or a kernel lock. The original UI tuple can still be reused before entering the backend; U10 cannot retrospectively prove its contents were the same at UI-render time.

**GIO may differ across mounts/providers.** A backend that does not expose suitable metadata will now refuse Restore, even if its previous listing worked. Source-owner/user acceptance and a documented compatibility route would be needed before any wider deployment claim. Do not silently fall back to unsafe metadata-less Restore.

The **no-overwrite behavior** comes from GIO's final move without `--force`; Python's two `lexists` checks alone do not prevent a racing destination. Directory symlink swaps and hostile GIO service behavior are not solved by this PR. The proof is one disposable local runner filesystem. No Burn, Empty Trash, cross-owner file deletion or protected Archive write authority is introduced.

## CHECKLIST

- [x] Syntagma/Hospital/permissions and current GitHub ownership preflight
- [x] Upstream GIO `G_FILE_COPY_NONE` no-overwrite semantics inspected
- [x] Add repeated exact GIO source metadata and reindex preflight to Trash-owned Restore
- [x] Add pure synthetic adversarial tests
- [x] Extend CI-only real GIO fixture to inject late destination collision
- [ ] Exact-head CI, real injection receipt and any test fixes
- [ ] Independent Nurse 2 security review and operator merge approval
- [ ] Post-merge CI and any explicitly authorized native compatibility acceptance

## NEXT

After exact-head tests, request Nurse 2 independent review. If metadata behavior is insufficient across the operator's mounted Trash providers, open a separate source-owner compatibility design instead of weakening the check without review.

## DECISIONS

Draft implementation only; no PR merge, local machine mutation, Quickshell reload, actual user file move, protected Archive activation or broader GIO authority. This change is limited to Restore: no `--force` or Burn path was added. Recovery is closing this unmerged branch/PR or reverting the scoped commit if merged later.
