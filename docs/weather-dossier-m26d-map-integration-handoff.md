# Weather Station // M26-D MAP Selection to Dossier Native Smoke

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Weather Station / MAP-to-Dossier Integration Verification  
**STAFF:** External, Hospital-compatible ChatGPT (not registered live).  
**ASSIGNMENT:** Verify the existing real `StationDiscovery.qml` event-marker-to-dossier chain in disposable Fedora CI, without modifying any production source.  
**BASELINE:** `main` @ `77e74fba2f5cfe8ef70216d45322b1544724f9ab`.

## IMPLEMENTATION

M26-C PR #1083 merged, having verified the real card and shared
ActionButton in Fedora Quickshell 0.3.2 with native X11 mouse clicks.

This **M26-D** adds a full MAP-level native test using:
- Unmodified production `StationDiscovery.qml` and related Weather
  components, plus the actual M22 preview, M23 admission, M24 codec and
  M25 FileView dossier store.
- A **test-only synthetic GDACS provider** substituted *inside a copied
  temporary configuration directory*. The production
  `services/weather/GdacsService.qml` is not modified.
- A real Quickshell `FloatingWindow` in isolated Fedora 44
  `Xvfb` and native `xdotool` pointer actions.
- A disabled provider polling state (`stationOpen:false`) to avoid
  loading live source data. The synthetic GDACS record is an event
  with provider-native ID `FL:M26D:1`, NOT a real emergency alert.

The test attempts this sequence:

1. Confirm synthetic GDACS event appears as a real projected MAP marker
   and no dossier file exists.
2. Scroll the actual MAP viewport to the marker; click it with native
   X11 pointer input, not a direct property setter.
3. Assert actual `selectedContextSourceId`, normalized event ID,
   cross-domain dossier preview, M23 review and explicit capture
   availability; still no dossier automatically saved.
4. Scroll to the actual nested `StationEventContextCard` and
   left-click its real `SAVE DOSSIER` ActionButton.
5. Require actual M25 FileView callback and one on-disk dossier record,
   correct provider-native identity and non-incident semantics, and
   no change to the independent source-native archive.

## HOW TO USE

CI-only runner:

`bash scripts/weather/verify_dossier_map_fedora_m26d.sh`

It creates temporary HOME/XDG directories and an isolated X11 server
and deletes the test tree on exit. No personal computer changes,
production `shell.qml` startup, live user feeds or compositor input.
Not an operator desktop command without separate approval.

## VERIFY

At PR creation, **M26-D CI is unverified**. It must show:

`M26D_PASS // ACTUAL_MAP_SELECTION_TO_DOSSIER_STORAGE`

A passed M25 regression alone is not sufficient. If the full
StationDiscovery instance fails due to missing Qt dependencies or
unsupported graphics in CI, report that actual failure, not a
production defect. Narrow fixes should remain in fixture/CI scope.

## WATCH OUT FOR

This tests one source-native GDACS event through the real MAP
controller. It does not test USGS, EONET or FIRMS markers individually,
provider network feeds, full WeatherStationW menu navigation, Wayland
input, Stage Director hosting, local graphics drivers, visual layout
acceptance, retention/backup policies or power-failure durability.

Production weather sources and services remain owned by their existing
workers. This branch only adds a fixture, synthetic test source,
sandbox script, CI workflow and handoff documentation.

## CHECKLIST

- [x] M26-C merge and current source reviewed
- [x] Existing MAP selection and dossier bindings inspected
- [x] Isolated native full-MAP fixture and synthetic GDACS provider
- [x] Disposable CI runner and source contract
- [ ] Full M26-D native CI success
- [ ] Operator merge and final acceptance
- [ ] Real Wayland/Sway and full menu acceptance

## NEXT

Run CI, resolve only observed test integration gaps, and hand off
the result. If production source fails, preserve the evidence and
escalate before modifying shared Weather code.

## DECISIONS

No production code changes, local machine writes, shell restarts,
live service registration, automatic capture, cross-source event merge
or PR merge by this test assignment.
