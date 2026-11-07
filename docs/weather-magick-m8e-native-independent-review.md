# 🏥💜 MAGICK // Independent Code Review and Isolated Native Verification

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK > Natal/Transit verification
ASSIGNMENT // Independent source audit and actual QML component preflight before transit timeline expansion
STAFF // DOC, external OPEN AI / CHATGPT (Hospital-compatible, not live registered)
BASE // main a43421f605d7aa187a092461585ba7dd0169002d
BRANCH // verify/weather-magick-m8e-isolated-native-20261107
PR // #1411, draft, unmerged at this checkpoint
PERMISSIONS // GitHub source/test/docs only; no workstation writes, live installation, restart, production activation or merging

## IMPLEMENTATION

Independent audit examined the merged M8b, M8c and M8d source rather than relying solely on PR descriptions:
- M8b's `celestial_natal_chart.py` calculates topocentric apparent JPL positions and constructs a strict source signature; it is invoked via `CelestialNatalChartService.qml` with a request over stdin instead of leaking event details into process arguments.
- M8c's `StationMagickTransitComparisonPolicy.js` requires matching engine, exact ephemeris SHA-256, observer coordinates, date-specific true ecliptic, tropical model and exact NAIF identities before computing cross-chart aspect tolerances.
- M8d's `StationMagickUtcDateField.qml` reuses TASKS month/day/year controls; `StationMagickEventChartSetupPane.qml` reads only the manually saved `PlaceRegistry.homePlace` when the coordinate pair is empty. It does not claim live GPS.
- Existing GitHub CI was previously source-contract/synthetic. It did not instantiate the actual Qt components or verify live kernel output.

Added a disposable **real Quickshell offscreen** integration fixture and Linux script:
- `tests/weather/fixtures/M8eNativeMagickShell.qml` tests true Qt property bindings and invokes DATE/TODAY, verifies modal date initialization, manual HOME override, private field clearing and transit NOW.
- `scripts/weather/verify_magick_native_m8e.sh` constructs a fresh /tmp HOME, XDG environment and Quickshell config, copying only repository source into it; no access to ~/.config/quickshell, private data or the live Sway session.
- `.github/workflows/weather-magick-m8e-isolated-native.yml` installs real Debian Quickshell and the needed QtQuick.Effects / Qt5Compat QML modules, then runs the fixture and preserved M8d/M8c/M8b tests.

## HOW TO USE

GitHub review: open PR #1411 and expand `MAGICK M8e isolated native Quickshell acceptance preflight`; locate the marker `M8E_NATIVE_PASS // REAL_QML_DATE_HOME_TRANSIT_COMPONENTS`.

Native Fedora operator acceptance (separate from this CI) must use the installed Post-Apollo Weather Station UI:
1. MAGICK > ASTROLOGY > NATAL > EVENT SETUP: confirm month/day/year arrow buttons, TODAY UTC, NOW UTC.
2. With a deliberately configured HOME: leave both coordinates empty and confirm AUTO HOME indicator. With only one manually entered coordinate, calculation must be unavailable. Enter both manually for override.
3. Use the configured local JPL kernel to calculate a real natal chart, then TRANSITS with manually chosen UTC time. Confirm wheel zoom/pan, source status, and input clearing on exit.
4. Capture native screenshots and any QML/runtime errors; operator decides final acceptance.

## VERIFY

- Exact real-offscreen QML job at initial review iteration: **PASS** after two fixture/environment corrections:
  - First failed because the test container omitted `QtQuick.Effects`, resolved by installing actual Debian QML modules (test environment issue).
  - Second failed because fixture Items were unparented in ShellRoot and therefore effectively invisible. Resolved by parenting them inside an offscreen `Window` (fixture issue, not production date bug).
- The corrected actual-QML run and related M8d/M8b/M8c unit tests passed in GitHub Actions, using synthetic HOME and no user data.
- Recheck final PR-head workflows after this documentation change. No real DE440s ephemeris execution or Fedora/SwayFX UI has been tested by this session.

## WATCH OUT FOR

This is **native offscreen Quickshell/Qt in Debian**, not a claim that the operator's running Fedora Silverblue/Post-Apollo instance is installed, current, visually correct or accepted. The fixture does not click real pointer coordinates, verify panel clipping/animation or run the user's JPL kernel.

The M8c “transit” is currently a *single selected UTC snapshot*, not a time series or an exact aspect-contact search. Its angular orb labels are astrological conventions derived from measured coordinates.

Do not reinterpret saved HOME as current device GPS. Avoid storing natal/event information in test logs, process argv, caches or CI artifacts.

## CHECKLIST

- [x] Verify M8b/M8c/M8d merged into main
- [x] Check open MAGICK/transit PR collisions
- [x] Independent code review of source, privacy and provenances
- [x] Add isolated native QML fixture with actual components
- [x] Correct disposable Qt imports and parent/visibility setup
- [x] Native offscreen component test passes
- [ ] All final exact PR-head CI checks after documentation
- [ ] Independent second reviewer, operator merge decision
- [ ] Operator Fedora native UI + actual DE440s acceptance
- [ ] Next separate M8f transit timeline and numerical aspect-contact work

## NEXT

Keep PR #1411 open for review; do not merge or alter running desktop without operator authorization. The M8f analytical timeline/event finder can be built separately behind its own draft PR as isolated code/tests, but live UI connection and final acceptance remain gated by Fedora native verification.

## DECISIONS

A synthetic PASS is not a native desktop PASS. Reuse the existing M8b JPL engine and preserve all sensitive session-only inputs. Final completion and production merge belong to the operator.
