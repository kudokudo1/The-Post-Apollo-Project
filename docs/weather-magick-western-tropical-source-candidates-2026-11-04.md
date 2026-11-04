# MAGICK // Western Tropical Lens Research Catalogue
## Candidate references and claims review // November 4, 2026

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Research
ROLE // External Hospital-compatible documentation worker
ASSIGNMENT // Identify source candidates for MAGICK's first Western tropical interpretive lens, with Hellenistic held as second priority and Vedic/Jyotisha third
PERMISSION // Research only; no interpretive engine, generated reading, code extraction, copyrighted text import, personal journal or new data collection
STATUS // Candidate bibliography, **NOT** an operator-approved canonical library
RELATED // docs/weather-magick-operator-design-decisions-2026-11-04.md and docs/weather-magick-m6-m7-celestial-events-linked-time-spec-2026-11-04.md

## IMPLEMENTATION // Verified source candidates

### Tier 1: Western tropical candidate reading list

**1. Sue Tompkins, Aspects in Astrology: A Guide to Understanding Planetary Relationships in the Horoscope**
- Primary relevance: readable, organized treatment of aspects, how different planetary pairings are interpreted, and why a single aspect should not be read without the rest of a chart.
- Source validation: publisher catalog lists Destiny Books / North American Edition (2002), ISBN 9780892819652; author's own site records first publication in 1989 and later editions.
- Good first research task: build a **metadata table** of recognized major aspect types and candidate interpretation topics; attribute each claim, edition, page/section and limitations before any prose is displayed. Do not lift the book's delineations wholesale.
- Important limitation: this source emphasizes natal chart interpretation. Current MAGICK data are primarily two celestial bodies at selected UTC dates, **not** automatically a birth chart. The UI must not present natal-specific statements as a generic "sky now" reading.
- Publisher: https://www.simonandschuster.com/books/Aspects-in-Astrology/Sue-Tompkins/9780892819652
- Author: https://suetompkins.com/books/

**2. Sue Tompkins, The Contemporary Astrologer's Handbook**
- Primary relevance: broad foundation in planets, signs, houses, elements, modes, aspects, chart synthesis and other contemporary interpretation conventions.
- Source validation: author's site describes its scope and UK publication by Flare Publications.
- Good research task: identify the minimum vocabulary MAGICK should explain before surfacing interpretations: planet meaning, aspect category, sign quality, chart context, house/angle requirement, and differences between mathematical observation and traditional reading.
- Important limitation: a textbook's holistic birth-chart methodology does **not** prove that a pairwise current-time astronomy diagram can be turned into a personal reading. Record which inputs are absent.
- Author: https://suetompkins.com/books/

**3. Robert Hand, Planets in Transit: Life Cycles for Living**
- Primary relevance: representative Western work on transits and interpretations of five major aspect types between moving bodies and fixed natal chart positions.
- Source validation: Open Library work catalog verifies a 1976 print work, subsequent editions and bibliographic identities. **An exact edition must be chosen before citing individual interpretations.**
- Good research task: draw a distinction between a transiting planet aspecting a natal reference point versus a current planet aspecting another moving planet. These are not automatically interchangeable claims.
- Important limitation: Hand's work focuses on astrological *transits in relation to natal charts*, not an independently calculated world-level event-ranking algorithm. No birth data or house cusp may be silently assumed.
- Catalog: https://openlibrary.org/works/OL6357687W/Planets_in_Transit

**4. Astrodienst / Astrowiki: Aspect, Applying Aspect, Orb and introductory aspect guide**
- Primary relevance: short, publicly inspectable working definitions of conjunction (0), sextile (60), square (90), trine (120), opposition (180), applying/separating, and multiple orb conventions.
- Good research task: capture definitions and compare several competing orb profiles. A 6° generic orb currently used by M4 is a configurable sampling/annotation convention, not a universal standard.
- Important limitation: Astrodienst is an educational/practitioner reference, not an academic demonstration of celestial effects on people. Some descriptions use "influence" language that belongs to the tradition, not to the measured JPL data contract.
- Sources:
  - https://www.astro.com/astrowiki/en/Aspect
  - https://www.astro.com/astrowiki/en/Applying_Aspect
  - https://www.astro.com/astrowiki/en/Orb
  - https://www.astro.com/astrology/in_aspect_e.htm

### Tier 2: Hellenistic, explicitly second priority

These are **research references**, not currently selected rules for the Western tropical lens.

**5. Claudius Ptolemy, Tetrabiblos (Apotelesmatica)**
- Primary relevance: historical text documenting Ptolemy's approach to astrological geometry, zodiac and interpretation within a Greco-Roman philosophical framework.
- Verification/context: Internet Encyclopedia of Philosophy describes Ptolemy's distinctive approach and its differences from other ancient astrologers, including treatment of lots/places and tropical-zodiac history.
- Important limitation: "Hellenistic" is not a singular unchanging method; Ptolemy is not interchangeable with Valens.
- Context: https://iep.utm.edu/hellenistic-astrology/

**6. Vettius Valens, Anthology (Anthologiae)**
- Primary relevance: ancient practice examples and historically important techniques/horoscopes, preserving multiple earlier authors' methods.
- Verification/context: IEP discusses Valens's role and substantial differences of emphasis and methods from Ptolemy.
- Good research task: enumerate documented techniques with work/book numbers and a named translation/edition rather than constructing an imagined composite "Hellenistic voice".
- Important limitation: editions and translations differ and carry their own copyright; choose one explicitly if detailed excerpts are later needed.
- Context: https://iep.utm.edu/hellenistic-astrology/

