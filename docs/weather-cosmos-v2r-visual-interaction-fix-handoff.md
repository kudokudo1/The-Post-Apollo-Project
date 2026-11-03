# Weather Station // COSMOS V2r clickable visual controls

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station / COSMOS V2 interaction repair
STAFF // External Hospital-compatible ChatGPT doctor, not live registered
STATE // GitHub implementation, CI and local acceptance separate
ASSIGNMENT // Correct inert Moon phase markers and inaccessible Sun graph controls

## IMPLEMENTATION

The original eight Moon phase markers were Rectangle elements with no input handler. Their button-like appearance was misleading. V2r replaces them with reusable ActionButton controls, unique short labels and actual selection callbacks. Choosing a phase shows an educational REFERENCE explanation; it never changes the current recorded Moon phase, illumination, image, date or provider state. CURRENT clears the selection. Clicking the Moon disk inspects the current category if one is verified.

The Sun plot previously required a calibrated sunrise offset and had only the pointer-sensitive chart surface. It now has explicit 00 / 06 / 12 / 18 / NOW controls, click-to-lock, hover, UNLOCK and a MouseArea preventing the surrounding Flickable from stealing input. NOW requires a valid provider local observation minute. Unavailable cases distinguish missing date, missing coordinates and unavailable civil offset.

The Sun model now reads the existing Weather Station provider-local astronomy date and moonCivilOffsetMinutes property, which already prefers the Open-Meteo civil offset and falls back to sunrise calibration. This adds no new collector, writer, clock or ephemeris. Existing COSMOS routing, HOME ownership, CLASSIC, Stage Director and terminal remain untouched. The visual height increases to 304px; it remains inside existing scrollable StationSky.

## HOW TO USE

After a separately approved local installation, open SUBJECTS > COSMOS > MOON. Select NM/WC/FQ/WG/FM/NG/LQ/NC to read a reference explanation, click the Moon disk for the current phase, and CURRENT to clear. The provider-based Moon graphic and values do not change with reference selections.

Open SUBJECTS > COSMOS > SUN. Click 00/06/12/18/NOW to inspect a modeled local time, or hover/click the solar curve and UNLOCK afterward. If the model is unavailable, a specific input prerequisite appears instead of a silent dead click.

## VERIFY

Old V2 numerical source contracts and new test_cosmos_visual_interactions_v2r.js check the actual button handlers, pointer properties, source state preservation, fallback date and civil offset, and no new providers. Full COSMOS/WEATHER/teardown checks must pass. GitHub CI cannot verify a Qt Canvas frame or actual pointer hitboxes; the operator's Fedora Quickshell visual test remains pending.

## WATCH OUT FOR

Moon markers are educational categories, not dated future predictions, magic correspondences or an ephemeris. Sun altitudes are calculated and may still be unavailable for invalid input. The alternate civil offset is inherited from the existing location service. If every SUBJECTS control is still unresponsive after this change, inspect shared pointer containment and the Station window input surface rather than patching individual visuals. Those shared seams have other owners.

## CHECKLIST

- [x] Source/ownership and policy preflight
- [x] Actual Moon buttons and selected phase reference text
- [x] Solar presets, pointer protection, unavailable input explanation
- [x] Existing date/civil time data reuse
- [x] Source-level regression test and CI wiring
- [ ] Latest branch-head CI and merge verification
- [ ] Actual Fedora Quickshell pointer and visual acceptance

## NEXT

Verify all CI green, merge in existing Weather repository workflow, then test Moon reference buttons, Sun presets and chart click separately on the real desktop. If pointer events still fail globally, ask the input/Stage Director owner to investigate common containment.

## DECISIONS

Narrow interactive usability repair only; preserve original scientific data and source ownership. No local machine writes, no production activation, no live Hospital registration.