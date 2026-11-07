# 🏥💜 MAGICK M8l // Four-by-Four Matrix and Explicit Workload Planner

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Weather Station > MAGICK > ASTROLOGY > TRANSITS > MATRIX
STAFF // External DOC, OPEN AI / CHATGPT (Hospital-compatible, not live registered)
ASSIGNMENT // Follow accepted M8k with a bounded larger comparison set and better operator-facing calculation budget
BASE // main ceca5d62431d562ab5aab6da5551eaf4e9e0cab2 at branch creation
BRANCH // feat/weather-magick-m8l-four-by-four-budget-planner-20261107
PERMISSIONS // GitHub implementation, tests, documentation and draft PR only. No local desktop writes, service restarts, merging or production activation.

## IMPLEMENTATION

- M8k PR #1432 **verified merged** (merge commit 45dd6f847f8a311cb2ab13ddbebedcb5f790800b); user reported the implementation approved. No open MAGICK or MATRIX PR was found before starting M8l.
- Expanded `scripts/weather/celestial_transit_matrix.py` maximum selections from 3×3 to **4 natal bodies by 4 moving bodies**. **No increase** to its existing resource ceilings of 2,200 pair-samples, 3,000 total 15-minute station-scan points, 150 source events, or 120 KB output. The source epoch, observer, ephemeris SHA-256, topology, one-shot stdin privacy and accepted M8f/M8i numerical engines remain unchanged.
- Existing 3×3 7-day (60-minute) search still works. 3×4 at 7 days and 60 minutes uses 2,028 pair-samples and 2,692 station samples and remains supported. A full 4×4 at one day and 60 minutes uses 400 pair-samples and 388 station-rate samples, so it is supported. A 4×4 seven-day search uses 2,704 pair-samples and is rejected under the retained budget, rather than silently consuming more work.
- `StationMagickTransitMatrixPolicy.js` mirrors the Python count limits through a pure, explicit `budget()` function. The same policy's `request()` uses that budget, preventing front-end and Python disagreement. `fittingSpan()` recommends the largest valid range from the existing 1/7/14/31-day list that does not exceed the currently chosen duration. The suggestion does not change any value automatically.
- `StationMagickTransitMatrixPane.qml` allows four bodies on each selection rail, adds a source-workload strip showing number of pairs, pair-samples and station-rate samples against their respective limits, and an explicit FIT N DAYS button only when over budget. Clicking FIT reduces the duration only, never deletes selected bodies, changes UTC, switches ephemeris or changes data sources.
- Existing WHEEL/TIMELINE/MULTI navigation, pair-cell source counts, event paging, once-only station semantics, exact contact UTC, minute-rounded wheel handoff, TASKS date steppers and session-only state are maintained.

## HOW TO USE

After an explicitly authorized merge and deployment, open Weather Station → MAGICK → ASTROLOGY → NATAL → TRANSITS → MATRIX. Choose 1–4 natal reference bodies (yellow row) and 1–4 moving bodies (cyan row), plus UTC start date, desired 1/7/14/31-day range and 30/60-minute cadence. A workload strip displays the exact requested pair and station-sample budgets. If over budget, SEARCH stays disabled. Click **FIT 1D** (or the shown safe duration) to shorten only the selected range, then SEARCH. The cell grid presents aspect counts per pair, while station events remain attached to the moving body only.

## VERIFY

- `tests/weather/test_magick_four_by_four_m8l.py`: backend 4×4 request, 4 moving ×3 natal 7-day feasibility, reject 4×4 seven-day / five-body overflow, synthetic 16-pair event aggregation, stations emitted once per moving body, unchanged source/private-file limits.
- `tests/weather/test_magick_four_by_four_ui_m8l.js`: Python-equivalent budget arithmetic (400/2,200 + 388/3,000 for one-day 4×4), 2,704/2,200 overrun for 7-day 4×4, FIT choice, unchanged JPL source contract, and preservation of original wheel/event controls.
- Updated one M8k pre-expansion negative fixture to use **five** natal selections instead of the former four-body boundary; M8k and earlier positive tests stay unchanged.
- `tests/weather/fixtures/M8lNativeMatrixBudgetShell.qml` with `scripts/weather/verify_magick_native_m8l.sh`: disposable offscreen real Quickshell/Qt instantiation, four-by-four binding, explicit FIT of an over-budget 7-day request to one day, strict source-shaped synthetic result with 16 pair cells and one moving-body station, and original WHEEL callback.
- Dedicated `.github/workflows/weather-magick-m8l-four-by-four-budget.yml` runs Python/Node/native test jobs with M8k, M8j and M8i regressions. Verify exact PR-head CI before reporting success.
- Synthetic inputs are only to test code behavior, not live DE440s ephemeris outputs, actual birth records or the operator's current Fedora panel layout.

## WATCH OUT FOR

- This is not permission to run 16 pairs over every duration. Existing CPU and event budgets remain strict. The search may take longer than the accepted 3×3 on similarly sized ranges; actual DE440s kernel timing is a separate acceptance gate.
- FIT RANGE is intentionally operator-triggered. An over-budget request is rejected, not automatically shortened without a click. The current date and operator-entered birthplace are never modified by budget controls.
- The source still searches sign-changing angular crossings and finite-difference station estimates, subject to the accepted M8i limitations. The numerical bracket (1 second for aspects, 60 seconds for station estimates) is not equivalent to observational accuracy. WHEEL event inspection remains nearest UTC minute.
- New 4×4 header/row sizing has an isolated offscreen native fixture at 640×525; smaller actual Fedora panels and all-user mouse affordances remain unverified.
- No change to live Quickshell, local Fedora filesystem, TASKS, Settings++, social identity, storage or other patients. No merges/production activation claimed.

## CHECKLIST

- [x] Re-read current Syntagma AGENTS / Hospital / Post-Apollo guide
- [x] Verify accepted M8k merged into exact GitHub main and no competing open MAGICK/MATRIX PR
- [x] Expand to 4×4 without changing existing sample/event/output limits
- [x] Add visible resource estimator and explicit FIT duration control
- [x] Update invalid max-selection fixture; add new numeric/JS/offscreen QML tests
- [x] Create additive M8l GitHub CI
- [ ] Pass exact final PR-head GitHub CI
- [ ] Independent second-worker review and actual operator DE440s CPU comparison
- [ ] Operator merge decision, Fedora native layout and final acceptance

## NEXT

Check new numerical, JavaScript, offscreen and repository-wide workflows and repair failed evidence. Keep draft/unmerged unless operator explicitly authorizes a merge. Future improvements can evaluate real JPL runtime and source sampler reuse, adjust panel geometry for smaller layouts, or introduce explicit resource-limited longer-range searches as independently scoped work.

## DECISIONS

M8k is the accepted baseline and must not be reopened as unaccepted. M8l is a separate optional expansion. Larger body counts do NOT mean a larger CPU budget. The source and observer remain exactly bound, stations are not attributed to natal pairs, and user's live system remains unchanged.
