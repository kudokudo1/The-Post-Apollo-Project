# 🏥💜 Weather Station M32 // Optional WATCH v2 QML sender and selected catalog source

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Weather SUBJECTS / optional Stage Director WATCH integration
ASSIGNMENT // Connect existing selected MEDIA player and M31 chassis-local rect to verified SwayPX WATCH v2 client without hard dependency, unsafe browser or local machine mutation
ROLE // External DOC, Hospital-compatible, not live-registered
BASE // `main` `31a595d2c72cb3005a5fc925757394dd4338456e`
UPSTREAM // Weather M31 PR #1305 merged at `a7ba5a428d41fb1043b1f49175600a1c44702fdd`; SwayPX SD2 PR #73 merged at `dd612f430467d78d30841fa6a3abc877191cee30`
STATE // CI candidate, no operator installation or runtime activation

## IMPLEMENTATION

M31 exposes `WeatherStationW.activeSubjectPlayerViewportRect` as one strictly bounded, chassis-local rectangle. M32 carries a **catalog-authorized source token** through the identical selected loaded-viewer chain:

- `StationNewsCatalogPolicy.toViewerRecord` attaches `watchSourceId` only for a canonical `bbc` or `cspan` catalog row with its canonical URL. Arbitrary publisher pages, user creators, fake BBC labels and input URLs receive empty token. This is separate from the HTML URL and never serializes it to the native bridge.
- `StationNewsHub.activeWatchSourceId` requires an actually open viewer with nonempty geometry. `StationMediaSubjectPane` handles normal NEWS and the nested MEDIA overview NEWS hub. The ordinary workspace and INDEX owner propagate only the active selected player, then Weather root publishes `activeSubjectWatchSourceId`. Other pages or terminal takeover yield empty values.
- `StationWatchBridgeGate.qml` has **no `import PostApollo.StageDirector`** and is default OFF. Its Loader only evaluates `StationWatchNativeAdapter.qml` when `optIn && hostOpen`. An ordinary desktop without the external plugin never loads the native file. The gate binds the M31 rectangle and selected token reactively into the loader, and exposes read-only bridge status.
- Only `StationWatchNativeAdapter.qml` imports `PostApollo.StageDirector 1.0` and constructs `WatchBridge`, borrowing the owning Weather process's existing Qt Wayland connection per SwayPX contract. The adapter sends a WATCH request once when a canonical publisher selection, positive viewport and physically paired private WATCH object are present; **SENT does not mean ACCEPTED**. Viewer CLOSE or route/source changes revoke the private WATCH candidate via native CLOSE and do not send another source until a new permitted pairing.
- The Weather root sets `stageDirectorWatchOptIn: false` by default. No extra button, developer menu, browser subprocess, open URL, scene clip, focus, popup, pointer input, or local installation was introduced. Existing `WATCH IN STATION` continues to open the safe-mode preview with video disabled.

The real C++ `WatchBridge` native same-client event loop and CLOSE ACK are already tested in SwayPX PR #73; this PR specifically verifies the **Weather QML glue** without importing the real native module in ordinary installations.

## HOW TO USE

Nothing changes on the current desktop until the optional SwayPX plugin is separately built, installed into Quickshell's Qt QML import path, and explicitly enabled in the owning runtime. The operator approval for these local steps has **not** been requested or granted in this assignment.

The future deployment will set `stageDirectorWatchOptIn: true` only in an operator-approved Weather runtime, with the validated plugin and SwayPX pairable compositor. The UI action remains **SUBJECTS → MEDIA → WATCH → BBC or C-SPAN → WATCH IN STATION**, followed by physically pairing the real host per SwayPX's private gesture. The adapter then sends the selected fixed source token and M31 viewport. The same viewer's **CLOSE** sends protocol CLOSE; browser rendering is still absent.

Other catalog entries remain selectable in safe mode but cannot request a native WATCH candidate. A successful candidate still cannot launch the browser, move/crop a window, or route input.

## VERIFY

- [x] Re-read canonical Syntagma `AGENTS.md` / Hospital protocol; inspect latest Weather and SwayPX HEAD and open ownership
- [x] Preserve M31 single active MEDIA and 1000×700 chassis; no CLASSIC restoration
- [x] Only BBC/C-SPAN catalog IDs, exact canonical URLs, no arbitrary native URL
- [x] Native import in separate opt-in-only QML file; default ordinary gate disabled
- [x] Synthetic source/VIEWER CLOSE and route-change lifecycle in QML adapter
- [x] Add disposable Fedora native Quickshell tests with optional module **absent**, then with test-only mock QML module
- [ ] Exact HEAD Node, native Quickshell, Weather teardown and Syntagma CI green
- [ ] Exact commit merged and read back on `main`
- [ ] Operator-approved local native plugin installation and true Qt/Wayland paired Weather client
- [ ] Separately authorized restricted browser renderer, clip and input containment and final acceptance

## WATCH OUT FOR

The optional QML import must NEVER be moved into `WeatherStationW.qml`, a normal shared component, or `StationWatchBridgeGate.qml`; Quickshell resolves imports when those types load and would fail to start on ordinary systems without the plugin. A false value for `stageDirectorWatchOptIn` must prevent all attempted plugin loads.

The embedded browser still is not usable: `StationChannelScreen.playbackAvailable` remains `false`. The native WATCH protocol only produces `CANDIDATE_ONLY` and `VIEWPORT_CANDIDATE_ONLY` information, never authority over an unrelated XDG window. Server pairing requires a native physical host selection and same `wl_client`, **not** a fabricated namespace or QML string. Real operator Quickshell + Wayland plugin import is yet unverified; disposable mocked QtQML glue is not a substitute.

The gate closes the native client when Weather closes/unloads; if a user selects another publisher after a candidate has been sent, the existing pairing is revoked rather than silently retargeting the browser. The operator must re-pair for a subsequent WATCH source. Other publishers are safe-mode only.

## CHECKLIST

- [x] GitHub-only file changes, no local Fedora/QS restart
- [x] No second NEWS, Kitty, MPD or Chrome process
- [x] Selected-publisher token follows same exclusive MEDIA rect and is allowlisted
- [x] No mandatory Stage Director import for ordinary desktops
- [x] Viewer CLOSE maps to protocol CLOSE when paired
- [ ] Green CI and merge
- [ ] Operator deployment approval and real integrated Quickshell test
- [ ] Browser supervisor/render/crop/input accepted in separate milestone

## NEXT

After CI and merge, coordinate an **operator-approved runtime installation plan** for the native SwayPX Qt module. Validate the existing Qt/Quickshell QPA ABI on the operator's Fedora Silverblue and the explicit native pairing selection, then perform an in-station WATCH/CLOSE event handshake. Only then consider restricted browser session lifecycle, viewport masking and pointer containment.

## DECISIONS

External Hospital-compatible DOC, GitHub-only permission. SUBJECTS remains canonical, CLASSIC retired, original terminal preserved. Fixed allowlist and fail-closed no-plugin default. No real browser, installation, automatic opt-in, or production input authority. Operator final DONE remains open.
