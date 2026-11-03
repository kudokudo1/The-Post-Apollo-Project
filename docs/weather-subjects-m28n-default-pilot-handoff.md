# Weather Station // M28-N Reversible SUBJECTS-first open pilot

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station / CLASSIC → SUBJECTS continuity  
ASSIGNMENT // Change the *opening preference*, not delete CLASSIC; preserve the one source/terminal/data owner  
STAFF // External Hospital-compatible Doctor (not live Hospital-registered)  
PERMISSIONS // Bounded GitHub branch, tests, CI and PR; **no local Fedora writes, Quickshell restart, production activation, CLASSIC removal or final acceptance**  
BASELINE // `main` `3b261ac18b9a337fd301cc2ace6b3b4a985df2bf`, M28-M audit merged

## IMPLEMENTATION

The pilot adds `StationSubjectDefaultPolicy.js`, a pure, versioned gate with `SUBJECTS_FIRST_PILOT = true`. The root WeatherStationW uses it on **open()**, while the collapsed view remains `subjectNavigationOpen: false` to unload native source panels when not on-screen. The existing rail can still switch to CLASSIC for the current open session, and the toggle can switch back to SUBJECTS without changing original source ownership.

**Important lifecycle discovery:** `WeatherStationW.qml` is an always-visible `PanelWindow`, whose `implicitWidth/Height` become 0 when `menuOpen=false`. Setting `subjectNavigationOpen=true` at object initialization or after close would allow `StationSubjectNavigator.workspaceLoader` to remain active while a 0x0 window is hidden. Thus SUBJECTS-first means **select SUBJECTS when opening, not keep SUBJECTS loaded while closed**. The close path must set `subjectNavigationOpen=false`, then `menuOpen=false`; the next open reselects SUBJECTS. Root `WeatherService` and `SpaceService` remain globally owned; only view-scoped sources unload.

### Intended UI/keyboard contract

- **Open Weather Station**: default into the live SUBJECTS workspace, retaining the route last selected during the current root lifetime; reopen from deep INDEX by returning to the last normal workspace; normalize the legacy `currentView === "terminal"` to `"home"` before opening SUBJECTS to avoid a phantom terminal overlay.
- **Rail bottom → CLASSIC**: enter the preserved original eight-mode display only when the root Kitty terminal is IDLE and no context terminal is requested; this is a temporary per-open rescue route.
- **Rail bottom → SUBJECTS**: return to the real seven-family workspace, also guarded against open terminal. Original `openLegacyFromSubject()` still works as the deep-INDEX emergency route.
- **Escape in deep INDEX**: return to that subject's previously selected workspace, not CLASSIC; **Escape in SUBJECTS workspace or CLASSIC**: close Weather Station; Meta+Shift+Q always closes. Retain one keyboard handler and its Shortcut fallback.
- **Close**: close any original Kitty session via the root terminal owner, unload the subject workspace, collapse the 0x0 PanelWindow. Reopen follows the pilot preference; a manually entered CLASSIC fallback does not permanently change user preferences.
- **Rollback**: change `SUBJECTS_FIRST_PILOT` to `false` in the versioned policy (new reviewed PR and separately approved live deployment) to restore original CLASSIC-first open, while preserving all original components. The in-widget CLASSIC button is the immediate session fallback. No hidden local setting or auto-user migration is created.

### Do not remove

`StationHome`, `StationGround`, `StationSky`, `StationSpace`, `StationDiscovery`, `StationNewsHub`, `StationRadio`, `StationTerminal`, all underlying providers, `WeatherHomeFavoritesStore`, persistent cache, archives, history, home favorites, original event/dossier stores, source badge, NWS alert priority, single map/relevance/timeline actors, and M0's 103-ID source provenance. Do not activate QtWebEngine or Stage Director viewer work as part of this pilot.

## HOW TO USE

After **separately authorized** local deployment: open Weather Station normally; it should show SUBJECTS HOME or the previous active native route. Use bottom of left rail **CLASSIC** to enter the original eight-page display; the same button then reads **SUBJECTS** to return. Test INDEX via the top button and Escape to exit INDEX; Escape once more to close. Reopen: SUBJECTS should return. Launch TOOLS → STAR MAP or CONSOLES and verify the same single Kitty/Sway actor is used; try toggling CLASSIC while terminal is open, which must remain unavailable.

## VERIFY

- Pure source policy: `tests/weather/test_subjects_first_pilot_m28n.js`, asserting feature gate and opt-out, 0x0 close unload, INDEX Escape behavior, CLASSIC fallback safety, root binding, single terminal, original source count and original component preservation.
- Dedicated workflow `.github/workflows/weather-subjects-first-pilot-m28n.yml` plus full original GitHub CI, including navigation/W1 rail, Weather/Cosmos/Earth source ownership, terminal and NWS alert priority.
- Native Fedora/Quickshell/Kitty CI tests validate many original contracts; this does **not** replace the operator's live compositor session acceptance.

## WATCH OUT FOR

- `onCurrentViewChanged` originally forces `subjectNavigationOpen=false`, a potential trap when restoring legacy terminal or changing hidden CLASSIC state. Preserve the one root terminal cleanup but avoid forcing a subject-to-classic switch accidentally.
- `StationSubjectNavigator` persists `indexOpen` and `currentPath` across closes. Reopening must not display a parent group with no renderable content just because INDEX was previously open.
- Original `WeatherStationW.qml` `sourceStatusText`, `currentView` and footer rely on CLASSIC routing. Only the SUBJECTS-first *preference* is changing, not complete legacy retirement.
- Weather M6c PR #1146 has **merged**. The pilot root patch was authored over its merged WeatherStationW, preserving provider diagnostics and its Escape priority. PR #1148 (the original incomplete draft) was separately merged before root wiring; corrective PR #1150 contains that missing root integration. Do not mistake the earlier merge for finished functionality.
- Stage Director isolated playback remains a separate blocker; 103/103 source mapping does not imply video hosting or operator acceptance.

## CHECKLIST

- [x] Review Syntagma AGENTS / Hospital authority and previous M28-M dependency handoff.
- [x] Identify root 0x0 PanelWindow close-state and background workspace risk.
- [x] Implement isolated pure pilot policy, test and CI without sharing a root file with active M6c ownership.
- [x] Integrate root open/close/keyboard/terminal guards after M6c merged; no duplicate collectors.
- [x] Update only historical assertions for the guarded CLASSIC fallback and M6c diagnostics Escape priority.
- [x] Complete corrective PR #1150 code and all 34/34 automated checks on pre-documentation head `57701f937c78e8db1bf2ff7ef88948d740663348`; final HEAD must be reverified after this documentation amendment.
- [ ] Merge corrective PR #1150 if its final HEAD is green and collision-free.
- [ ] Live Fedora/Quickshell/Sway acceptance and explicit CLASSIC deletion permission remain separate.

## NEXT

After corrective PR #1150 lands, leave both views available and gather real operator acceptance of open/close, keyboard/INDEX, single Kitty identity, weather/space source lifecycle, provider health and saved state across normal restarts. Use `StationSubjectDefaultPolicy.SUBJECTS_FIRST_PILOT=false` as the source-level rollback if user acceptance fails. Deletion of CLASSIC presentation is a distinct, higher-risk milestone requiring separate approval.

## DECISIONS

The feature flag is in source and fully reversible; the operator's installed machine is untouched. No claim of live Hospital registration or final DONE. The root window's collapsed source lifetime is a hard correctness requirement. The one root `StationTerminal` and original service/store actors remain canonical.
