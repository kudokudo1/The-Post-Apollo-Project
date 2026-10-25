# Weather Station NEWS // Isolated video/browser viewer handoff

**STATUS //** Scoped integration contract and recovery handoff; external viewer **not implemented**. Operator approved the crash-safety first step and pursuing a separate viewer process. No verified live Hospital Room, Assignment, Session, worker role or ownership transfer.
**PATIENT //** `kudokudo1/The-Post-Apollo-Project` (NEWS UI). **DEPENDENCY //** `kudokudo1/Post-Apollo-SwayPx` (future Stage Director compositor capability). **AUTHORITY //** operator approval and explicit integration/merge gates.

## IMPLEMENTATION // Existing evidence and crash blocker

Operator installed the QtWebEngine QML module on Fedora Silverblue 44 and rebooted. Launching **NEWS → WATCH IN STATION** aborted the entire Quickshell 0.3.2 process (Qt 6.11.2) with:

`FATAL: Argument list is empty, the program name is not passed to QCoreApplication. base::CommandLine cannot be properly initialized.`

The crash stack crosses `QQuickWebEngineView` → `Qt6WebEngineCore` → `abort()`. In Quickshell v0.3.2, upstream `src/launch/launch.cpp` constructs the Qt application with `auto qArgC = 0; new QGuiApplication(qArgC, argv)`, which matches the Chromium command-line abort mechanism. Separate repair of that host would require a tested patched Quickshell binary and further host initialization/DRM/GPU verification, not a casual QML edit.

**Crash-safe milestone:** `widgets/weather/StationChannelScreen.qml` and `widgets/weather/StationViewerHost.qml` no longer import or indirectly instantiate `StationNewsWebView.qml`. WATCH opens a static safe-mode surface with CLOSE returning to NEWS; REPORTS still shows article metadata with disabled reader. The legacy WebEngine file is deliberately retained but unreachable from NEWS. No outside browser launches, local binary changes, new pollers, music/audio-controller change or compositor write.

## HOW TO USE // Proposed future transport contract

Preserve the operator's **WATCH IN STATION → single immersive viewer in the Station bay → × CLOSE returns to the source list** contract. MUTE starts ON and remains disabled until playback is real.

The Weather Station should own only:
- selected catalog record (`sourceId`, title, registered HTTPS target, source category, optional allowed YouTube video ID);
- viewer lifecycle intent (`open`, `close`, `mute/unmute`), explicit state (`not connected`, `starting`, `visible`, `failed`, `closing`);
- visible viewer bay rectangle and active output identity, derived at runtime from layer-shell/Wayland coordinates; tab selection and input focus policy.

A separate **browser/video process** should own web authentication/cookies, decoding, web audio and actual playback. The owning launcher must enforce a known program and allowed catalog target or checked single YouTube video. Never concatenate arbitrary URLs, channel names or shell fragments. Avoid unrestricted protocol handlers, inadvertent secondary tabs or accidental launch on browse. Honor publishers' paywalls/DRM and terms.

The future **Stage Director / SwayPX owner** must independently validate whether and how it can contain one real browser/video surface behind the NEWS viewport: compositor clipping (not an opaque painted cover), stacking/focus, per-surface actor identity, accurate pointer mapping and keyboard release, output/workarea translation, secondary monitors and popup restrictions. No requirement to build the view in Kitty; Qt/Chromium and MPV have different needs than terminal apps.

### Existing seams to inspect

