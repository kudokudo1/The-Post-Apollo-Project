# 🏥💜 Trash++ U8 // Media Deletion-Path Inventory and Owner Boundary

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration unverified  
ASSIGNMENT // Read-only Media operation inventory, protective source contracts, no Media-owner modifications  
BASE // `main 65dd052c5385093a6005441fd6272736e08d7885`  
SCOPE // `scripts/trash/media_delete_inventory_u8.py`, `tests/trash/test_u8_media_delete_boundary.py`, Trash CI and this document only.

## IMPLEMENTATION

U5 Gallery, U6 Cleanup queue and U7 Desktop screenshot review were merged in #1986. The operator reported **5/5 native preview/UI acceptance checks passed** (recorded at #1986 comment 6952246766). Their live GIO move-and-Restore path with a disposable file remains **not yet verified**; never confuse this with the Media handoff.

U8 does **not** introduce a new TRASH button. Instead, its read-only inventory makes the distinct Media effects explicit:

| Path | Operation | Concrete effect | U1 universal GIO Trash eligible? |
| --- | --- | --- | --- |
| `scripts/media/headless_mpd.py` | `MpdBackend.remove(song_id)` → MPD `deleteid` | Removes a numeric MPD **queue entry**, not its referenced source file | **NO** |
| `scripts/media/media_controller.py` | `dispatch("queue_remove")` | Validates numeric queue ID; rejects the currently active MPD track (`ACTIVE_TRACK`); calls backend remove | **NO** |
| `scripts/media/headless_mpd.py` | `MpdBackend.clear()` → MPD `clear` | Clears MPD playback queue; not exposed through current controller `dispatch` | **NO** |
| `scripts/media/media_intent_store.py` | `IntentStore.save` | Atomically replaces `$XDG_STATE_HOME/post-apollo-media/controller-intent-v1.json`; removes any residual private `.intent-` temporary file | **NO** |
| `scripts/media/media_controller_server.py` | `path.unlink()` | Removes a stale user-owned controller Unix socket under `$XDG_RUNTIME_DIR/post-apollo-media/` and unlinks only bound inode on shutdown | **NO** |
| `widgets/MediaDeckW.qml`, `widgets/MediaDeckBrowserControls.qml`, `modules/Mediaplayer.qml` | Hi-Fi controls/transport | No generic file TRASH/BURN/DELETE review control exposed in surveyed panels | **NO** |
| `scripts/media/radio_stream_relay.py`, directory and YouTube catalogs | In-memory or network media refs | No owned local music-library deletion backend identified in the audited source family | **NO** |

The current `media_controller_cli.py queue-remove QUEUE_ID` talks to the controller's owned MPD queue. The word `deleteid` is MPD's queue protocol, **not** the `gio trash` filesystem API. Routing it through an arbitrary path-based lifecycle button would blur Media and file authority.

### Source-level guardrails added
- `scripts/trash/media_delete_inventory_u8.py`: fixed-repository-path, bounded source-only AST inspection. Reads known files, reports exact source SHA-256 witnesses, classifications and drift warnings as JSON. No imports of Media owners; no scripts, MPD, GIO, subprocesses, socket connections or local media operations.
- `tests/trash/test_u8_media_delete_boundary.py`: confirms the known classifications and that source drift (different MPD command, missing active-track protection, new Media lifecycle deck, missing source file) fails closed. Drift always leaves `actionAuthority:false`, `sourceOwnerApproval:false`, `genericTrashEligible:false`.
- Trash CI additionally prints the bounded U8 report. No new Media-owned workflow or UI changes.

## HOW TO USE

Safe read-only repository audit (from the repository root):

```sh
python3 -I -B scripts/trash/media_delete_inventory_u8.py
python3 -m unittest discover -s tests/trash -p 'test_u8_media_delete_boundary.py' -v
```

The JSON should report `INVENTORIED_READ_ONLY`, never “approved” or “file deletion enabled.” `DRIFT_OWNER_REVIEW_REQUIRED` means inspect changing Media sources with their owner, not modify Media automatically. No need for live MPD, Quickshell, radio, or music files.

## VERIFY

- Inventory is source-only, **not** a live filesystem scan, capability certificate or authorization grant.
- Verify the U8 AST test and full Trash CI on the PR's exact head before operator review; do not claim CI until it passes.
- Existing Media-owned `tests/media/test_headless_controller.py` tests that the active MPD queue entry is refused without `deleteid`.
- No native Media file deletion or Restore flow exists to exercise through U8 at this stage.

## WATCH OUT FOR

A real Media-file TRASH workflow must first distinguish **owned local source file** from MPD queue ID, YouTube item ID, radio UUID/stream token, cached state, recording and third-party provider catalog. It needs a Media-owner-approved path scope, stable file witness (e.g. inode/size/mtime and verified root), retention and permissions, preview and one-use confirmation, recoverable GIO move, and post-move Restore receipt. Some of these do not exist. Protect copyrighted/provider media and other source-owned data. The protected Archive/security lane remains independent.

Never use the shared BURN control for an MPD queue entry, backend state file, socket, radio station ID or external provider ref. Do not rewrite Media's actual controller or transport without source-owner assignment.

## CHECKLIST

- [x] Recheck canonical Syntagma/Hospital/permissions, main HEAD and Trash U5–U7 acceptance
- [x] Inspect Media-owned QML, MPD backend, controller, CLI, socket and intent store
- [x] Classify queue mutation separately from source file deletion
- [x] Create bounded read-only source report and synthetic fail-closed tests
- [ ] Full exact-head CI and fix any U8 source-only test issues
- [ ] Independent Media-owner and Nurse 2 review
- [ ] Authorize and design a *real* Media-owned local-file deletion adapter only if needed

## NEXT

**U9 proposed implementation contract**: if the Media owner confirms a concrete local-library file-delete need, implement a new Media-owned file preview/one-use GIO adapter with stable filesystem identity, preview count, root allowlist, and a recoverable receipt. Connect only that adapter to Trash++'s request-only deck in a separate approved feature. Do not conflate this with `queue_remove`. Otherwise U8 is a successful **no-file-delete-needed** finding and Media stays queue-only.

## DECISIONS

- No generic Media TRASH/BURN integration is approved or created by U8.
- Keep all Media-owned files and services unchanged.
- No live workstation writes, backend calls, MPD mutations, production activation, PR merge or live Hospital registration.
- User's prior U5–U7 UI acceptance is preserved; end-to-end disposable-file Restore remains separate.
