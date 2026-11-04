# Post-Apollo // CAMERA, TV/MEDIA and SHELF foundation

**Patient:** \`kudokudo1/The-Post-Apollo-Project\`  
**Room/assignment:** new small desktop modules; first milestone Camera M1  
**Role:** external Hospital-compatible development worker; no live registration claimed  
**Status:** Camera M1 merged; M2 legacy gallery / zoom / selected Trash in draft PR #1265, native acceptance pending; future Zoom/TV/Shelf phases deferred  
**Authority:** operator final acceptance; no merge, live restart, package installation or local file deletion authorized by this document

## DECISIONS

These are **three independent surfaces**, designed to coexist simultaneously with Social, Weather and other widgets.

| Surface | Owns | Reuses | Deliberately does not own |
|---|---|---|---|
| CAMERA | shutter, captured files' viewfinder/gallery, screenshot classification, media metadata and user-directed photo management | existing empty \`modules/Screenshot.qml\`, \`services/files/FileService.qml\` identities, Sway/Wayland screenshot utilities | every filesystem path, Social messages, Zoom credentials, astronomy, TV playback |
| TV/MEDIA | video viewing, local/streamed movie and TV controls, media player targeting; later radio/TV channels | existing \`modules/Mediaplayer.qml\`, \`widgets/MediaDeckW.qml\`, MPD/MPRIS and source adapters | camera capture and screenshot cleanup, Social account state |
| FILE EXPLORER → SHELF | directories, search, copies, moves, browsing, later organized library shelves and shortcuts | existing \`services/files/FileService.qml\` (single filesystem truth) and AppControl FILES | duplicate filesystem scanning daemon or separate file identities |

### CAMERA // Immediate pain points

User has many thousands of screenshots on their Desktop and cannot conveniently select a single monitor, move screenshots into a predictable gallery, or batch-clean old files. They want an actual camera-like experience: view photos by date, manage/annotate/edit photos later, and host/launch video meetings without closing Social.

**Camera M1 contract (implementation candidate)**

- Reuse empty Screenshot dock module and add a separate \`CameraW\` PanelWindow to the existing shell. Its open state is independent of Social, so two widgets can remain visible simultaneously.
- An explicit shutter with three modes: selected region via \`slurp\`, focused Sway monitor via \`swaymsg -t get_outputs\` and \`grim -o\`, or full desktop via \`grim\`. The panel masks itself before capture.
- New PNGs saved to \`~/Pictures/Screenshots/Post-Apollo/\`. Gallery *reads existing files in place*: this directory, \`~/Pictures/Screenshots/\` and direct images on \`~/Desktop/\` (no second image database). Latest 150 results have thumbnails, local paths and timestamps. Inventory is read-only.
- Explicit \`PREVIEW MATCHES\` searches only Desktop image **filenames** that look like screenshots (Screenshot/Screen Shot/grim/Spectacle/Swappy/Flameshot). Ordinary family/other pictures must never enter that cleanup plan merely because they end in \`.jpg\`.
- **Separate confirmation** is required to invoke \`gio trash\`; original file stat signatures (device/inode/size/mtime) must match the preview; reject symlinks, traversals, stale plans and unexpected paths. Plan expires in 10 minutes; operations are non-recursive, reversible and do not invoke \`rm\`. No automatic mass deletion, migration or cleanup on install.
- Source tests are not a substitute for live Fedora/Wayland verification. Prerequisites: \`grim\`, \`slurp\`, \`swaymsg\`, and \`gio\` for Trash; inspect tool-status panel rather than assuming packages.

**M1 acceptance:** native startup without QML errors; open/close without stealing Social state; capture all / focused / region; gallery PNG preview and date; preview Desktop matches without moving photos; confirm Trash on a *disposable fixture directory*, verify recovery in desktop Trash, then operator explicitly accepts use with the actual Desktop. Never run a mass cleanup on the user's live Desktop for initial testing.

### CAMERA M2 // Legacy image inventory and viewfinder checkpoint (PR #1265)

- **Implemented in draft source:** Gallery enumerates Desktop, Pictures (including historical nested screenshots), Downloads, and known Screenshots folders. An explicitly chosen additional visible directory under HOME can be scanned without moving originals. Hidden directories, symlinked paths and scanning all of HOME are excluded.
- **Large libraries:** server-side search and 120-image pages replace the first-150 cutoff. ListView virtualizes thumbnails; reaching the end loads the next page automatically, with an explicit LOAD MORE fallback. Safety caps of 60,000 files, 1,600 directories and depth 4 report truncation. Nonstandard/external or very deep folders need separately scoped work.
- **Viewfinder:** reusable components/CameraImageViewer.qml is registered in components/qmldir; pointer-centered wheel zoom, fit reset, +/- controls and mouse-drag pan up to 8× are read-only over original files.
- **Single-picture Trash:** select an image, request preview, then separately CONFIRM TRASH or CANCEL. The Python helper writes a short-lived one-file signature plan and calls gio trash only after confirmation and unchanged-file checks. Existing Desktop bulk cleanup remains separate.
- **Metadata honesty:** shown date is filesystem modified time, not necessarily the picture's original capture time after copying.
- **Verification:** disposable 5,000-screenshot paging and safe Trash tests plus static QML source contracts. Native Fedora/Sway/Qt visual acceptance has not been performed and no personal image has been deleted or migrated.

**Still pending:** multi-select, arbitrary removable/network volumes, date-range UI, metadata-driven duplicates, restore UI, nondestructive editing, and Zoom/camera meeting integration.

### CAMERA // Follow-on milestones

1. **M2 image organization:** folder selection, recursive opt-in scanning, paging/virtualization beyond 150, sorting/filters by date/type, multi-select, batch metadata and duplicate detection, granular safe Trash with undo/restore. Support old screenshot filename conventions without automatically classifying unrelated photos.
2. **M3 editing:** nondestructive crop/rotate/annotations, copy-on-write export and explicit save changes; never overwrite the only original. Add clipboard copy and screenshot/region selection hotkey after keyboard-ownership audit.
3. **M4 video / Zoom:** separate \`MEETINGS\` mode with a Zoom integration adapter. First inspect installed Zoom client and actual Wayland screen-share/camera/mic behavior. A browser URL isn't an embedded call surface, and a launched Zoom native window isn't automatically contained in Camera. Stage Director/SwayPX may later provide controlled child view/containment. *Do not claim embedded Zoom video until the actual compositor/portal integration is tested.* Native Zoom, Social and Camera must be able to coexist without blocking keyboard/input.
4. **M5 webcam/photo/video capture:** use verified PipeWire/V4L2/portal permissions and on-demand shutter/record indicators. No always-on camera/mic process, background recording or silent upload. Respect privacy boundaries.

### TV/MEDIA // Future module work

- Extend the existing Hi-Fi Media Deck rather than replacing or duplicating MPD. Decide the separate TV/Video display chassis, transport mode, library, queue, subtitle, playback source and audio output selection.
- Use MPRIS for current external player control and a dedicated media surface for locally hosted video or accepted streaming media. Determine video/DRM/embed capability per source; no false claim of playing protected content via a headless catalog.
- Keep Social and Zoom meetings separately open; audio focus/ducking is an explicit future choice, never automatic microphone capture.

### FILE EXPLORER / SHELF // Future module work

- Extract the existing FILES/AppControl browser/search into a standalone, user-sized explorer view owned by \`FileService\`, not a second scanning provider.
- Later add a **Shelf** presentation for folders, collections, pinned locations, previews, NAS-connected libraries and user-curated workspaces. Shelf is a *presentation/index of real file identities*, not a parallel filesystem.
- Require clear permissions and recovery for destructive file operations. Migrate nothing implicitly; defer NAS sync / cross-computer media access until the shared identity/connection service has a reviewed contract.

## VERIFY / WATCH OUT FOR

- Existing code: \`modules/Mediaplayer.qml\`, \`widgets/MediaDeckW.qml\`, \`services/media/\`, \`services/files/FileService.qml\`, empty \`modules/Screenshot.qml\`.
- The Camera shell insertion is a real startup-graph change and requires native startup smoke **before** merge/deployment. GitHub CI validates policy and source only.
- Desktop contains real user data. No cleanup plan may run on personal files without a fresh explicit preview and user action; trash vs permanent deletion stays distinct.
- Environment dependencies, Zoom embedding and Stage Director maturity are unverified from a source-only assignment.

## NEXT

1. Complete Camera M1 CI; perform disposable native smoke before live acceptance.
2. Expand Camera browsing/cleanup based on observed naming and screenshot locations; obtain operator approval for any local folder migration.
3. Implement Zoom adapter under a separate cross-widget/Stage Director contract.
4. Begin TV and standalone Files/Shelf only after reuse boundaries and concurrent ownership checks.