**7. Chris Brennan, Hellenistic Astrology: The Study of Fate and Fortune (2017)**
- Primary relevance: modern secondary survey of the historical practice, terminology and transmission, useful for comparing ancient authors before choosing primary-text implementations.
- Source validation: bibliographic record lists Amor Fati Publications, 2017, 698 pages. Use as a **modern historical interpretation**, not as the ancient primary source.
- Sources: https://theastrologypodcast.com/2017/02/25/hellenistic-astrology-the-study-of-fate-and-fortune/ and https://allstora.com/products/hellenistic-astrology-the-study-of-fate-and-fortune

### Tier 3: Vedic / Jyotisha, deferred by operator

- Do **not** choose sidereal ayanamsa, nakshatra system, house convention, auspicious timing rules or a canonical historical commentator yet. These are later user/source decisions.
- Keep source UTC positions separate from sign assignment; a sidereal reference choice may change sign labels without changing the astronomical observation.
- MAGICK should eventually explain the chosen zodiac convention, historical provenance and why familiar tropical sign/date ranges may not match Jyotisha. No Vedic reading is currently implemented.

## HOW TO USE // Proposed evaluation matrix

Before any interpretation text ships, complete a provenance/eligibility row per claim:

| Field | Reason |
|---|---|
| lens_id / family / scope | modern_western_tropical, hellenistic, later jyotisha; no silent school mixing |
| source_author, work_title, edition/translation | precise, independently auditable attribution |
| section/page locator or stable public URL | user can inspect origin and resolve disagreements |
| original meaning paraphrase reviewed by worker | avoid indiscriminate reproduction of copyright material |
| interpretation_context | sky-now, natal, horary, mundane, timing, historical-method, etc. |
| required_input_fields | positions, birth epoch/location, house system, orb profile, fixed stars, observer |
| source_celestial_event_id | tie optional meaning to real M4/M6 geometry, not synthetic data |
| configured zodiac/coordinate frame | tropical, later sidereal with named ayanamsa; preserve physical measurement |
| claim_kind | HISTORICAL_TRADITION / MODERN_INTERPRETATION / PERSONAL_REFLECTION, never physical observation |
| conflicting_sources and notes | display documented differences instead of averaging incoherently |
| status | researched / awaiting review / approved / not applicable / unavailable |

### Example of a permitted non-personal claim record

A current source-backed Mercury–Sun longitude conjunction could be labeled:

- OBSERVATION: "Mercury and Sun have geocentric apparent ecliptic longitudes separated by X° at [source UTC]." The numeric X must come from an actual M4/M6 computation.
- TRADITION: "In [named modern Western reference], conjunction is interpreted as [brief reviewed paraphrase]." Only show this after validating source context and its applicability; do not assign consequences to the user's life.
- AVAILABILITY: If no source or contextual method has been approved, show "NO CONNECTED INTERPRETATION", not generic-generated spiritual prose.

The current code correctly does not implement interpretive output.

## VERIFY // Research performed and limits

The following claims were independently checked through publisher/author and bibliographic sources: Sue Tompkins's aspect book and Handbook scopes, Robert Hand's Planets in Transit editions, Astrodienst's aspect terminology/orb variability, and IEP's historical study of Hellenistic writers. These sources are useful **for understanding traditions**, not evidence that astrological interpretation has established scientific predictive validity.

Research access checked November 4, 2026. No entire books were obtained, licensed, copied or analyzed page-by-page; this shortlist does not imply text-level inspection of chapters. A future authorized researcher needs the chosen editions and reading access for claim-level citations.

## WATCH OUT FOR

- The operator did **not** select any named author or automatically approve an interpretation library. Candidate authors are an evaluated starting point, not a normative lock-in.
- Avoid conflating **natal-chart** transit interpretations with **two contemporary moving planets**; these have different input contexts.
- Both modern and Hellenistic sources can disagree on orb, planetary influence, whole-sign aspect rules, fixed stars and house systems; never combine methods without an explicit lens record.
- Respect copyright: link to a book, cite short material appropriately and write original explanatory paraphrases; do not bulk-import proprietary chapters or published readings.
- The data from JPL do not verify metaphysical effects, life predictions, or magical causation. Traditional texts are historical/cultural research materials.
- Leave the Jyotisha selection, personal journaling and synastry/natal chart implementation to future separately scoped work.

## CHECKLIST

- [x] Verify operator's first/second/third lens order in merged decision record.
- [x] Research public descriptions of modern Western aspects and transits.
- [x] Confirm core Western candidate publications with author/publisher/library records.
- [x] Identify historically grounded Hellenistic primary/secondary candidates.
- [x] Mark context, edition, method and copyright gaps before any prose generation.
- [ ] Operator reviews usefulness of candidates; no need to choose an author yet.
- [ ] Researcher with legitimate reading access extracts a minimal *original paraphrase* vocabulary table, with section-level citations.
- [ ] Operator approves first modern Western lens convention and UI semantics.
- [ ] Only then authorize source-attributed interpretive code or user-facing readings.

## NEXT

The next scoped research deliverable is a **comparative terminology table** for major aspects, retrograde/stations, applying/separating, orbs and natal versus sky-now interpretation, with document-level citations and explicit context requirements. The operator should evaluate clear examples of how each source approaches an identical mathematical configuration before selecting a favorite.

Hellenistic methods follow as a distinct second study with source-specific rules. Vedic/Jyotisha remains third as requested, with no premature sidereal default.

## DECISIONS

Confirmed operator priorities: modern Western tropical > Hellenistic > Jyotisha; combined MAGICK home; two linked network/spatial views; NOW-first past/future navigation.

No author, orb algorithm, astrological truth claim, copyright license, implementation task or detailed personal chart methodology is approved by this catalogue.
