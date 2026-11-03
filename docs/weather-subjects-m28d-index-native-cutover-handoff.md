# Weather Station // M28-D deep INDEX native cutover links

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Weather Station / CLASSIC → SUBJECTS Full Capability Migration  
DOCTOR // External Hospital-compatible ChatGPT  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL, no verified Hospital registration  
ASSIGNMENT // Distinguish migrated native SUBJECTS controls from still-pending CLASSIC source links in the deep INDEX  
PHASE // Bounded GitHub implementation and CI  
BASE // main at `9fe2e0a619f511b550e45da550a369b6044f5b81`

## IMPLEMENTATION

M1's `StationSubjectNavigationPreviewPolicy.sourcePagesForPath` historically enumerated which old eight-page CLASSIC screen once contained a control mapped to the selected subject. That is **source provenance**, not evidence that the control remains unmigrated. After merged M28-A/B/C, deep INDEX was still offering redundant **OPEN CLASSIC** pages for already routed controls.

M28-D preserves the historical `sourcePagesForPath` function unchanged and adds two projections:

- `remainingSourcePagesForPath`: old page shortcuts with **only exact separately reviewed M28-A/B/C wired controls excluded**, leaving every unreviewed source page intact.
- `nativeDestinationsForPath`: unique actual subject leaf destinations, carrying mapped-control count and originating milestone for the same exact list.

The explicit first-batch cutover set is:
- M28-A: NEWS mentioned places + NEWS map inspector, now MEDIA → EARTH.
- M28-B: NEWS topic, publisher-country and language/time/region filters, reporting trends, story families and article inspector in MEDIA.
- M28-C: STAR MAP and seven existing context consoles in TOOLS, with the single original Kitty owner.

Deep INDEX now shows **OPEN SUBJECTS // route** buttons for these known destinations; they use the existing navigator's `chooseRoute` and close the INDEX for leaf routes. The `STILL PENDING // CLASSIC` section retains the old page-opening callback for all other mapped families. No collector, cache, archive writer, terminal session manager, page loader, or event provider is changed.

**Important:** a wired native route is not a claim of full parity, actual provider availability, operator acceptance, or live Fedora/Sway Kitty geometry. The separate M1 historical source mapping is retained for audit.

## HOW TO USE

After review, merge and separately authorized desktop deployment: open Weather Station → SUBJECTS → header **INDEX**. Drill to NEWS or TERMINAL groups. For completed M28-A/B/C cutovers, choose **OPEN SUBJECTS // ...**; this enters the selected native subject route without switching to CLASSIC.

For other unresolved source controls, old **OPEN [CLASSIC PAGE]** shortcuts remain available. Selecting **WORKSPACE** returns to the previous workspace as before.

## VERIFY

- Dedicated Node contract `tests/weather/test_index_subject_cutover_m28d.js` verifies the exact 10 reviewed source-control IDs and milestone provenance, preservation of the historical M1 source map, native deduplicated route links, still-pending CLASSIC links, invalid-input rejection, and no shadow process/file owners.
- Workflow `.github/workflows/weather-subjects-index-cutover-m28d.yml` reruns original M0/M1 navigation, W1/W1r layout, and M28-A/B/C route contracts.
- **CI status:** pending until checked on this PR's final head.
- No native Quickshell pointer or Fedora/Sway desktop verification is claimed by this bounded test milestone.

## WATCH OUT FOR

- This is an INDEX shortcut migration, **not** full CLASSIC deletion.
- Original M1 contract uses `status: SPEC_ONLY` in the route metadata even after several live pane integrations. Do not infer capability parity from this old status alone, or mark additional IDs as native without specific tests.
- Unreviewed WEATHER, COSMOS, EARTH, WATCH, RADIO and other control families may still need detailed parity or UI acceptance. Never delete their CLASSIC fallback on the basis of route name matching.
- Another worker owns the independent MAGICK ephemeris work. This branch changes no MAGICK implementation, source service, shared settings, or Stage Director/Kitty compositor code.
- Local Quickshell is not modified or restarted.

## CHECKLIST

- [x] Read Syntagma authority, Hospital and Post-Apollo protocols; inspect current GitHub work.
- [x] M28-C terminal safety fix PR #1116 merged (30 green workflow runs).
- [x] Separate M1 source provenance from post-M28-A/B/C unreviewed source shortcuts.
- [x] Offer known working SUBJECTS route links without auto-launching terminal actors.
- [x] Preserve source pages for every not-yet-reviewed mapped capability.
- [x] Add focused test + workflow and durable handoff.
- [ ] Verify final-head M28-D CI and correct focused failures if any.
- [ ] Review/merge and separately deploy locally.
- [ ] Audit remaining per-control parity, including original INDEX/CLASSIC pages.
- [ ] Obtain operator local/runtime acceptance before final CLASSIC deletion.

## NEXT

Complete M28-D CI, then begin a source-by-source remaining-controls matrix. Advance only additional controls with evidence of real subject-native functionality; transfer missing interactions into their owning subject rather than duplicating the original page. Keep the current original page loader until every required capability and operational dependency is accounted for.

## DECISIONS

Existing operator architecture: one SUBJECTS-first interface with HOME, WEATHER, COSMOS, EARTH, MEDIA, MAGICK, TOOLS. CLASSIC ultimately removed, never retained as fallback; removal gated on complete parity and acceptance. M28-D is intentionally narrower: a staged exact-ID cutover and provenance audit, no local host write, no auto-merge, no provider/store mutation, no new terminal actor and no claim of final DONE.
