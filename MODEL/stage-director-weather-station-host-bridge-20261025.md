# Weather Station → Stage Director // NEWS host and viewport seam

**STATE //** Implemented as a source-level, read-only observation seam in a separate Weather UI feature branch, not merged or locally activated.  
**PATIENT //** `kudokudo1/The-Post-Apollo-Project`; dependency `kudokudo1/Post-Apollo-SwayPx`.  
**OPERATOR //** Final authority. No live Hospital Room/Assignment or worker takeover assumed.  
**DATE //** 2026-10-25.

## IMPLEMENTATION

The operator asked for NEWS channels to WATCH within Weather Station. In-process QtWebEngine aborted Quickshell, so the existing NEWS viewer remains safe-mode and external browser launching is disabled until an independent compositor viewport has been verified.

Stage Director PR #7 on the SD1 development chain identifies native layer-shell Weather host **candidates** only if they have an exact namespace `post-apollo-weather-station`. Current Weather Station `widgets/weather/WeatherStationW.qml` previously had no unique namespace. This change adds `WlrLayershell.namespace: "post-apollo-weather-station"` **statically**, before its Quickshell layer-shell window connects. It preserves the existing overlay layer, keyboard ownership, margins, input-mask terminal cutout and all menu geometry. The namespace becomes part of the host protocol and should be treated as stable once merged.

The other half is **actual NEWS player geometry**, not legacy Star Map/Kitty geometry:
- `StationChannelScreen.qml::playerViewportRect` derives directly from `playerBay.x/y/width/height`, excluding the CLOSE/MUTE strip and bottom status bar.
- `StationNewsHub.qml::playerViewportRect` exists only while a channel viewer is open. It maps the loaded channel screen's local viewport to the NEWS hub with `mapToItem`. When closed, before the Loader is ready, or while NEWS is not open, it returns an empty rectangle.
- `WeatherStationW.qml::newsViewerViewportRect` maps NEWS-hub-local viewport to the Station `stationBackground` logical chassis. `newsViewerGeometryValid` rejects closed/inactive/zero-sized/out-of-chassis locations.

There is no new subprocess, browser process, scene IPC, filesystem write, polling service, QtWebEngine construction, or cross-repository compositor mutation. The current `CHECK VIEWER` remains read-only and cannot launch.

**Candidate identity is not authorization.** Any third-party layer client can attempt to copy a namespace. The trusted Stage Director owner must associate the actual Quickshell layer-shell client and a specific operator WATCH intent with one browser process and verified actor, then install popup/input, post-layout clip and teardown gates before activating V1 native clipping.

## HOW TO USE

After operator-approved merge and local update, the Weather Station menu works as before. NEWS → channel → WATCH IN STATION opens the *same safe mode*. The geometry and namespace are internal properties for future Stage Director coordination; no new control is shown and no external player starts.

Developers can inspect `WeatherStationW.qml::newsViewerViewportRect` and `::newsViewerGeometryValid` in a QML debugging session. Coordinates are **relative to the Station chassis**, not compositor-global, screen pixels or video-player coordinates. The compositor must use its own observed layer surface origin and output bounds; it must not interpret QML X/Y alone as a trusted absolute placement.

## VERIFY

Static Weather regression test `tests/weather/test_station_news_viewport_geometry.js` checks one immutable namespace declaration, actual component-based player geometry, the open/close guard and chained local mapping. Existing NEWS crash-safety checks ensure the in-process WebEngine cannot run. Source-level tests do not prove a running Quickshell instance advertises the namespace, or that resizing, output scale and nested browser render match the model. These need runtime acceptance.

The Quickshell Wayland `WlrLayershell.namespace` property is available in 0.2.1 and documented as a string set **before** window connection. `mapToItem` is Qt Quick's item-coordinate conversion. All actual compositor coordinates are Stage Director's responsibility.

## WATCH OUT FOR

- **Separate integration:** the SwayPX PR #4–#7 series is merged only along stacked **development branches**, not necessarily onto `master`. Recheck base refs before assuming production SwayFX includes it. A taskbar pull only updates its checked-out local branch.
- **No live auth from namespace:** the compositor may recognize a matching string, but must verify session ownership, process provenance and mapped layer. Never set `owner_verified` or `can_bind_viewer` simply because the text matches.
- **NEWS/report distinction:** Channel player bay geometry applies to the channel safe-mode screen, not GDELT REPORTS article reader.
- **QML Loader lifecycle:** property references are reactive, but coordinates are only populated after `StationChannelScreen` is instantiated and valid. CLOSE returns a zero rectangle.
- **Output coordinates:** Sway output workarea origin, scaling and multi-monitor translation are not inferred in this code. The actual layer-shell host origin must be observed by SwayPX.
- **Operational risk:** changing namespace of an existing layer shell can affect external rules matching the prior namespace, although existing in-repository Weather behavior is unchanged. Obtain live acceptance before any local pull/restart.
- **No playback proof:** the viewer stays disabled; no claims about CNN/C-SPAN/YouTube streams being playable in Weather Station.

## CHECKLIST

- [x] Inspect both repository heads, current source and stacked PR status
- [x] Add distinct Weather layer-shell namespace
- [x] Derive channel NEWS bay from real QML item dimensions
- [x] Invalidate coordinates on close/inactive/loader-not-ready
- [x] Add regression tests and handoff
- [ ] GitHub CI
- [ ] Operator-approved merge and optional live read-only namespace/geometry smoke check
- [ ] Trusted compositor host/process/actor association
- [ ] Popup/input/reapply/teardown authority and nested browser test
- [ ] Real WATCH playback integration with rollback

## NEXT

After GitHub checks, the authorized Stage Director owner should inspect actual mapped layer namespace, global compositor coordinates and output with a non-actuating observer. Verify these against the QML logical rectangle at runtime; only then implement authenticated host ↔ browser session ownership, real scene clipping, and input/popup containment in a nested compositor. Keep safe-mode WATCH active until the complete chain is accepted.

## DECISIONS

Re-use the existing Weather Station QML hierarchy and Stage Director candidate contract. Change no UI layout or implicit dimensions. Do not activate a browser merely because a namespace or geometry matches. Preserve reversible dev-branch and operator deployment gates.
