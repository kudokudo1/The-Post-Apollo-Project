# 🏥💜 Trash++ U10b // Secondary GIO Identity Evidence, Compatibility-Safe

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle · GIO Restore  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration unverified  
ASSIGNMENT // Add optional GIO secondary identity comparison to **merged U10** `restore-reviewed` without replacing reviewed revisions or post-Restore checks  
BASE // `main 0d5a84517562b0a8ae4eb898f60faba738a8010f`  
LEGACY REFERENCE ONLY // `feat/trashpp-u10-gio-restore-identity-20261117` at `ad6922fd`, **do not merge directly**

## IMPLEMENTATION

U10 PR #2030 has already merged at `2e425badd9410f5e97ce65ed3f6dceabf5377f6f`. Its **existing** reviewed command uses UI index revision and exact GIO row token, double fresh GIO listings, destination checks, GIO's unchanged `trash --restore`, and a checked post-Restore inventory. U10b extends only that established command, preserving all seven U10 safeguards and the legacy CLI entrypoint unchanged.

A new source-only `_restore_metadata(gio, row)` requests at most one selected item's GIO attributes: `trash::orig-path`, `trash::deletion-date`, `id::file`, `standard::type` and `standard::size`. It parses only recognized fields from the `attributes:` section, limits the output to 32 KiB, rejects duplicates/malformed values and an explicitly reported original path that differs from the reviewed source. A successful reading yields a deterministic witness tuple. It is **provider data**, not an inode lock, proof of byte identity or access credential.

After U10's first approved full-index check and vacant-target check, U10b samples the selected item's metadata. After U10's second complete index/review check, it samples metadata again and compares both witnesses; if they differ, `RESTORE_SOURCE_METADATA_CHANGED` refuses the operation **before launching GIO Restore**. U10's last destination `lexists` check, unchanged no-`--force` GIO command, and post-state verification still run in their original order.

### Compatibility decision

**Secondary GIO attributes are not mandatory on every storage provider.** Some GVfs/mount implementations omit `trash::deletion-date`/`id::file`, return only type/size, or refuse `gio info`. For any such provider, an unavailable metadata sample yields no additional identity claim; both samples must agree (both unavailable or the same available fields). The existing **mandatory** U10 row/revision checks and post-Restore result verification remain active, so an unsupported provider is not newly denied *solely* for omitting optional metadata.

A source mismatch in any **reported** `trash::orig-path`, any observable metadata change between reads, duplicate or oversized reported metadata fails closed. Temporary metadata loss between an available first sample and unavailable second sample also refuses; the user must refresh/retry deliberately after inspection.

The successful `restore-reviewed` receipt adds `metadataWitness: observed|unavailable` and `secondaryIdentityObserved: bool`; the latter is true only when `trash::deletion-date` or `id::file` was observed. These do **not** certify identity or filesystem atomicity. Even stable provider metadata can be reused, forged by a provider, or swapped after the last check. Missing metadata does not silently get reported as verified.

## HOW TO USE

After separately approved merge and authorized workstation synchronization: **Trash++ → TRASH → FILES → RESTORE** as before. No new UI control, no manual tokens, and no desktop service installation. On `RESTORE_SOURCE_ORIGINAL_CHANGED`, `RESTORE_SOURCE_METADATA_CHANGED` or `RESTORE_METADATA_MALFORMED`, refresh and inspect the GIO item rather than automatically retrying.

## VERIFY

- `tests/trash/test_gio_secondary_identity_u10b.py` covers provider presence/absence, reordered output, weak type/size-only evidence, source-path swap, duplicates/oversized output, between-inventory metadata swap, sample loss, and the existing reviewed CLI path with both supported and unsupported providers.
- The existing **private U9 GVfs+DBus runner** is extended to inject a disposable target **immediately before the actual `restore-reviewed`'s final `gio trash --restore` subprocess**. The real GIO move must refuse to overwrite the late destination, preserve the still-trashed item, and then allow the original disposable bytes to be recovered with the reviewed CLI.
- The runner emits `lateCollisionPreserved:true`, `metadataCompatibilityMode` and `secondaryIdentityObserved` without exposing paths or original user data.
- Full exact-head Trash Python/Node/real-GIO CI and Grammar must be checked before claiming PASS. The metadata field presence is assessed from the runner's real returned result, not guessed across platforms.

## WATCH OUT FOR

This is additional observable drift protection, **not** atomic compare-and-restore. The URI and GIO metadata can change after the final observation; a malicious provider can lie. The true no-overwrite check comes from GIO's provider move without `--force`, whose cross-provider atomicity and mount semantics are not proven here. A provider returning no useful metadata receives U10's original guarantees, no new secondary identity guarantee.

The late-collision experiment runs only on a temporary GitHub runner file; no Camera controller, personal files, Burn/Empty Trash, protected Archive, MPD, remote sync or local Fedora state are touched. The original U10 post-restore `verified` means observed path/list state, not verified bytes for arbitrary data. The runner alone hashes its own disposable file.

## CHECKLIST

- [x] Read canonical Syntagma and recheck current GitHub main, U10, old branch and open ownership
- [x] Create a **fresh branch from current merged main**, not merge the stale 5-ahead/46-behind U10 identity branch
- [x] Add optional secondary GIO metadata comparison within merged U10 `restore-reviewed`
- [x] Add negative and cross-provider-missing synthetic tests
- [x] Extend **new reviewed route** real-GIO late collision CI fixture
- [ ] Exact-head GitHub tests and real-provider compatibility evidence
- [ ] Independent Nurse 2 review, operator merge approval and post-merge verification
- [ ] Any wider filesystem/provider atomicity guarantee requires separately scoped design and real tests

## NEXT

Verify actual runner `gio info` attribute behavior and test pass/fail, repair only concrete U10b regressions, then submit the small draft PR for independent NRS-2 review. Do not merge the legacy branch or modify source-owned Camera, protected Archive or user-host files.

## DECISIONS

Compatibility-safe optional witness, explicit observational receipt, unchanged mandatory U10 controls. This draft grants no new filesystem operation or permission. No merge, production activation, local workstation write or live Hospital registration. Rollback: close the unmerged PR and retain merged U10 unchanged.