- `widgets/weather/WeatherStationW.qml` for the PanelWindow, content-bay rectangle, panel visual clip, source selection and screen/output.
- `widgets/weather/StationNewsHub.qml` for catalog tabs and `chooseItem`, `closeViewer`, `channelMuted`; `StationNewsCatalogPolicy.js` and `StationViewerPolicy.js` for source URL qualification.
- `widgets/weather/StationChannelScreen.qml` for the safe-mode viewer / integration point.
- `widgets/weather/StationTerminal.qml` and `StationTerminalGeometry.js` for the *existing terminal-only* Sway actor/geometry lifecycle. Do not repurpose its terminal actor ID or assume its alpha cutout clips browser content.
- `widgets/messanger/XBrowser.py` for the currently implemented separate Chromium app-window and controlled window-class/profiles. It is a precedent for isolation, not a verified NEWS-in-bay host.
- `MODEL/weather-station-virtual-viewport-proposal-20261024.md` and SwayPX draft [PR #3](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/3), a **proposal**, not merged implementation authorization. SD0 is observer-only at the last verified evidence.

## VERIFY // Acceptance gates

1. Safety CI: neither NEWS watch/article route imports or dynamically loads `StationNewsWebView.qml`; CLOSE and mute-disabled controls stay visible.
2. Stage Director ownership gate: inspect current SwayPX branch/PR and Hospital assignment, if any; operator approves any compositor prototype separately. Do not assume an existing live Stage Director scene actor.
3. Separate-process smoke check: create a uniquely targetable viewer actor without affecting Quickshell; on browser crash or renderer failure, the shell stays alive and records failure; no unwanted workspace switching.
4. Containment: browser paints **only** inside the NEWS bay while open; no off-bay pixels or stray pointer targets; no forced browser launch beneath another window; verified both outputs, workarea offsets and resize.
5. Lifecycle: one viewer at a time; repeated clicks reuse or refuse, no duplicate processes; closing the Station closes/detaches the correct owned viewer; × CLOSE restores source rack and does not kill unrelated browser sessions.
6. Audio: starts muted, explicit UI control updates actual player and accurately reflects state; no spurious playback during catalog browse.
7. Source-specific: Al Jazeera, LiveNOW FOX, House/Senate floor, CNN/provider-login examples are tested separately. A registered link is *not* proof that the site allows player embedding.
8. Rollback: restore safe static viewer on any failure, terminate only owned child/surface, preserve saved creators and existing GDELT rate limits. No production activation before operator review.

## WATCH OUT FOR

- The fatal WebEngine constructor abort happens **inside Quickshell** and cannot be caught by a QML `Loader.Error` handler. Avoid using it even for a "probe" in the live shell.
- Do not assume compositor clipping is available: the Stage Director proposal remains P-level, not a working compositor. Side-by-side/browser launches alone fail the operator's no-interruption requirement.
- Any separate process that stores browser profiles or session tokens needs a clear storage and permission policy; Quickshell must not ingest those credentials.
- The LIVE/CONGRESS/CREATORS registry is a destination catalog, not a 24/7 stream client. NEWS REPORTS still uses GDELT under its independent cooldown.
- Source for this report: operator crash backtrace (2026-10-24), latest Post-Apollo UI source and Quickshell v0.3.2 `src/launch/launch.cpp` inspection. Reverify all paths at implementation time.

## CHECKLIST

- [x] Real crash captured, in-process web route diagnosed
- [x] Crash-safe NEWS branch assembled and tested under CI (when workflow passes)
- [x] Handoff and acceptance contract documented
- [ ] Real external browser/video process and compositor integration assigned
- [ ] Local live safety verified after approved merge/pull/reload
- [ ] Real embedded playback and close/mute behavior verified

## NEXT

Have the authorized Stage Director/SwayPX owner take this document together with the P-level viewport proposal and report back with an isolated, reversible V0/V1 prototype plan. Only after ownership and acceptance evidence may a separate NEWS viewer-integration branch wire actual launch/control. Existing player safe-mode should remain the fallback until then.

## DECISIONS

Confirmed direction: protect the entire Quickshell session before enabling video; prefer isolated media/browser execution to unrecoverable WebEngine-in-shell; preserve internal NEWS semantics and registered provider URLs; do not change existing local Quickshell or the compositor without explicit approval and independent owner coordination.
