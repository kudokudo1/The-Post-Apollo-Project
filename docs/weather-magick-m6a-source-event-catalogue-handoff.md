# MAGICK M6-A // Source Event Catalogue Handoff

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather StationW / MAGICK Event Research and Source Catalogue
ROLE // External Hospital-compatible developer; live Hospital registration not verified
ASSIGNMENT // Source-backed catalogue for aspects, stations, grazing candidates and sampled motion
BASE // main at 14d2c7d384622e20c5ac48dff77874686f36c055
BRANCH // feat/weather-magick-m6a-source-event-catalogue-20261104
PERMISSION // GitHub-only bounded source work, no merges or local Fedora mutations
OWNERSHIP // New isolated pure Python adapter and tests, workflow, handoff. Existing M4/M2, root service and Weather UI left untouched.

## IMPLEMENTATION

The source M4 graph backend already calculates geocentric apparent true-ecliptic-of-date longitudes, pairwise aspects, motion and numeric event markers. M6-A creates a renderer-neutral, read-only adapter rather than a new JPL engine or collector.

- scripts/weather/celestial_event_catalogue.py accepts canonical M4 visual-data.v1 JSON and produces post-apollo.weather.magick-event-catalogue.v1 JSON.
- Source admission validates canonical query, timestamp grid, requested body IDs, source sample agreement, pairwise angular separation/aspect values, valid source provenance metadata, event type, timestamp, angular tolerance and rate-window consistency. Source-kernel SHA shape is checked; only upstream M4 actually hashes the JPL file.
- Normalized event classes:
  * computed_crossing: existing M2 numerically refined aspect crossing, explicitly non-exhaustive across all possible contacts;
  * finite_difference_estimate: geocentric apparent longitude station, with original rate-window method;
  * bounded_grazing_candidate: M3 searched near-tangent candidate, never mislabeled a confirmed crossing.
- Five existing major aspect angles: 0-degree conjunction, 60 sextile, 90 square, 120 trine, 180 opposition. They are conventional geocentric ecliptic-longitude relationships and have no established physical effect on human behavior.
- Sampled aspect states within a named orb at the LAST actual M4 grid time remain separate from the exact event records.
- Sampled direct/retrograde/indeterminate motion runs have source sample boundaries, not invented precise station transition times.
- Deterministic event_id values depend on JPL hash, type, name, classification, body IDs and actual source event time. Stable for identical metadata, but refinement changes across future overlapping windows can change the time and ID. Never use as perpetual personal-record IDs.
- Explicit search states: bounded_non_exhaustive when requested and not_requested otherwise. 3–4 body source windows with include_events=false can still report sampled relationships, but no invented multibody search.
- Bounded stdin-to-stdout CLI, no file writes, network, Qt, extra service, installation or user location lookup.

Source and tests:
- scripts/weather/celestial_event_catalogue.py
- tests/weather/test_celestial_event_catalogue_m6a.py
- .github/workflows/weather-magick-source-event-catalogue-m6a.yml
- docs/weather-magick-m6a-source-event-catalogue-handoff.md

## HOW TO USE

This milestone creates no visible MAGICK button or view. A later M7 component can request the existing M4 JSON via the single root-owned JPL Process and pass the result through build_catalogue(raw) to obtain source-classified events and sample-state labels. It must display the source time and provenance.

Developer test from the repository root:

    python3 -m unittest discover -s tests/weather -p 'test_celestial_event_catalogue_m6a.py' -v

The catalogue script also reads one existing M4 JSON object on standard input and prints normalized JSON on standard output. Invalid sources exit nonzero with an explicit error. No new JPL file or Python dependency is required by the adapter itself.

## VERIFY

Initial implementation head 4081fdce6ac91195b85aea7b619b3323f2362c08:
- 3/3 GitHub jobs passed: pure-source-contract, official-jpl-contract and validate.
- 9 offline source tests passed, one intentionally skipped where no kernel is available.
- 10/10 tests passed in a disposable GitHub runner using genuine DE440s and Skyfield 1.55, including real Sun/Moon source-event lineage.
- Legacy M4 geometry and M2 dynamics numerical tests passed in the pure runner.
- Direct tests cover five major aspects, stations, tangent candidates, source query consistency, four-body sampled-only cases, event identities, no-query cases, invalid data, and CLI behavior.
- CI is not proof of live Quickshell integration. No GUI was changed.

The final PR head must be rechecked after this documentation commit.

## WATCH OUT FOR

- M4 event search still supports at most two requested bodies. Full 3–4 body event discovery remains a separately bounded M6-B problem.
- A missing event is not proof that none occurred; bracketed crossing search can miss tangent contacts. Grazing candidates and station estimates have different classifications.
- The catalogue uses major aspect longitude rules as a conventional observational geometry layer, NOT a verified spiritual/causal influence.
- The catalogue does not calculate true eclipses, lunar nodes, exact ingress/equinox times, natal chart readings, houses, heliocentric 3D or personal journals.
- Source event IDs are deterministic for identical event metadata, not immutable across search refinements. Do not attach durable private journals to them without a later identity strategy.
- Source-last-sample time is not necessarily NOW. Do not mislabel it current at UI integration.
- Origin is geocentric/apparent/true-ecliptic-of-date; the selected spatial solar-system view must have its own correct coordinate frame, linked only by time and body selection.
- No local Fedora, Quickshell, ephemeris installation or runtime process was modified.

## CHECKLIST

- [x] Verified current main, merged M6/M7 research specification and no overlapping open PRs.
- [x] Reused M4/M2/M3 computed event sources and did not expand provider ownership.
- [x] Stable per-input event identification, exact versus candidate versus estimate labels.
- [x] Consistent provenance, body/time and sampled-state admission.
- [x] Pure numerical and genuine official JPL regression tests passed at implementation head.
- [ ] PR-head checks after handoff.
- [ ] Operator authorized merge and acceptance.
- [ ] M6-B selected multibody pairwise event search scope and costs.
- [ ] M7 network/spatial visual contract and live acceptance.

## NEXT

The next bounded step is M6-B design: select 3–4 source bodies and determine the precise, performance-bounded event-discovery model without pretending that M4 already searched six pairs. M7 can subsequently bind this catalogue to the accepted NOW-centered time selection and two correctly framed graphical modes. Modern Western tropical interpretation is first, Hellenistic second, Jyotisha third, each with cited sources and approved conventions.

## DECISIONS

M6-A stops at a verified read-only event catalogue. No additional interpretive lens, new display, second provider, persistence, global time/store or local deployment is authorized by this milestone.
