# Weather Station // M28-M CLASSIC retirement readiness

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Weather Station / CLASSIC → SUBJECTS full-capability migration  
STAFF ROLE // External Hospital-compatible Doctor, OPEN AI // CHATGPT  
CONNECTION // EXTERNAL; no verified live Hospital Room or assignment registration  
ASSIGNMENT // Read-only source-level pre-retirement dependency inventory and proposed reversible acceptance gates  
SOURCE BASE // `main` `f964403f7b3913d28017e4b3a3e6bb8327859367` (M28-L merged)  
STATUS // Inventory/proposal only; **no CLASSIC deletion, runtime switch or local activation**

## IMPLEMENTATION

**No executable code is changed in M28-M.** M28-D through M28-L documented native SUBJECTS destinations for all **103/103 historical M0 mapped controls**. The M28-L source parity PR #1143 merged with **53/53 CI checks green**, including native Fedora NEWS/MEDIA→EARTH, terminal and source tests. This establishes historical *source wiring* but not complete feature parity or the operator's workstation acceptance. M0 `StationSubjectNavigationPolicy.PANELS` and `sourcePagesForPath` still preserve historic provenance.

The code-level cutover inventory below is the dependency map for the next **separately authorized** implementation. Current CLASSIC UI and source services must **not** be bulk-deleted as one patch.

### A. Legacy display to retire, not original component implementations

| Owner | Current role | Proposed fate / dependency gate |
|---|---|---|
| `WeatherStationW.qml` `mainModes` (8 IDs), `currentView`, `navigationIndex` | CLASSIC selection, keyboard navigation, panel label and some terminal/source gating | Remove only after replacing every reference with a valid SUBJECTS route or explicit terminal session |
| `modeRail` legacy `railColumn` + `subjectBrowserToggle` | Eight CLASSIC buttons and CLASSIC/SUBJECTS switch | Future cutover should retain shared **160 px** rail geometry, seven-family `StationWorkspaceFamilyRail`, and deep `StationSubjectRail` |
| `weatherContentLoader`, `homeViewComponent`, `groundViewComponent`, `skyViewComponent`, `spaceViewComponent`, `mapViewComponent`, `newsViewComponent`, `radioViewComponent`, `placeholderViewComponent` | Whole-page CLASSIC loader and component declarations, inactive under SUBJECTS | Candidates to remove **only after** explicit root lifecycle transition and rehearsal; do not delete `StationHome`, `StationGround`, `StationSky`, `StationSpace`, `StationDiscovery`, `StationNewsHub`, or `StationRadio` component files because SUBJECTS reuses them |
| `StationSubjectNavigator.qml` `legacyPageRequested` / `classicSources` | Legacy index fallback and read-only source lineage | Retire clickable fallback only when all 103 covered and live accepted; **preserve** M0 source provenance and canonical route metadata for audit/recovery |
| `WeatherStationW.openLegacyFromSubject(pageId)` | Returns INDEX to old CLASSIC page | Remove bridge only with new navigation; never leave an inert clickable button |
| `StationSubjectNavigationPreviewPolicy.js` | Historical M1 `sourcePagesForPath`, 103-ID milestone registry, pending/native route presentation, four exact HOME overrides | Retain provenance / milestone accounting or archive deliberately in-place; do not silently reinterpret 6 M0 subjects as 7 workspace families |

### B. Root source owners that **must survive**

- **Global shell** `shell.qml`: the single live `WeatherService`, `SpaceService`, NWS official alerts, persistent last-good cache, bounded live history, event archive, dossier archive and Weather place-cache M6b integration. All currently bind into the same `WeatherStationW`; M28-M does not own or rewrite `shell.qml` or M6b state.
- **Station root** `WeatherStationW.qml`: one `WeatherServices.CelestialVisualService`, `WeatherHomeFavoritesStore`, `WeatherHistoryService`, `SeismicService`, `NowcoastLightningService` and `NwpsRiverService`. Their current `active` expressions include branches on both CLASSIC `currentView` and native SUBJECTS `subjectNavigator.currentPath`. Any cutover must adapt *only* the admission guards and verify no doubled pollers, lost history or extra writes.
- **Original loaded map services**: `StationDiscovery.qml` owns its appropriate `StationDiscoveryService`, GDACS, FIRMS, NOAA HMS, NOAA MRMS, RainViewer and source-specific status where relevant; its native EARTH and WEATHER map instances depend on these. Preserve provider-native event identity, GKG article-mention separation, manual imagery requests and explicit archive/dossier admission.
- **Persistent original HOME**: `StationWorkspaceSurface.qml` mounts one `StationHome`, retaining ranker, 60s relevance watch, local previous-observation snapshots, history and favorites. `WeatherHomeFavoritesStore` remains the original single durable writer. Preserve the state while changing routes and closing/reopening.
- **MEDIA**: `StationMediaSubjectPane` mounts original NEWS, WATCH/CREATORS and Radio. Keep creator saved JSON and explicit recent upload checks; keep shared Hi-Fi/MPD radio transport, memory and favorites without creating a second MPD owner.
- **TOOLS / badge**: `StationToolsSubjectPane`, original source-health and provenance (weather fix, AQI sample clock, NOAA provider sample vs receipt times), cache/archive status, and `StationSubjectSourceBadgePolicy`. Preserve the **one** root header badge and official NWS alert priority; maintain explicit CURRENT/AGING/STALE/CACHE/READING/OFFLINE distinctions.

