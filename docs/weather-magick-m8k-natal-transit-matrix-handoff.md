# 🏥💜 MAGICK M8k // Bounded Natal × Transit Source Matrix

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > ASTROLOGY > TRANSITS > MATRIX
STAFF ROLE // External DOC, OPEN AI // CHATGPT; Hospital-compatible, not live-registered
ASSIGNMENT // Extend accepted M8j with 1–3 natal references compared against 1–3 moving JPL bodies in one bounded source request
BASE // main a3bdb54ecd2173d896df4ef8fae7ffce8ec67a3e
BRANCH // feat/weather-magick-m8k-natal-transit-matrix-20261107
SCOPE // Additive JPL Python engine, strict read-only QML policy/service/pane, existing Astrology deck navigation, isolated tests/docs/CI.
PERMISSIONS // GitHub development, tests, draft PR. No local workstation edits, installation, restarts, merge, production activation or operator final acceptance.

## IMPLEMENTATION

- `scripts/weather/celestial_transit_matrix.py` reuses the accepted M8f source-crossing search and M8i station detector. It independently computes up to **3 natal body longitudes** from the full verified natal epoch, then up to **3 moving JPL tracks** over an explicit UTC range, all with the same installed Skyfield/JPL BSP SHA-256, observer and true ecliptic-of-date frame.
- Unlike repeating the old M8h full search nine separate times, each transiting body has a cached source sampler. Transit source plot samples are returned once for each selected moving body. Each natal/transit pair receives its own exact-crossing aspects and count.
- **Stations belong to the moving body**, not a natal pair. Station events appear exactly once for each moving source, with `natal_body:null`; they do not inflate matrix cell aspect counts. A station opened in WHEEL uses the first selected natal reference **for viewing only**, labeled as such.
- Explicit resource limits: <=3 natal references, <=3 moving bodies, <=31 days total window, 30/60-minute cadence; <=2200 pair-samples across all selected pairs; <=3000 total station-rate grid points, <=150 events and <=120 KB output. Example: 3x3 for 7 days at 60 min is supported, 2x2 for 14 days at 60 min is supported; longer/larger combinations reject rather than silently perform unbounded work.
- `StationMagickTransitMatrixPolicy.js` validates the exact natal chart NAIF IDs, observer, source SHA, time bounds, selected target lists, natal longitudes against the existing chart, each moving sample track, aspect event counts per pair, event bounds and station de-duplication. Source mismatch fails closed.
- `CelestialTransitMatrixService.qml` only launches a private one-shot local process upon explicit SEARCH, with personal time and coordinates sent on bounded JSON stdin rather than arguments. It does not create persistent natal/event records, network calls, notifications, profile updates, background polls or weather/GPS assumptions.
- `StationMagickTransitMatrixPane.qml` adds a compact pair-count table, selects natal and transiting bodies separately, reuses TASKS-style date/month/day/year controls, lets users change duration/cadence/aspects, shows source-filtered event rows, allows clicking a cell for exact pair events, and returns to WHEEL on selecting an event.
- `StationMagickAstrologyPane.qml` adds MATRIX as a fourth mode in existing TRANSITS, preserving WHEEL, TIMELINE and MULTI. An inspected matrix event returns to WHEEL at the **nearest whole UTC minute** and retains exact source event UTC. `StationMagickTransitChartPane.qml` labels the natal reference and transit body when reached from MATRIX.

## HOW TO USE

After independent review and separately approved merge/deployment: Weather Station → MAGICK → ASTROLOGY → NATAL: calculate a real full JPL chart with correct event date, UTC and birth/event location. Open TRANSITS → MATRIX. Select up to 3 natal bodies (yellow row) and up to 3 moving bodies (cyan row), UTC date using TASKS steppers/TODAY, range 1/7/14/31 days, cadence 30/60 min and aspect families. Press SEARCH. A grid cell reports **the number of source crossings for that natal/moving pair**. Clicking a cell filters to that pair; clicking it again clears the pair filter. The event list includes moving-body stations once, separate from pair counts. Click an event to inspect WHEEL at the nearest minute; exact UTC event timestamp remains labeled. The range button may display unsupported combinations, but SEARCH remains unavailable until within the bounded budget.

