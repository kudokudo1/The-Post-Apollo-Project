# Weather Station // M26-F Subject Navigation Continuity Checkpoint

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Weather Station / Subject Navigation Continuity  
**STAFF:** External Hospital-compatible ChatGPT worker, not live-registered  
**ASSIGNMENT:** Verify selected event, in-memory dossier preview, and persisted archive history across CLASSIC MAP and EARTH investigation routes.  
**BASELINE:** `main` @ `0d079505e90c38ce6d58abde3ad8f715227194c6`.

## IMPLEMENTATION

This test-only milestone separates two distinct state lifetimes:

1. **Within EARTH**, `StationEarthSubjectPane.qml` holds a single
   `Loader` containing one `StationDiscovery.qml` while
   `kindForRoute(subjectRoute)==="map"`. Direct transitions among
   `earth/maps/overview`, `earth/investigations/context`,
   `earth/investigations/dossiers`, and
   `earth/investigations/archive` should keep the same MAP object,
   selected event, preview, map viewport and dossier archive store.
2. **Across CLASSIC MAP → SUBJECTS/EARTH**, a different ownership
   boundary applies: in `WeatherStationW.qml`,
   `weatherContentLoader.active: !subjectNavigationOpen`. Opening
   SUBJECTS destroys the loaded CLASSIC `StationDiscovery`. EARTH
   creates its own independent `StationDiscovery` via
   `StationEarthSubjectPane`. Each owns local
   `selectedMapEvent`, `selectedMapGdacsEvent`,
   `selectedMapEarthquake`, `selectedMapHotspot` and derived
   `selectedDossierPreview`. No selected-event snapshot or restoration
   relay exists in the root or subject navigator today.
   Therefore **CLASSIC ↔ EARTH selected-event and unsaved preview
   continuity is NOT currently implemented**. Do not report it as
   working simply because the saved archive is shared.

The test-only native fixture
`tests/weather/fixtures/M26FEarthRouteContinuity.qml` instantiates
the real `StationEarthSubjectPane`, its real
`StationDiscovery`, the existing event-context ActionButton and the
real M25 `WeatherDossierArchiveStore.qml`. A single synthetic GDACS
record `FL:M26D:1` is substituted into the isolated temporary
configuration. The Fedora 44 Xvfb runner sends actual mouse clicks
on the MAP marker and SAVE DOSSIER button. It verifies SAME MAP object,
event/preview identity, viewport continuity, no automatic save through
the four EARTH routes, then one explicit dossier save and saved-history
visibility on the EARTH archive route. It verifies the disk JSON and
no source-native archive write.

The Node audit
`tests/weather/test_dossier_navigation_boundary_m26f.js` records
the **existing CLASSIC↔EARTH blocker**. Its success means the
source-level ownership boundary was classified, NOT that the desired
cross-mode continuity passed. It intentionally marks the missing
handoff as a pending test. No production component is modified.

## HOW TO USE

GitHub CI:
`bash scripts/weather/verify_earth_navigation_continuity_m26f.sh`
and
`node --test tests/weather/test_dossier_navigation_boundary_m26f.js`.

The script runs only inside disposable Fedora CI, with a private
Xvfb virtual display and temporary HOME/XDG directories. It must not
be run against the operator's live Fedora Silverblue tree without
specific local-machine approval.

## VERIFY

Native and audit CI have **not yet been observed at this document's
creation**. Look for these separate classifications:

- Positive EARTH-only marker:
  `M26F_PASS // NATIVE_EARTH_SUBROUTE_CONTINUITY_ONLY`.
- Known cross-family blocker:
  `M26F_BLOCKED // CLASSIC_EARTH_SELECTION_HANDOFF_NOT_IMPLEMENTED`.
- Shared store:
  `M26F_SHARED // PERSISTENT_DOSSIER_STORE_BOTH_VIEW_FAMILIES`.

A green CI job here does **not** close CLASSIC↔EARTH selection continuity.
The missing feature remains an explicit acceptance blocker.

## WATCH OUT FOR

M26-E PR #1091 verified native clicks and distinct identity across four
synthetic providers and merged. That is not route-continuity evidence.

The production change necessary to truly fulfill CLASSIC↔EARTH event
handoff would require a **shared, explicitly owned transient selection
snapshot** at the WeatherStationW boundary, with sourceId + native ID,
timestamp/freshness, bounded preview reconstruction from the destination
provider, no automatic M23 staging and no new FileView writer. The
design must account for invalidated/fetched-out events, gaps between
providers, stale previews, and navigation back. This would modify
shared production navigation seams owned by another Weather worker.
**It is a proposed follow-up requiring scoped owner/operator approval,
not an implementation or accepted design in M26-F.**

The EARTH route smoke uses isolated X11 and synthetic data. It does not
verify production WeatherStationW navigation visually, user Fedora/Sway
focus, Stage Director window containment, real feeds or final operator
acceptance.

## CHECKLIST

- [x] Current GitHub, AGENTS/OPERATE and ownership preflight
- [x] Reconstructed CLASSIC loader and EARTH loader lifetimes
- [x] Source-level cross-mode blocker audit
- [x] Native EARTH route continuity fixture and disposable runner
- [x] CI and recovery documentation
- [ ] Native EARTH route smoke passed
- [ ] External Weather/navigation owner accepts cross-family design
- [ ] CLASSIC↔EARTH handoff implemented and tested
- [ ] Operator desktop/Wayland acceptance

## NEXT

Inspect native CI. Fix only test-fixture/runtime issues within M26-F
ownership. Hand off the CLASSIC↔EARTH state-transfer architecture gap to
its owning worker, preserving separate FileView and provider lifetimes.
Do not add automatic dossier capture or silently change shared
production components under this verification assignment.

## DECISIONS

M26-F is a bounded verification assignment, not permission to modify
`WeatherStationW.qml`, `StationDiscovery.qml` or
`StationEarthSubjectPane.qml`. No live host changes, Quickshell
restart, archive migration, production deployment, PR merge or
Hospital registration are performed by this worker.