### C. Navigation / keyboard / terminal collision gates

1. **Current default is CLASSIC**: `WeatherStationW.subjectNavigationOpen: false`; `open()` does not change it. `close()` resets it to false. Thus simply deleting the CLASSIC loader would make a freshly opened or reopened Weather Station blank. A cutover needs a coherent SUBJECTS-first default, open/close behavior and reversible feature gate.
2. **Escape currently returns from SUBJECTS to CLASSIC** rather than closing: the `Keys.onPressed` branch sets `subjectNavigationOpen = false`. Tab, Shift+Tab, Up/Down, Enter and INDEX source navigation also branch on that flag. Rewrite and native-test these as one coherent keyboard contract, not scattered replacements.
3. **Terminal has one verified compositor actor**: `StationTerminal.qml` at the root launches Kitty with mode-specific `weather-screen*` app IDs, geometry verification, input-hole clipping and exact close through Sway. `WeatherStationW.currentView === "terminal"` and `subjectTerminalMode` participate in mode identity and `terminalHoleActive`. Removing CLASSIC `currentView` must preserve native `tools/terminal/star-map` and consoles, app-ID isolation, explicit close and geometry invariants. Do **not** move terminal into an unrelated widget or start a second Kitty.
4. The header `contextTerminalLaunch` currently serves as INDEX when SUBJECTS is active and as original terminal launcher otherwise. Preserve native INDEX and CLOSE affordances and `contextTerminalRequested` gating before removing `currentViewName`.
5. The original `newsMapOverlay`/legacy NEWS→MAP bridge resides in `WeatherStationW` CLASSIC component handlers. SUBJECTS has its *separate, tested* `StationSubjectNavigator.showNewsMentionsOnEarth` route handoff. Preserve article location provenance and explicit clear, but do not keep a stale duplicate bridge pointing at deleted CLASSIC routes.
6. NEWS external viewer geometry is still coupled to CLASSIC `currentView === "news"` in the root `newsViewerViewportRect` / `newsViewerGeometryValid`. Do not delete or promise video until the authorized **Stage Director isolated viewer** contract is integrated, separately tested and accepted.

### D. Verified blockers distinct from migration ledger

| Gate | Evidence at M28-M | Acceptance still required |
|---|---|---|
| Source-route accounting | 103/103 exact original IDs in `WIRED_IN_SUBJECTS`; M28-L PR #1143 53/53 checks green | User checks actual on-screen controls and corresponding data/interaction, not just route names |
| Original collector/state continuity | Existing W1/M28 native and Fedora CI verifies bounded mechanisms | Local Fedora/Quickshell/Sway smoke, open/close and repeated family changes, no blank panes or leaked pollers |
| NEWS WATCH video | `StationChannelScreen.qml` has `playbackAvailable: false`, WebEngine disabled after Quickshell SIGABRT; publisher catalogs and saved creator controls work independently | Separate Stage Director/isolated renderer acceptance or explicit decision to keep safe-mode viewer as a known limitation |
| Terminal | One root `StationTerminal` and native TOOLS launch routes, CI checks | Actual Kitty actor identity/geometry/input masking/exact close, no Sway window collision |
| Location and sample freshness | M28-I/M28-L show provider weather fix, AQI and NOAA sample clocks, without treating receipt as sample time | Test current user's local weather provider data, new M6b location cache, stale/failure and offline fallback |
| Stores/archive | Persistent cache, live history, event/dossier storage and favorites have original owners; explicit archive actions | Restart/reboot readback, no automatic archive write, no corruption or accidental deletion under routes |
| INDEX provenance and recovery | M0 mapping retained; all tracked CLASSIC shortcuts now redundant | Preserve milestone/provenance records in GitHub and a reversible, versioned rollback until final operator acceptance |
| Final DONE | **Not granted** | User final review and explicit approval before CLASSIC UI removal and production activation |

