# Weather Station W1 // Full-width workspace and HOME continuity

PATIENT // The-Post-Apollo-Project
ROOM // Weather Station subject-workspace reformat
ROLE // External Hospital-compatible doctor
STATE // W1 implemented in isolated branch; W2 and W3 planned only
AUTHORITY // User approved staged layout reformat and preserving legacy HOME intelligence

## IMPLEMENTATION // W1

Seven AppControl-style top modes: HOME, WEATHER, COSMOS, EARTH, MEDIA,
MAGICK, TOOLS. Each selects the existing overview route immediately.
The center mounts an existing subject pane, not an empty subject index.
Horizontal bottom buttons select combined source submodes.

HOME has eight bottom controls:
OVERVIEW / AUTO / QUICK / SNAPSHOT / HISTORY / RUNTIME / SOURCES / MAGICK.

One original StationHome.qml remains instantiated through all HOME
bottom sections and while switching to other subjects under SUBJECTS.
The entire original HOME content appears on OVERVIEW. Other HOME tabs
focus its existing code sections without rewriting panel contents:
AUTO = rank/watch/alerts; QUICK = quick+relationships;
SNAPSHOT = current snapshots + alerts;
HISTORY = forecast history + relationship traces;
RUNTIME = original StationRuntimeRack;
SOURCES = original source-health panels;
MAGICK = existing observation-only lunar/solar reference lens.

This preserves existing 60-second relevance checks, activeWatchIds,
rankRelevant hysteresis, source-age thresholds, previous-provider
observation deltas, live history and snapshot controls.
The WeatherHistoryService is active for new HOME subject mode.

Top modes are a full-width workspace; the historical 160px vertical
rail remains in the CLASSIC mode and MORE/INDEX. The original 135-route
index remains accessible through MORE for all deep paths.
CLASSIC remains a separate eight-page UI and its original source
ownership, MAP news handoff and exact Kitty/Sway terminal geometry
are untouched. No new provider or writer is created.

## W1 CONTROL TABLE

TOP:
 HOME | WEATHER | COSMOS | EARTH | MEDIA | MAGICK | TOOLS | MORE | CLASSIC

BOTTOM WEATHER:
 OVERVIEW | NOW + AIR | FORECAST | WATER | HAZARDS | MAPS | HISTORY

BOTTOM COSMOS:
 OVERVIEW | SUN | MOON | PLANETS + SKY | EVENTS | SPACE WX

BOTTOM EARTH:
 OVERVIEW | GEOGRAPHY | GEOLOGY | EVENTS | FIRES | MAPS | DOSSIERS

BOTTOM MEDIA:
 OVERVIEW | NEWS | WATCH | RADIO | CREATORS

BOTTOM MAGICK:
 OVERVIEW | LUNAR + SOLAR | PLANETARY | ASTROLOGY | DIVINATION | GRIMOIRE

BOTTOM TOOLS:
 OVERVIEW | SOURCES | STORAGE | TERMINAL | SETTINGS

All paths are declared in StationWorkspaceNavigationPolicy.js.
A selected family always lands on its overview; deep children stay
available through MORE until their deeper context controls are
reorganized.

## NEXT // W2, HOME smart deck and pinning (PLANNED, NOT IMPLEMENTED)

Audit both StationHome and any older separate Home/favorite UI.
Current StationHomePolicy.rankRelevant ranks up to three contextually
important items with stale-data handling and hysteresis. It is not
verified as uniform randomized swapping. Its periodic evaluation is
60 seconds, with event-triggered updates from the source owners.
Keep this deterministic relevance engine.

Planned AUTO deck controls:
 MODE AUTO/PINNED/MIXED | ROTATE | NEXT | HOLD | FAVORITE
 WHY THIS CARD? | AGE | SOURCE PROVENANCE | RELEVANCE SCORE

No persistent favorite pin store was verified in current
StationHome.qml. Do not invent a saved favorites catalog. Before
adding persistence, find the actual originating store and identify
stable panel IDs instead of unstable display-list indices.

Maintain urgent NWS alerts independently of user HOLD/pin states.
Never treat a saved favorite as proof that its source is still live.
A panel should retain selected/favorite state across tab changes;
do not force re-seeding relevance every time a user opens COSMOS.

## NEXT // W3, richer source-driven cards and graphs (PLANNED)

HOME data families to retain and expose more prominently:
 - source health (receive age versus observation age, cached/stale)
 - relevance/decay, ranked watch cards and pinned favorite lane
 - quick current weather and forecast
 - auto snapshots and delta/previous observation comparisons
 - forecast model history versus bounded live observation history
 - AQI/weather, magnetic field, pressure/water relationship graphs
 - original StationRuntimeRack source operating catalog
 - MAGICK Moon/Sun observational strip and clear reserved interpretive
   and planner slots, with no invented tarot/astrology/ritual records.

StationRuntimeRack is a catalog of source operating rows, not a
verified machine-wide Linux process list. If OS process details are
needed, integrate AppControl/System read-only through its owner,
not by falsely labeling source rows as every process on the machine.

Subject overviews later become card launchpads that summarize real
data and graphs, then open detailed submodes. Reuse original
sample arrays/history stores and chart components; never draw
fake values or create another polling engine.

## VERIFY

W1 automated scope: seven family destinations, the 44 bottom controls,
all original HOME section keys and source state, one persistent HOME
component, CLASSIC/terminal ownership, and previous subject contracts.
GitHub CI cannot confirm visual widths or live provider freshness.
Actual Quickshell test on Fedora requires separate local approval.

## WATCH OUT FOR

The 1000px Weather Station frame may require button-width tuning after
a real visual smoke. No terminal hosting change or local files were
modified. Existing MAGICK routes are still not complete symbolic
calculation engines. WATCH embedded video remains unverified.

## CHECKLIST

- [x] Source, branch, ownership, protocol preflight
- [x] Bounded seven-family W1 workspace and original HOME reuse
- [x] W1 tests/workflow and recovery plan
- [ ] CI final head verified
- [ ] Merge per operator existing authorization when green
- [ ] Local runtime and visual acceptance
- [ ] W2 smart card/favorite work, separate assignment
- [ ] W3 graphs/overview cards, separate assignment

## DECISIONS

Stage navigation first. Preserve all original HOME functionality.
Do not migrate/replace source-owned data in the UI refactor.
W2 and W3 are requirements, not claims of implemented functionality.
