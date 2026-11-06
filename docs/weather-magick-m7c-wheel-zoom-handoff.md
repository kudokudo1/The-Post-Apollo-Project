# 🏥💜 MAGICK M7c // Annual Wheel Viewport Recovery

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station / MAGICK / Lunar + Solar annual calendar viewport
ASSIGNMENT // Fix undersized lunar/solar wheels and add usable zoom/pan/focus controls
STAFF // External Hospital-compatible DOC; not live Hospital-registered
BASE // main at dfc60bba61f0bfae66ebb34f05fddad7a4704e11 at start
SCOPE // MAGICK annual QML, pure viewport geometry policy, tests and CI
PERMISSIONS // GitHub-only implementation authorized by operator; no workstation changes or automatic merge

## IMPLEMENTATION

M7b PR #1395 is merged. The operator's native screenshots showed both annual wheels rendered as tiny circles surrounded by unused panel space, with no zoom or pan.

Cause: the Canvas was anchored **below the tall control column and above the details column** and used the smaller canvas dimension to set its radius. Its actual height was only what remained after all those rows, and it had no zoom transform or inverse click hit-testing.

M7c changes only the presentation/interaction path:

- The Canvas now fills all space between the existing top mode buttons and the bottom of the annual panel; controls and detail readings float above it, without whole-page scrolling.
- The initial wheel is **160%**, with 100% FIT and up to 800% maximum. A 420 x 220 px viewport uses an initial wheel diameter of approximately 319 px rather than a smaller leftover-canvas dial. The zoomed dial may be clipped intentionally; use drag-to-pan or FIT.
- **Mouse wheel** zooms about the cursor; **click + drag** pans the diagram. Pan is bounded so the dial stays recoverable.
- Toolbar **− / + / FIT / RESET / FOCUS (BACK)** remains reachable even in Focus. FOCUS hides year/zone/status and readings to maximize inspection; BACK restores them. Year, month and explicit CALCULATE YEAR remain reachable in the normal view.
- Pointer hit-testing applies the exact inverse of the pan/scale transform before selecting lunar days or the closest real solar term.
- Yearly ephemeris, JPL kernel, source handling, daily phase/illumination and 24 solar-term calculations remain untouched. The old M7a forecast and M7b navigation remain intact.

## HOW TO USE

After operator-approved merge and local deployment:
1. Weather Station > MAGICK > LUNAR + SOLAR > CALENDAR > LUNAR YEAR or SOLAR YEAR.
2. Use **+ / −** or mouse scroll over the wheel to zoom. **FIT** shows the complete circle, **RESET** restores the default magnification and centered view.
3. Click-drag the wheel to pan in zoomed view. Click a Moon date or solar term to inspect its real data. Double-click the wheel to fit.
4. Click **FOCUS** to remove other information rows and inspect more of the dial. Click **BACK** to return. Open **ZONE** only when changing the explicit IANA timezone.

## VERIFY

- New tests/weather/test_magick_calendar_viewport_m7c.js exercises full-viewport radius, pointer-invariant zoom, min/max limits, pan bounds, inverse date selection, QML handlers, preservation of numerical source.
- New .github/workflows/weather-magick-m7c-viewport.yml runs that test and existing M7b/M7a regression tests.
- GitHub CI and native Qt/Quickshell visual and interaction verification are separate gates. Screenshots are evidence of the *previous* defect, not evidence of this patch running.
- No local Fedora / Quickshell restart, configuration edits or installs were performed.

## WATCH OUT FOR

- High zoom crops portions of the circle by design. FIT and RESET are recovery controls.
- At very high zoom, a small screen cannot show all 365/366 day markers simultaneously; use MONTH to see individual daily Moon discs.
- Focus mode hides astronomical readout labels but retains the zoom toolbar. BACK restores the readout.
- Native cursor behavior, QML loading errors and exact compact geometry require operator review after deployment.
- Source timezones remain explicit; global Settings timezone and normal Planner/Calendar ownership remain outside M7c.

## CHECKLIST

- [x] Recover current main and verify M7b merged
- [x] No open MAGICK PR collisions at preflight
- [x] Isolated M7c branch
- [x] Full-viewport Canvas and compact floating controls
- [x] Wheel at pointer, drag pan, plus/minus, Fit, Reset, Focus
- [x] Inverse-hit selection based on actual dates
- [x] Pure JS geometry checks and CI
- [ ] CI verified
- [ ] Independent review and operator merge
- [ ] Native Quickshell zoom/pan/labels and overlap inspection
- [ ] Operator acceptance

## NEXT

Verify M7c PR CI against its exact final head, repair failures if needed, and separately authorize merge/deployment. After native review, adjust text/label density and mouse/keyboard behavior from actual panel screenshots without expanding into COSMOS or global Calendar ownership.

## DECISIONS

This is a viewport fix, not a redesign of the numerical ephemeris. Preserve the M7b astronomy source and the current non-scrolling MAGICK navigation. Operator controls merges, live desktop changes, and acceptance.
