# Weather Station // M28-T NEWS + RADIO 1:1 migration

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station CLASSIC → SUBJECTS original visual/content preservation  
ASSIGNMENT // Make original CLASSIC NEWS and RADIO interfaces fully accessible inside MEDIA without feed/player changes  
STAFF // External Hospital-compatible Doctor, OPEN AI // CHATGPT; no confirmed live Hospital registration  
BASE // `main` `ba6e640c30543c31b4825bdad469d4c0fb58743b` (M28-S MAP merged)  
AUTHORITY // Operator requested 1:1 migration now, visual styling and live feed fixes later; no local workstation modifications

## IMPLEMENTATION

The earlier M28-D/E/J source ledger certified **17 MEDIA routes** and 103 historical controls, but many native MEDIA routes **filtered original panels**. The original `StationNewsHub.qml` uses one six-tab interactive channel surface (LIVE, CONGRESS, REPORTS, COMPARE, CREATORS, SATIRE); its REPORTS tab uses `StationDiscovery.qml` and shows GDELT headlines, filters, reporting trend graphs, story families, article/location inspectors, source cooldown, and visual history together. In SUBJECTS, the NEWS route had no six-tab selector and filtered the REPORTS groups. Original `StationRadio.qml` similarly displays search/presets/directory, saved favorites/recents, single transport/MPD controller, and status simultaneously, while native RADIO routes filtered them apart.

**M28-T is additive and route-scoped:**

- `media/news/full`, exposed in the five-button MEDIA bottom rail as **NEWS // ALL**, and at INDEX → MEDIA → NEWS → ALL ORIGINAL TABS AND REPORTS. This selects the **same existing `StationNewsHub`** through the existing one `StationMediaSubjectPane` Loader. The new exact-route `isFullNews()` restores original LIVE/CONGRESS/REPORTS/COMPARE/CREATORS/SATIRE top tab bar, effective section and its original GDELT report loader. Only while REPORTS is selected does the one `StationDiscovery` news report view load. The full NEWS route permits all original news report filter, list, trend, story-family and inspector-hint sections. Saved creator controls and explicit uploads remain on the original single file/process owner.
- `media/radio/full`, exposed as **RADIO // ALL**, and INDEX → MEDIA → RADIO → ALL ORIGINAL CONTROLS. It selects the **same existing `StationRadio`** through the same single MEDIA Loader, and enables its seven original grouped panels: header, source, search/presets, station directory, saved favorites/recent history, transport and status. Radio Browser selection/LOAD/ENTER remains deliberate, with **no autoplay** and existing Hi-Fi/MPD transport. No extra `HeadlessMediaController`, memory store, player, URL launcher or stream fetcher is added.

The original 17 detailed MEDIA routes remain available in INDEX, yielding **19 routes total**. MEDIA keeps five equally sized main bottom slots; only NEWS/RADIO landing paths/labels change. The unchanged MEDIA overview remains two summary bays. Existing original CLASSIC NEWS/RADIO/NEWS→MAP handoff and its user-visible safe-mode viewer are untouched. The 103-control source provenance ledger is unchanged.

**M28-S follow-up verification:** An earlier draft MAP PR #1175 was merged by another participant before its corrected final full-suite CI completed. This milestone adds a retroactive full MAP/source-lifetime test to its workflow and to the broad existing Weather CI. Do not call M28-S 100% verified until checks are run on the compatible new source baseline. The original MAP remains a shared exact `StationDiscovery` instance, no duplicate.

## HOW TO USE

After a separately approved workstation update, open Weather Station → **SUBJECTS → MEDIA**. Select **NEWS // ALL** in the bottom mode row; use its original six channel tabs, including REPORTS for article filters, charts, story analysis and inspectors. Select **RADIO // ALL** to see directory, search, favorites, recents, transport and status in one scrollable view. The old focused NEWS/WATCH/RADIO/CREATORS routes remain accessible through INDEX. Compare to CLASSIC → NEWS and CLASSIC → RADIO. The NEWS viewer's video engine remains disabled in safe mode; this route does not claim video playback.

## VERIFY

- `tests/weather/test_media_full_visual_parity_m28t.js` checks exact two full routes, original 17 routes retained, real five MEDIA bottom buttons, original six channel tabs, full GDELT list/trend/story/inspector, seven RADIO panel types, original MPD transport/memory, same loader, manual actions and safe video mode.
- M28-T updates `tests/weather/test_media_subject_panels_d1.js` only for additive route accounting and channel tab presentation. Older D1 behavior, M28-J MEDIA catalogs, M28-E radio source mapping, M28-A MEDIA→EARTH handoff remain guarded.
- Dedicated `.github/workflows/weather-media-full-visual-parity-m28t.yml` re-runs M28-T, existing MEDIA tests and MAP's retrospectively verified `tests/weather/test_map_full_visual_parity_m28s.js` with native source/lifetime/rail regressions, plus other applicable PR workflows.
- **Source-level/CI is distinct from native Fedora/UI/pointer acceptance**. No workstation restart, local update, download, or live feed test occurred.

## WATCH OUT FOR

- The original channel tabs are user-facing **catalog destinations**. Watch-channel labels are not proof of playable video. Quickshell WebEngine was disabled due native runtime failure; separate Stage Director isolated viewer work remains a known blocker.
- The original radio directory will automatically make its existing *directory search* after mount (as in CLASSIC); this is **not audio autoplay**. Playback requires explicit selection/LOAD/PLAY and uses the original private controller.
- MEDIA overview still contains one half-height GDELT reports bay and one half-height RADIO bay; for complete original content, choose NEWS // ALL or RADIO // ALL. Do not redesign the summary dashboard in this migration.
- All original creator file ownership and explicit upload check commands remain unchanged. Never create a duplicate saved-channel writer.
- The 103/103 control ledger is a navigation source audit, not full UI visual acceptance. Other CLASSIC sections can be audited separately; CLASSIC retirement is not approved.
- If GitHub merges this PR before final checks finish, explicitly record the verification gap and run a new compatible full CI PR before claiming technical completion. This is documentation/verification protocol, not a source functionality change.

## CHECKLIST

- [x] Read current Syntagma AGENTS, Hospital Agent and Authority protocols.
- [x] Verify current main and no other open Weather PRs.
- [x] Restore exact original NEWS top tabs and in-pane GDELT report groups.
- [x] Restore complete original RADIO directory, saved/recents and transport in one view.
- [x] Keep old focused routes, five bottom media modes, safe-mode video and shared controller.
- [x] Add explicit full-content and provider-ownership tests plus independent MAP retrospective workflow.
- [ ] Run and repair final-head CI; verify source ownership and merge only green.
- [ ] Operator compares actual MEDIA/MAP screens after separate authorized local update.
- [ ] Continue broader visual parity audit and seek separate CLASSIC retirement approval.

## NEXT

After M28-S/T green GitHub validation, compare original MAP, NEWS and RADIO to their **SUBJECTS FULL** modes at the user's native monitor geometry; log missing controls or clipping as independent issues. Preserve CLASSIC and all source/data owners until operator accepts the 1:1 migration. Styling work comes afterwards.

## DECISIONS

Operator instruction: **move 1:1 for now; appearance later**. All original source owners are retained. No media playback expansion, local system mutation, backend/feed repair, irreversible removal, or live Hospital registration is asserted.