## HOW TO USE

No workstation steps are required for this documentation milestone. For operator acceptance of existing landed SUBJECTS code: after a **separately authorized local update**, open Weather Station → SUBJECTS; inspect HOME QUICK/HISTORY, WEATHER data, COSMOS, EARTH event maps/dossiers, MEDIA NEWS/RADIO/CREATORS, MAGICK and TOOLS health/storage/terminal. Verify the active source badge, MAP source racks and real provider timestamps. CLOSE and reopen; test keyboard and source failure states. Keep CLASSIC available for immediate in-widget comparison.

The proposed future retirement rollout is: (1) make SUBJECTS the default through a reversible **remote PR feature flag**, retaining untouched CLASSIC fallback; (2) CI and operator native desktop acceptance; (3) remove duplicate CLASSIC *presentation* and legacy routing with explicit approval; (4) preserve original provider/service/source files; (5) verify lifecycle, release/rollback and final operator acceptance.

## VERIFY

- GitHub technical checkpoint: `main` at `f964403f7b3913d28017e4b3a3e6bb8327859367`, PR #1143 merged with 53 successful CI checks.
- Audited exact current QML call sites: `WeatherStationW.qml` root source declarations and admission guards, currentView/open/close/escape/mode/loader, one terminal actor and input hole; `StationSubjectNavigator.qml` original provenance/legacy dispatch; `StationWorkspaceSurface.qml` persistent original HOME and six native panes; `StationDiscovery.qml` provider ownership; `StationTerminal.qml` Sway identity; `shell.qml` global source/store injection.
- This is a **source-level audit only**, not a dynamic reference graph or full live execution trace. Untraced conditional loader effects, other repository-level consumers, and workstation-specific runtime dependencies may still exist. A separate code search / smoke rehearsal is required before deletion.

## WATCH OUT FOR

- Do **not** delete `StationHome`, `StationGround`, `StationSky`, `StationSpace`, `StationDiscovery`, `StationNewsHub`, `StationRadio`, `StationTerminal`, or their source services merely because CLASSIC `Component` blocks are later removed. They are reused by SUBJECTS.
- Do **not** remove `currentView`, `subjectNavigationOpen`, or `contextTerminalRequested` without changing dependent admission, keyboard, open/close, input mask and terminal identity logic.
- In the deep INDEX, legacy placeholder language such as “EXACT M28-A/B/C CONTROL CUTOVERS” and a blanket “MAGICK IS A PLANNED INTERPRETIVE SUBJECT” has become stale as later M28 and MAGICK M5 milestones landed. Update UI copy only during a separate reviewed navigation clean-up, without declaring unsupported ephemeris/video features operational.
- The Weather M6b coordinate-keyed place-cache PR landed concurrently with M28-L (files disjoint); the new cache must be included in later location/offline acceptance, not reverted by this older source migration.
- No local machine writes, `git pull`, Quickshell restart, service reload, Sway mutation, cache repair, archive write, backend installation or production activation have been performed by this M28-M audit.

## CHECKLIST

- [x] Recheck live GitHub main and confirm M28-L green/merged.
- [x] Inventory root and original component presentation boundaries.
- [x] Identify services and shared stores that must survive retirement.
- [x] Identify keyboard/open/close and terminal-currentView dependency collisions.
- [x] Record NEWS viewer and Stage Director separation, provider timing and persistence gates.
- [x] Preserve source-migration provenance and proposed rollback.
- [ ] Produce a **separately authorized** reversible SUBJECTS-default cutover PR with all conditional source admission/tests migrated.
- [ ] Run full repository reference search and native Fedora/Quickshell/Sway/Kitty verification.
- [ ] Record operator acceptance of behavioral parity, current safe-mode video exception and backup/rollback.
- [ ] With explicit approval only, remove redundant CLASSIC presentation and bridges; leave native component/source ownership intact.
- [ ] Re-run full CI plus workstation manual tests and obtain final DONE acceptance.

## NEXT

Do **not** treat the M28-L 103/103 source ledger as a request to delete CLASSIC. Next implementation should be a distinct, reversible **SUBJECTS-first default pilot**, retaining all current CLASSIC files and an emergency return path while switching open/close/keyboard/lifetime semantics coherently. Wait for operator approval of the risk change, or explicitly scope it in a new Hospital-compatible Assignment.

## DECISIONS

M28-M is a read-only analysis/documentation checkpoint. The operator remains final authority. Original services, caches, history, archives, source evidence, terminal and safe-mode video boundary are not deletion candidates; no live registration is asserted. Rollback remains the last known green GitHub source plus the untouched CLASSIC UI. Technical checks do not equal final user acceptance.
