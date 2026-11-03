# Hospital // COSMOS V2b desktop 0/5 USNO row reconciliation

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station // Visual Intelligence, V2b live verification
STAFF ROLE // Nurse 2 (external Hospital-compatible, no live Hospital registration)
ASSIGNMENT // Restore actual USNO event markers in the V2b planetary event clock
PHASE // Draft GitHub correction; local desktop retest pending
SOURCE // Operator screenshot 2026-11-03 16:05 desktop clock

## IMPLEMENTATION

The screenshot shows the V2b COSMOS clock panel itself on the current SKY // ALL route. Its source badge reads USNO RECEIVED, but the graph reports **0/5 DATED PLANETS** and all five lanes are blank; the original adjacent USNO rise/transit/set cards below have five populated planet records.

A source inspection found a plausible cross-QML boundary fault: the new policy's \`clockRows\` discarded \`providerRows\` outright if \`Array.isArray(providerRows)\` was false. QML \`var\` values arriving from a different component may be indexed/list-like without satisfying that JavaScript check, even though QML Repeater renders the same rows. This is a source-level hypothesis, **not** direct live Qt proof.

Narrow remedy on a separate branch:
- Permit only bounded, length-indexed array or QML list-like inputs (0–32 records), rejecting strings and malformed sizes.
- Normalize provider planet name/date text for exact matching; still validate the requested real YYYY-MM-DD date and require source row's date to match.
- Parse exact HH:MM text from QString-like values without permitting invented or invalid times.
- Handle QML-like event collections in filters and counts; source rows never become synthetic tracks.
- Keep original USNO service, existing StationSky mount, shared navigation, COSMOS and CLASSIC untouched.
- New dedicated test fixtures replicate a non-Array list-like QML crossing with five planets, wrapped strings, invalid dates, and unbounded/invalid inputs.

## HOW TO USE

After CI and authorized merge/deployment, visit Weather Station → SUBJECTS → COSMOS → SKY // ALL, scroll to PLANET CLOCK; or INDEX → COSMOS → PLANETS AND STARS → PLANET RISE/SET. The count should reflect actual source-dated events; the R/T/S filters and marker selection should now have visible inputs.

## VERIFY

Observed in operator screenshot: current graph exists and visually responds to event filter selection; source says received, original cards populated, new clock shows 0/5. Not observed: any functioning graph markers, selected detail or actual QML list runtime type. Automated tests simulate list-like \`var\` input, enforce no loss of valid rows and no acceptance of wrong dates. Repository V2b GitHub CI triggers from modified policy/tests. Passing Node tests **cannot prove** a Qt native list-conversion regression is eliminated until the operator retests.

## WATCH OUT FOR

No production or local write was performed by this correction. Do not silently relax date checks to force markers, fabricate a planet path, or create duplicate USNO requests. If count remains 0/5 after deployment, inspect native diagnostic prints of \`typeof providerRows\`, \`providerRows.length\`, and the first row's name/date/status (with safe bounded logging) before further changes. Maintain W2/W28 HOME/CLASSIC ownership and MAGICK's separate JPL ephemeris lane.

## CHECKLIST

- [x] Inspect supplied desktop screenshot
- [x] Verify merged V2b graph and active raw provider cards in source
- [x] Identify likely strict Array.isArray cross-component compatibility issue
- [x] Bounded list normalization patch and regression fixtures
- [ ] Pull-request head CI green
- [ ] Native QML deployment / 5/5 source count and clickable event markers verified
- [ ] Operator acceptance

## NEXT

Review CI and PR, merge only under existing scoped authorization, then retest the live graph. If failure persists, investigate actual QML-native value types and exact provider row/date fields instead of bypassing provenance checks.

## DECISIONS

Preserve single-source USNO data ownership and exact civil-date validation; use a small list adapter instead of touching the shared migration navigator. No final DONE claim.
