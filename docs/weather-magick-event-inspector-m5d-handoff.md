# Weather StationW // MAGICK M5d Source-Backed Event Inspection

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Celestial Visuals
STAFF ROLE // External Hospital-compatible development worker; live registration unverified
ASSIGNMENT // M5d interactive calculated-event navigator and planetary coordinate inspector
BASE // main at 30289136998b9fb388180694c6d90e487724835a
BRANCH // feat/weather-magick-m5d-event-inspector-20261103
PHASE // Draft PR and CI; operator and live-Quickshell acceptance pending

## IMPLEMENTATION

This milestone extends the **existing** merged MAGICK instrument and its pure rendering policy. No other widget, source service, loader, scheduler, environmental discovery, CSS/theme, Weather location, or calculation backend is changed.

Changed:
- widgets/weather/StationMagickCelestialVisualPolicy.js
- widgets/weather/StationMagickCelestialInstrument.qml

Added:
- tests/weather/test_magick_event_inspector_m5d.js
- .github/workflows/weather-magick-event-inspector-m5d.yml

New pure policy functions:
- \`visibleEvents(m,view)\`: clips **only M4-provided event rows** to the current time window, sorts by calculated UTC.
- \`stepEvent(m,view,currentOrdinal,direction)\`: next/previous event navigation within actual visible events, cyclic, with no fabricated events. Empty event windows return no selection.
- \`nearestSampleIndex(m,unixMs)\`: binary search for closest actual M4 sample, ties assigned deterministically to earlier sample, with clamping.
- \`eventAt\` and \`eventLabel\`: expose exact calculated event timestamps separately from sampled visual positions; distinguish conventional longitude aspect crossing, finite-difference **estimated** station timing, and M3 grazing **candidate** (not exact confirmed contact).
- \`bodyDetails\`: source-provided ecliptic longitude, tropical zodiac-reference sector, ecliptic latitude and distance in AU at a selected **sample**. No houses, sidereal readings or invented sub-sample coordinates.
- \`pairDetails\`: M4-calculated longitude separation and conventional aspect labels for the selected sample.

The existing QML instrument gains:
- Clickable EVENT PREVIOUS / EVENT NEXT controls.
- A compact event-status field for source-provided event name, classification and calculated UTC time.
- Distinct highlighting for selected event markers on motion/aspect charts.
- Actual sampled-time locking and planetary inspector, in two compact rows.
- Event choice cleared when normal zoom/pan/manual sample selection changes the active time window.
- Chart area reduced slightly to make room for the additional controls in the same fixed-height instrument; no structural changes to the larger Station or SUBJECTS layouts.

The code retains existing wheel/body selection, graph modes, TIME stepping, UNLOCK/RESET, scroll-to-zoom, drag-to-pan and source provenance display.

## HOW TO USE

This is a GitHub-only UI change. Once accepted, merged and deployed under normal local update procedure:

1. Open Weather Station → SUBJECTS → MAGICK → ASTROLOGY and click CALCULATE.
2. Choose wheel, motion curve or aspect graph.
3. Use ◀ EVENT and EVENT ▶ to cycle the **calculated events visible in the current graph time window**.
4. The event row identifies the kind and exact backend-calculated timestamp; the wheel and body inspector display the **nearest real M4 time sample**, explicitly identified as such, rather than pretending to interpolate the ephemeris.
5. Existing TIME controls step through actual graph points, and UNLOCK or RESET clears event selection.

The panel shows NO CALCULATED EVENTS IN VIEW when a zoomed or selected time window contains no M4 markers. No separate ephemeris download, installer, polling loop, source cache or user-data store is added.

## VERIFY

Dedicated workflow .github/workflows/weather-magick-event-inspector-m5d.yml:
- Unit tests for temporal ordering of unsorted source markers, window clipping, cyclic navigation, nearest M4 sample choice, tie behavior, empty views, classification and exact original degree values.
- QML interaction-wiring tests for actual event buttons, event reset, selected time, mouse/scroll/zoom and no provider duplication.
- Prior M5a, M5b, M5c, default-path M5e, HOME and COSMOS regressions.
- Real JPL DE440s temporal window (Oct 15–Nov 13, 2026) runs the existing M4 CLI in disposable GitHub runner; actual source JSON is passed directly to the M5d visual policy. Verifies genuine events and nearest measured samples.
- CI cannot establish correctness of real Quickshell Canvas paints, clipping, overlap or pointer gestures on the operator's Fedora desktop.

Developer tests:

    node --test tests/weather/test_magick_event_inspector_m5d.js
    node --test tests/weather/test_magick_celestial_visual_m5.js

No end-user package installation or local process restart was made for this GitHub task.

## WATCH OUT FOR

- **Event timestamp is not sample timestamp.** M4 event searches may produce a timestamp between positions actually sampled. M5d visibly labels this distinction.
- M2/M3 event finder uses bounded sampling. It is not exhaustive for narrow tangencies; stations are estimated by finite differences. M3 grazing candidates may be within tolerance without physically touching the exact aspect.
- Ecliptic longitude aspects and tropical sign-sector labels are mathematical/traditional overlays, not 3D conjunctions, apparent local sky, birth chart houses or evidence of supernatural causality.
- For zoomed views, only events between the first and last visible M4 sample are navigable. Changing zoom invalidates event ordinal rather than carrying stale labels.
- The metadata inspector may elide at small widths; live native layout acceptance remains required before treating the interface as polished.
- This change does not install dependencies for users, affect the accepted home-local MAGICK launcher auto-discovery, or change the single root-owned M4 Process.
- PR merge is a separate operator-controlled gate. GitHub CI success is not live Fedora acceptance.

## CHECKLIST

- [x] Current repo main and open Weather PR preflight
- [x] Pure source-backed event clipping, time stepping and closest sample functions
- [x] Instrument event action controls, charts and measured-value inspector
- [x] No new backend, poller, location source or private journal
- [x] Tests and disposable JPL-to-instrument workflow
- [ ] Final PR-head CI verified
- [ ] Operator acceptance / merge
- [ ] Live Quickshell click, scroll, selection and small-window layout verification
- [ ] Further chart legibility polish after native screenshot feedback

## NEXT

After verified checks, review and merge on operator authority, then deploy using established local machine approval. Test EVENT buttons, body and aspect inspectors, plot highlight, source status, small-window geometry and interactions with M5c date/pair/span changes. Continue controlled M5 graphic polish and first-time Backend Manager provisioning in separate tasks, avoiding overlapping changes with other owners.

## DECISIONS

M5d is deliberately an additive, bounded view improvement. Backend-first M0–M4 and source truth remain canonical. No local Fedora write, new installation, runtime restart, live Hospital registration, automatic prediction or user personal-data change was performed.
