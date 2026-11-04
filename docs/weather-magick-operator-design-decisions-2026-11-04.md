# Weather StationW // MAGICK Operator Design Direction
## Confirmed preferences and roadmap reconciliation // 2026-11-04

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`
**ROOM:** MAGICK design and research roadmap (documentation only)
**ROLE:** External Hospital-compatible ChatGPT, no verified live Hospital registration
**ASSIGNMENT:** Record the operator's explicit choices and reconcile with existing plans *before* implementation
**BASELINE:** `main` at `3435a5e64656c09717737515cd6afe826dd2a126`
**AUTHORITY:** The operator made the choices below. This document records preferences and architectural constraints; it does not authorize implementation, merging, local deployment, or overriding another worker.

## IMPLEMENTATION // Recorded operator decisions

### D1. Two primary visualizations, linked

**Operator choice:** "Both as linked modes."

1. **Relationship network:** nodes represent selected celestial bodies; edges represent measured or computed angular relationships and their explicitly configured aspect interpretation. Selection, filters, and time navigation remain inspectable. This is *not* a physical orbit rendering.
2. **Spatial solar-system view:** actual position geometry at the same user-selected time, with a clearly stated observer, coordinate frame, projection, scale and epoch. This is *not* a zodiac diagram or a graph of astrological influence.
3. Both views synchronize a shared selection contract: chosen UTC instant or source sample, body IDs, current event, inspection focus and available source provenance. Each viewer computes/displays its **own valid coordinates** for the selected epoch. Never copy a geocentric longitude into a heliocentric position diagram or invent 3D coordinates from a 2D aspect chart.
4. The existing ZODIAC, MOTION, ASPECTS and RELATIONS instruments remain useful smaller views within this program; they are not discarded.
5. Map/slider navigation, zoom, pan and click inspection retain the established tactile Post-Apollo interaction grammar. When changing modes, preserve selected context where the destination mode has a valid source representation, and display a transparent unavailable state otherwise.

### D2. Interpretation priority is ordered

**Operator choice:** First Western tropical astrology; second Hellenistic; third Vedic because its sign/date conventions will differ from those familiar to many Western users.

- **Always available foundation: OBSERVATION.** Actual ephemeris observations/calculations, source names, time and frame, valid uncertainties and unsupported states stay visible without selecting an interpretive lens.
- **Priority 1: modern/contemporary Western tropical astrology.** First fully implemented, sourced interpretive lens. Tropical zodiac is the initial sign convention in MAGICK. No unspecified house system, orb set, delineation, or school is silently selected.
- **Priority 2: Hellenistic/traditional astrology.** Distinct *Western* tradition layer, with its own terminology, methods, evidence and chosen historical/modern source editions. Treat this as a second selectable tradition, not a duplicate of modern Western interpretations or a new astronomical ephemeris. Record exactly which Hellenistic rules and house/sect/lot conventions, if any, have been implemented.
- **Priority 3: Vedic astrology / Jyotisha.** Later separate sourced lens, typically involving a sidereal reference. Do not treat different Western/Vedic sign labels or calendar ranges as errors in celestial observations. At the **same UTC instant**, tropical versus sidereal sign assignments may differ because of the reference definition; named ayanamsa and any further calendars/house or nakshatra conventions must be explicit. Do not silently replace existing tropical dates, labels or readings. If a precise convention has not been selected and implemented, show unavailable rather than making one up.
- An astronomical event is not evidence of spiritual/psychological causation. Keep each named tradition's interpretation and citations separate from the source-calculated geometry.
- Every lens must include ID, source/tradition and edition/version as appropriate, zodiac/frame convention, input observation IDs/times, claim type, cited references and a clear distinction between disagreement of conventions and disagreement about factual measurements.
- Other proposed MYTHIC/CULTURAL, MAGICAL/CORRESPONDENCE and SECULAR/REFLECTIVE lenses remain optional later directions, not newly authorized implementations. Tarot and personal research are not promoted by this decision.

### D3. MAGICK HOME is a combined overview

**Operator choice:** "A combined overview."

A useful initial information hierarchy, subject to UI layout acceptance:

1. **NOW / CONDITIONS:** source-backed current celestial positions, lunar/solar phase state where available, selected bodies, timestamp, freshness and provenance. "Current" must not imply a live stream if a calculation is on-demand.
2. **CHANGES / NEXT:** significant calculated alignments, motion/station changes and upcoming source-backed events, shown with time, event classification and confidence/search limitations; no fabricated predictions or omitted unknown states.
3. **MEANINGS / SELECTED LENS:** the chosen tradition's sourced commentary about the currently selected event or body. Until a lens is implemented, explicitly show "interpretation not connected" rather than invented text.
4. **INSPECT:** one coherent jump into the linked relationship network/spatial mode plus existing wheel, graph and history details. Preserve selected event/body/time when possible.

This is one *combined* launchpad, not three competing homes. Detailed proportions, favorites and layout remain subject to an operator visual pass and neighboring SUBJECTS ownership.

## HOW TO USE // Reconciliation against the actual current architecture

| Existing plan or implementation | Reconciliation / requirement |
| --- | --- |
| `docs/weather-subjects-visual-intelligence-future-worker-roadmap-2026-11-03.md` section 7, observational source plus selectable named interpretive lenses | **Compatible.** This document fixes the first three astrology priorities and keeps the scientific foundation mandatory. Proposed lens registry/text schema remains to implement. |
| Same roadmap section 6, planetary wheel, change timeline, overview, optional houses/charts and traditional hours | **Compatible.** M5 already delivers part of the graphics; do not mistake that for a full natal/event chart, house system or lens implementation. |
| Same roadmap section 8, V3 lens contract and V4 planetary graphics | **Updated order within MAGICK:** source architecture already advanced M0–M5; finish actual data breadth, then linked views, then tradition-specific interpretation in the operator's stated order. Do not undo other SUBJECTS tracks. |
| `scripts/weather/celestial_contract.py`, `celestial_solver.py`, `celestial_dynamics.py` | Existing geocentric/topocentric/heliocentric position *contracts* and astronomical numerical work remain authoritative, with explicit frames/time and physical-source barycenters. |
| `scripts/weather/celestial_visual_data.py` | Visual model accepts 1–4 bodies but **event search is constrained to at most 2**. Supports pairwise relationships and sample timeline, **not** the proposed full multi-body event network today. |
| `services/weather/CelestialVisualQueryPolicy.js` | MAGICK frontend currently offers six fixed **two-body** presets. M6/M7 must explicitly expand selection/query/visual model as needed; don't claim an arbitrary planetary network is already wired. |
| `StationMagickCelestialInstrument.qml` and `StationMagickCelestialVisualPolicy.js` | Existing wheel, motion, aspects, separation dial, neon zodiac and draggable timeline are proven presentation foundations. Preserve source accuracy and accepted controls rather than rebuilding them for decoration. |
| `StationMagickSubjectPanelPolicy.js` and `StationMagickSubjectPane.qml` | Current descriptions correctly say interpretation is NOT CONNECTED. **Do not change that statement** until an actual sourced lens has been built and independently verified. The observational MAGICK overview is not yet the intended full combined overview. |
| Other Weather/CLASSIC/Stage Director/CPU++ workers | Not within this assignment. Reuse shared location/time/settings and coordinate for the HOME seam rather than implementing a duplicate store, clock, viewer or provider in MAGICK. |

## VERIFY // What exists and what does not

**Verified in GitHub source (2026-11-04):**
- M0–M5j numerical/visual modules and tests; default established MAGICK source-backed instrument; finite pairwise aspect measurement and timeline.
- M4 accepts up to four bodies for plotted positions/relationships, but requests with event search cannot exceed two bodies.
- Six hardcoded two-body presets in the MAGICK UI.
- MAGICK's named interpretive views are scaffolded; actual interpretive engine, transits/natal/house calculation system and journal storage are not connected.
- No open Weather/MAGICK PRs were returned from the current open-PR audit.

**Not verified or not yet implemented here:**
- Fully linked relationship network and physically meaningful solar-system spatial rendering at synchronized time.
- Selected Western tropical lens with sourced content, Hellenistic lens, or Vedic sidereal calculation/lens.
- An integrated, accepted combined MAGICK home.
- First-time end-user JPL/Skyfield automatic provisioning, native UI review of future modes, and full history/annotation/privacy features.

**Source and operator boundaries:** GitHub-main inspection is not a claim about the operator's local worktree, live Quickshell revision, or live Hospital registration. Previous user screenshots show a working M5 wheel and improved input, not future M6–M9 products.

## WATCH OUT FOR // Claims and conventions

1. **Reference frames differ.** The heliocentric spatial depiction must use the corresponding origin and geometry; the traditional ecliptic-longitude network may be geocentric. Linking by timestamp is not permission to reuse the wrong position values.
2. **Modern Western and Hellenistic are related.** Hellenistic is historically a Western astrological tradition. The two priority slots mean contemporary Western first, followed by a distinct traditional/Hellenistic reading and source model.
3. **"Contradictory dates" clarification.** Calendar dates and sign labels may differ with sidereal versus tropical zodiac definitions/ayanamsa. Explain the convention instead of claiming one system's astronomical measurement is false.
4. **Tradition is not source science.** Interpretations are source-based cultural/traditional claims; they do not alter planetary ephemerides or provide established evidence of causation.
5. **No silent defaults.** Ayanamsa, house system, reference text/edition, orb conventions, body/nodal assumptions and user-specific birth data require their own decisions and explicit validation.
6. **No scope expansion.** No tarot generator, observational journal, 3D engine, new time/location store, browser navigation, or production activation is authorized by this design-record task.

## CHECKLIST // MAGICK milestone gates and decisions still open

- [x] Record OPERATOR: two linked visualization modes.
- [x] Record OPERATOR: contemporary Western tropical > Hellenistic > Vedic/Jyotisha interpretive priority.
- [x] Record OPERATOR: one combined MAGICK home.
- [x] Reconcile with M0–M5j numerical/visual services and older SUBJECTS visual intelligence roadmap.
- [ ] **M5 freeze:** preserve the last accepted live wheel/drag behavior; document current runtime issues and close visual regressions.
- [ ] **M6 source breadth:** decide essential additional bodies/nodes and event searches; verify numerical source/frame and historical completeness.
- [ ] **M7 linked visualization design:** specify shared time/body/event selection and correct coordinate conversions, then bounded network and spatial representations with native acceptance.
- [ ] **M8 lens architecture:** select first Western textual/edition sources, permitted interpretations, exact orb/house settings if needed, and no-data behaviors. Build Western first; source-reviewed Hellenistic follows; Vedic follows after explicit sidereal/ayanamsa convention.
- [ ] **MAGICK combined HOME:** arrange NOW, CHANGES and SELECTED LENS/INSPECT affordances without duplicate provider owners; final design/acceptance with operator.
- [ ] **M9 opt-in human-observation research:** separately decide participant consent, data fields, historical snapshot fidelity, encryption, retention, deletion/export and experiment framing. Not authorized for this milestone.
- [ ] Any future native deployment, cross-domain UI seam edit and merge require their normal approval/ownership gates.

## NEXT

This **documentation-only** decision record may be reviewed and merged under operator authority. The first planning activity after it is to convert M6/M7 into a bounded technical spec with source/body/event coverage and a two-view synchronization contract, then obtain operator design acceptance before visual construction. In parallel, prepare a short sourced bibliography of modern Western tropical material and candidate Hellenistic references, but do not implement or fabricate lens output.

The next meaningful operator questions should concern **visual semantics** (what nodes and connections mean) and **specific tradition/source conventions** (not the whole Weather Station or other teams' work). Choose the simplest useful first network and spatial views with a clear definition of done.

## DECISIONS

Recorded user selection: "Both as linked modes"; "Western tropical astrology"; "A combined overview"; "Hellenistic to serve as 2nd priority and Vedic to come after because of the contradictory dates to what most people are used to."

These are confirmed **operator design preferences**. They fix direction and order, not code readiness, finished astrological claims, specific source texts, implementation permissions, or final acceptance. No source code, desktop files, running processes or live systems were modified by this documentation assignment.
