# 🏥💜 Weather Station M31 // Exclusive SUBJECTS MEDIA viewport for Stage Director WATCH v2

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Weather Station / SUBJECTS MEDIA viewport integration
ROLE // External DOC / Hospital-compatible, no live registration verified
ASSIGNMENT // Publish one read-only chassis-local active MEDIA player rectangle for verified SwayPX WATCH v2 QML client
BASE // `main` `8776b30b879bf7b43f72bd6c6ef759a382357541`
SCOPE // Weather geometry-only QML and source/native CI, no plugin activation
STATE // Candidate, exact-head CI pending

## IMPLEMENTATION

The verified SwayPX `PostApollo.StageDirector 1.0` `WatchBridge` (merged PR #73) consumes four **Weather chassis-local logical coordinates**. Weather's retiring CLASSIC NEWS viewport is not an allowed source. The original 1000×700 chassis and original MEDIA sources remain.

Exclusive read-only geometry path:

1. `StationNewsHub.playerViewportRect`: existing channel player's true geometry local to NEWS, and zero on viewer close/unload.
2. `StationMediaSubjectPane.activePlayerViewportRect`: read **the actual** `mediaLoader.item`. For NEWS/WATCH/CREATORS this is a direct `StationNewsHub`; for `media/overview` this is an Item with a nested `overviewNewsHub` that publishes `activePlayerViewportRect`. RADIO/hidden/unloaded routes report zero. `mapToItem(mediaPane)` and strict finite/in-bounds test.
3. `StationWorkspaceSurface.activePlayerViewportRect`: map the active workspace MEDIA pane into workspace coordinates and gate with `subjectWorkspaceActive`.
4. `StationSubjectNavigator.activePlayerViewportRect`: **exclusive owner selection** between the regular `workspaceLoader.item` when `!indexOpen` and `indexLayer`'s `mediaLivePane` when `indexOpen`. The index pane is no longer loaded as a hidden duplicate on the ordinary workspace route. `StationWorkspaceSurface` keeps its persistent HOME object but disables its hidden MEDIA pane when INDEX is active. Viewport is mapped to navigator coordinates.
5. `WeatherStationW.activeSubjectPlayerViewportRect`: map navigator player geometry to `stationBackground` local coordinates with `StationMediaViewportPolicy.owner()` and strict bounds. This must return `Qt.rect(0,0,0,0)` on station close, subject unload, terminal takeover, non-MEDIA route, hidden viewer or malformed/exceeding dimensions. `activeSubjectPlayerViewportValid` is a read-only validity hint.

No new NEWS provider, popup, process, service, cache, subscription, Qt WebEngine, browser launch or Stage Director compositor authority is added. `StationMediaViewportPolicy.js` is only a pure finite rectangle/owner guard; QML continues to own actual `Item.mapToItem` translations. A QML player rectangle is **not** an independent native `wl_surface`.

## HOW TO USE

On the existing Weather UI, normal SUBJECTS MEDIA routes, MEDIA overview, and INDEX continue to work unchanged. This PR adds no button and requires no local installation. A separate, operator-approved native client binding may later set `WatchBridge.viewport: weatherStation.activeSubjectPlayerViewportRect`, and send `(0,0,0,0)` when invalid. That module **must be loaded only when installed/approved**; an unconditional `import PostApollo.StageDirector` would break ordinary Quickshell systems. WATCH source tokens remain allowlisted to `bbc` and `cspan` by SwayPX.

The viewer still explicitly reports video playback unavailable. Successful geometry and candidate acknowledgement do not render video.

## VERIFY

- [x] Recheck latest Weather `main`, SwayPX `master` and relevant Syntagma AGENTS/OPERATE rules
- [x] Check current PR ownership: no open active Weather migration, old Hi-Fi taskbar PR is unrelated
- [x] Preserve CLASSIC retirement, existing active NEWS hub, original MEDIA routes and terminal actor
- [x] Add pure bounded geometry/owner policy and read-only reactive QML chain
- [x] Add source-level tests for nested overview, exclusive INDEX/workspace owner, bounds/hidden state
- [x] Add disposable Fedora 44 native Quickshell/QML test of actual NEWS viewer Loader, reports overview, RADIO, close, route switch and hidden pane
- [ ] Exact-head Node, native Quickshell, teardown and compatibility CI passing
- [ ] Bounded merge + exact-main read-back
- [ ] Same-Wayland-client WATCH bridge loaded by live operator-approved Quickshell
- [ ] Restricted browser renderer, scene/input/clip and actual desktop acceptance

## WATCH OUT FOR

`StationSubjectNavigator` has **two separate MEDIA pane definitions**, one within persistent workspace, another under INDEX. Both previously had NEWS loaders active as long as their own `visible` property was true, even when the INDEX parent was hidden. M31 prevents duplicate active hidden MEDIA hubs and reads only the selected one.

Qt's `Loader.item` is either a direct NEWS object, a RADIO object, or a MEDIA overview Item with nested NEWS. Never assume all of them expose `playerViewportRect` directly. Revalidating every coordinate at each parent mapping catches host resize and negative/out-of-chassis positions.

The native Quickshell test is a disposable Xvfb/QtQuick test, **not** a SwayPX compositor or operator desktop test. The production WATCH QML client remains in a different repository and is not automatically installed on this machine. Do not add an unconditional import or enable a real browser from this PR.

## CHECKLIST

- [x] One source of player geometry and bounded rebase
- [x] Zero for route changes, INDEX switch, hidden/unloaded NEWS and terminal takeover
- [x] Keep HOME persistence and existing TOOLS TERMINAL/CLOSE control
- [x] No local workstation changes or Chrome launch
- [ ] Review exact commit/CI, merge if green with current authorization
- [ ] Separate installation/import gate and WATCH source-selection handoff

## NEXT

After green source and native MEDIA geometry CI, merge into Weather `main`. Next distinct assignment integrates the **optional, installed** `PostApollo.StageDirector` native QML module with this property on the same Qt Wayland connection, without requiring that module on ordinary desktops. Connect the existing user-selected WATCH catalog item to the fixed allowlisted source, and use the same viewer CLOSE to revoke geometry. Actual embedded playback remains a subsequent gated browser supervisor/render/clip/input milestone.

## DECISIONS

SUBJECTS canonical; CLASSIC remains retired. No second player, no duplicate loader, no desktop activation. The geometry interface is read-only, and final operator acceptance remains open. SwayPX owns compositor authority, Weather owns viewport data.
