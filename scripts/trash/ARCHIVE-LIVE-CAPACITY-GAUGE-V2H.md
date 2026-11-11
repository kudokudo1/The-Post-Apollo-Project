# Trash++ // V2h-Gauge · Real Archive Capacity Bar

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // DOC-compatible external developer; no verified live Hospital registration  
ASSIGNMENT // Replace invisible 9px text-only capacity line with a real, prominent, data-bound Archive bar  
PERMISSIONS // Scoped GitHub branch / draft PR only. No local host writes, merges, production activation or destructive authority.

## IMPLEMENTATION

- The old illustrative progress bar shown in conversation was **not** part of the Quickshell code. V2h provided only a 13px-tall, 9px-font text line below the Archive page navigation. User's live screenshots exposed the mismatch.
- A new real Archive capacity gauge is placed **directly under ARCHIVE's title and REFRESH button**, before the status/search/filter rows. The old bottom capacity line is removed.
- The real bar's width is bound to `archiveCapacityRatio = clamp(chargedBytes / diskQuotaBytes, 0, 1)`, where `archiveCapacity` is only set after the existing protected read-only SQLite `archive_v2_index.py` successfully returns a validated capacity object.
- `chargedBytes` is the V2h physical/logical database + rollback journal footprint `max(logicalBytes, allocatedBytes)`. The bar has **no artificial minimum fill**, static animation, fake timer, slider or hardcoded example value. 0 used is empty, half used is half filled, full is filled.
- Dynamic labels show measured usage (KiB for less than 1 MiB, then MiB to 2 decimals), configured capacity budget, remaining MiB, and fraction used to 2 decimals. If the store has not been inventoried or the index failed, the track is empty and shows NOT MEASURED / NO DISK INVENTORY / UNAVAILABLE rather than pretending usage is zero.
- Color grammar: cyan for normal, orange at 80% or above, red at 100%. The gauge is read-only and never offers a Burn/Restore/Trash action. Its fill only updates when new real backend measurements arrive via existing Archive index refresh; after confirmed snapshot capture the widget already schedules an index refresh.
- Compact chassis displays a 52px top gauge and hides the redundant bottom Archive disclaimer, keeping scrollable records above a safe minimum. Other chassis receive a 66px gauge and a reduced scrollable list region to keep the header and copy controls accessible. No new window.
- V2h storage and quotas, owner permissions, source records, Camera cleanup, GIO Trash and Burn implementation are unchanged.

## HOW TO USE

After separately approved merge and desktop sync:
1. Open Trash++ > ARCHIVE. The actual capacity bar is now prominently below the heading, not near the bottom edge.
2. A real stored snapshot's measured bytes determine the fill fraction. The same row shows used, limit, remaining storage and used percent. Refuse to claim the bar itself measures system disk usage; it measures **V2 Archive** only.
3. REFRESH recomputes all three Archive inventories, including the protected V2 index. A successful CONFIRM COPY triggers the same V2 index refresh.
4. If the database is absent or the reader refuses, expect an empty bar explicitly marked unavailable instead of a fabricated measurement.

## VERIFY

- JavaScript source-and-binding tests evaluate the exact QML ratio expression at 0, 50%, 75%, 100%, over capacity, invalid denominator and tiny nonzero usage. They validate exact rendered pixel width for 0%, 1%, 50% and 100% without a fake minimum.
- Tests assert that the gauge resides above search/filter rows, uses backend `reply.capacity`, retains fail-closed null behavior, uses cyan/orange/red thresholds, and contains no click handler, backend write or destructive action.
- Existing Python 146+/JS 29+ Trash tests and Meta Apollo Grammar checks must remain green.
- Native four-size visual assessment is still separate. The CI checks bindings and structural constraints but cannot guarantee actual on-host rendering at every pixel density.

## WATCH OUT FOR

- A small archive (for example, 40 KiB used out of 768 MiB) will produce a **very thin** truthful fill, not an artificially enlarged bar. The adjacent numeric used and percentage labels make that visible.
- The figure is Archive-specific, not the disk usage of Quickshell or the entire machine. Database/journal footprint may temporarily change during a transaction; it reflects the last successful index measurement, not a continuous OS monitoring process.
- The configured 768 MiB limit is a software write budget, not an OS-enforced disk quota. We do not change this security limitation in a display-only patch.
- This visual change is intentionally not coupled to V2i provenance; no new snapshot metadata, Restore or Burn permission is added.
- No user's machine has been changed. GitHub code may merge independently but a verified live refresh is required before claiming native acceptance.

## CHECKLIST

- [x] Verify merged V2h baseline and no concurrent open Trash PR at branch creation
- [x] Replace microscopic bottom label with header bar
- [x] Bind width to real backend charged bytes and budget with 0-to-1 clamp
- [x] Add numerical used/remaining/% and meaningful capacity warning colors
- [x] Preserve compact access, read-only semantics and Burn safety
- [x] Add JS executable binding tests and updated Python UI source contract
- [ ] Final GitHub CI and any corrections
- [ ] Independent UI/security review
- [ ] Operator-approved merge and native four-size acceptance

## NEXT

**V2i · Snapshot Provenance and Integrity Metadata.** Once this visual correction is reviewed, implement verifiable source owner, source revision, capture evidence and lineage receipts for immutable V2 copies without expanding Restore/Burn authority. The NEXT milestone is implementation work, not merely another test request.

## DECISIONS / RECOVERY

PR remains draft and unmerged until independent/operator review. No source/backend changes, data migration or chmod. Roll back by reverting this UI/test PR; the V2h capacity backend and all previously stored snapshots remain intact.

BRANCH // feat/trashpp-archive-live-capacity-bar-v2h-ui-20261111