## VERIFY

- `tests/weather/test_magick_natal_transit_matrix_m8k.py`: synthetic 3x3 analytical source paths verify each pair ID, numerical contact time, cached moving tracks, station-once semantics and source/resource rejection. No test fixture is claimed as actual JPL astronomy.
- `tests/weather/test_magick_natal_transit_matrix_ui_m8k.js`: strict source payload admission, exact hash/site/NAIF/time/body validation, per-pair count consistency, rejection of false station-natal pair links, matrix event filtering and nearest-minute wheel callback; preserves old mode wiring.
- `tests/weather/fixtures/M8kNativeMatrixShell.qml` and `scripts/weather/verify_magick_native_m8k.sh` run actual Quickshell and Qt offscreen in disposable isolated HOME/XDG roots with source-shaped synthetic data; verify 2x2 cell counts, station handling, pair selection and exact-event signal. Does not run the operator's installed BSP.
- `.github/workflows/weather-magick-m8k-natal-transit-matrix.yml` runs new Python/JS/native tests and existing M8i/M8h/M8j/M8g regressions. Recheck exact PR-head success before claiming any gate passed.
- Real Fedora/SwayPX visual input/size acceptance, live JPL DE440s output/performance comparison, and independent second-worker review remain separate.

## WATCH OUT FOR

- This is a bounded **pairwise transit-event matrix**, not a magical causality predictor or unlimited 10×10 planet search. Conventional aspects label angular relationships computed from source longitudes. Tangential/grazing contacts and rapid station pairs can still be missed; finite-difference station times are estimates.
- A station is not a natal-body-specific event and must not be counted or labeled as such. Event row selection for a station uses the first selected natal reference **only** for rendering the existing wheel.
- Numeric <=1-second contact bracket and <=60-second station bracket describe root refinement, not guaranteed physical accuracy; WHEEL remains minute-resolution.
- The UI may need native compact-size fit work; isolated CI is not the operator's live Fedora desktop. M8j is accepted but no M8k merge/activation or final acceptance is inferred.
- This branch changes only owned Weather MAGICK files and adds new ones. Shared TASKS/Location/COSMOS providers, external services, and local desktop are unchanged.
- Source output up to 120 KB remains transient; no profile, TASKS, journal, calendar, saved birth data, downloaded BSP or notifications are written. CPU cost rises with pair count and source station checks; explicit budgets fail closed.

## CHECKLIST

- [x] Read current Syntagma AGENTS, Hospital protocol and working guide; identify patient/room/role/scope
- [x] Verify main SHA, merged M8i/M8j, no open MAGICK/transit PRs
- [x] Build bounded shared-source 1–3 by 1–3 numerical matrix, do not duplicate stations
- [x] Add strict JPL source-response validator, private service, MATRIX UI and wheel handoff
- [x] Add dedicated Python, Node, native QML regression workflow
- [ ] Exact PR-head CI and issue correction
- [ ] Independent second review, real DE440s performance and numerical comparison
- [ ] Operator merge, live Fedora deployment, visual and final acceptance

## NEXT

Run exact PR-head GitHub Actions and repair evidence-supported issues without widening scope; preserve accepted WHEEL/TIMELINE/MULTI. Keep the branch in draft until review and operator decision. If later extending beyond 3x3 or 31 days, require a separately scoped CPU/accuracy budget and consent.

## DECISIONS

Single JPL kernel SHA and original natal observer remain canonical. Station events are moving-body-only; matrix cells count aspect crossings, no fabricated imagery or event times. No live Hospital registration. Operator is final authority for merges, desktop changes, deployment and acceptance.
