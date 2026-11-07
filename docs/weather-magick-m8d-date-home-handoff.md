# 🏥💜 MAGICK M8d // TASKS Date Steppers and Saved HOME Coordinates

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station MAGICK / Astrology Natal and Transit Input
ASSIGNMENT // Replace difficult text dates with the existing TASKS date controls; auto TODAY; use valid desktop location as coordinate default
STAFF // External DOC / OPEN AI CHATGPT, Hospital-compatible; no live registration verified
BASE // main at c22e2cd923abd56adc7fd8c4e93ad88e3b8a90d3 (M8c PR #1409 merged)
PERMISSIONS // Bounded GitHub-only implementation, no local Quickshell changes, merges, shared settings writes or production activation

## IMPLEMENTATION

**Shared date control:** New `StationMagickUtcDateField.qml` directly reuses `widgets/tasks/TaskDateSegment.qml` and `TaskDateSegments.js` (read-only dependencies) for the exact TASKS per-part numeric boxes, up/down arrows, keyboard Up/Down and typed month/day/year edits. A compact TODAY button replaces only the selected date with the system UTC day at the moment of click. The M8b/M8c astronomical year limit 1901–2099 is enforced on edits and steps; month length/leap-year behavior comes from the unchanged TASKS date code. The date is not saved to TASKS.

**Natal event:** The event overlay now opens with the current UTC date if its date field is empty. Time remains blank until the user enters a birth/event time. NOW UTC sets both event date/time from one instant only when clicked. It retains the explicit calculation step, location inputs, supported zodiac/house selection, session-only privacy and clear-on-close.

**Transit event:** Its old single unstructured YYYY-MM-DD box is replaced with the same three TASKS spinboxes and TODAY control. Opening the transit screen fills the UTC date only if blank. NOW UTC sets date and time together on click; no continuous polling or implicit calculation. Existing planet/aspect/zoom controls are unchanged.

**Location fallback:** Read-only `PlaceRegistry.homePlace` from `qs.services.location` is the ONLY supplied coordinate source. If BOTH user coordinate fields are empty, an already saved, validated manual Post-Apollo Home location becomes the effective latitude and longitude. Yellow AUTO labels display the effective coordinate pair and its source; manual coordinates always override HOME only if BOTH were supplied. Partial manual pairs fail closed, and malformed entered coordinates are never silently replaced. No new location store, provider, GPS poll or side-effect process.

**Important distinction:** The currently available Post-Apollo Place Registry stores **manually selected HOME and temporary EXPLORE locations**. It does NOT establish live geographic device position. This change explicitly labels its fallback **AUTO HOME / SAVED DEFAULT, NOT LIVE GPS**. EXPLORE location and weather-provider/IP location are deliberately not treated as the operator's actual position. If HOME is unset, both coordinate inputs remain required. Genuine current GPS/GeoClue location would need a separately verified location provider, explicit permission and dedicated ownership review.

## HOW TO USE

After an operator-approved merge and local deployment:

1. Weather Station > MAGICK > ASTROLOGY > NATAL > EVENT SETUP. Change month, day or year using arrows / keyboard Up/Down or type a digit. TODAY selects the **UTC** date; NOW UTC fills date plus current UTC time. Date is also initially filled on form open, but time is not.
2. If the Post-Apollo HOME setting has valid coordinates, the empty latitude/longitude inputs display AUTO values and the HOME provenance readout. Press CALCULATE NATAL normally. To override location, type **both** latitude and longitude. A one-sided manual override will not mix with HOME.
3. Once natal is computed, TRANSITS uses the same date steps and TODAY / NOW UTC controls, followed by TRANSIT UTC. Its observer remains the natal chart's verified location, not an unknown live GPS point.
4. If there is no configured HOME, provide both coordinates manually. The UI reports HOME UNSET; it never inserts estimated coordinates or (0,0).

## VERIFY

- `tests/weather/test_magick_date_location_m8d.js` verifies UTC rollover, leap-year adjustments, 1901–2099 bounds, exact TASKS component reuse, both UTC shortcuts, HOME-only default, manual precedence, partial-coordinate refusal, no Google/OS/browser geolocation, privacy and existing JPL calculation routes.
- Existing M8b/M8c/M7a regression tests remain in the `.github/workflows/weather-magick-m8d-date-location.yml` gate. Check exact PR HEAD before claiming completion.
- Native Fedora/Quickshell acceptance still needed: 3 spinboxes + arrows in compact MAGICK layout, current UTC date accuracy around local-midnight transitions, field focus, entered coordinate precedence, HOME defined/unset cases and no spurious calculation.

## WATCH OUT FOR

- HOME is not GPS and may differ from physical current position. The UI never claims otherwise.
- Natal birth location and time are important for a real birth chart: default HOME and TODAY are convenient for a current event, **not necessarily the natal person's birthplace or birth date**. User must check coordinates/time before CALCULATE NATAL.
- UTC is intentionally used. A local calendar day may differ from the current UTC date around local midnight; UTC inputs are what the M8b engine consumes.
- If both coordinates are blank, a change to saved HOME before calculation changes the fallback because inputs are not snapshotted. The effective source and coordinates remain visible before calculate.
- The form does not save birth details to personal grimoire, Journal, TASKS, Weather providers or network. It only reads existing HOME.
- TaskDateSegment remains owned by TASKS; its code is NOT changed. Neither shared PlaceRegistry nor Settings is modified.

## CHECKLIST

- [x] Syntagma and Post-Apollo/Hospital preflight, current GitHub HEAD and open PR review
- [x] Verified TASKS date control source and PlaceRegistry behavior
- [x] Reused TASKS segmented date widget in MAGICK natal/transit
- [x] UTC date default and TODAY/NOW shortcuts
- [x] HOME fallback with clear source label, no assumed GPS
- [x] Explicit/manual coordinates retain precedence and privacy
- [x] Scoped JS regressions and dedicated CI workflow
- [ ] Exact PR-head CI and independent review
- [ ] Operator merge and authorized native desktop deployment
- [ ] Live compact QML field/arrow focus review and HOME fallback acceptance
- [ ] Separate geolocation provider/consent integration, only if operator approves

## NEXT

Check the draft PR's CI; repair any failures; hand off for independent review and operator decision. If the operator later requires *actual live current device position* rather than a saved HOME default, route this to Location/Settings ownership to implement an authenticated permission-aware provider first.

## DECISIONS

Reused existing TASKS controls verbatim, never changed TASKS records. Kept existing M8b/M8c numerical data and private stdin intact. Do not substitute guessed Washington/DC coordinates, an Explore destination, IP geolocation or temporary weather provider position for physical GPS. Operator is final authority for merge, local writes and acceptance.
