# Weather Station // W2a HOME Smart Deck, Session Favorites and Rotation

**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Weather Station / CLASSIC → SUBJECTS HOME Intelligence Migration  
**STAFF:** External Hospital-compatible ChatGPT (no live Hospital connection verified)  
**ASSIGNMENT:** W2a restore operator-selectable random HOME panel swapping, HOLD and favorite weighting while retaining the existing W1 HOME instance and source owners.  
**BASELINE:** `main` at `5d737335d531f822b72e9908864d6fc696895246`.

## IMPLEMENTATION

W1/W1r already mounts one persistent `StationHome.qml` under
`StationWorkspaceSurface.qml` and exposes separate HOME bottom tabs:
OVERVIEW, AUTO, QUICK, SNAPSHOT, HISTORY, RUNTIME, SOURCES and MAGICK.
W1 also preserves the original deterministic `rankRelevant()` and
its 60-second watch timer, live/sample history, source health and
original `StationRuntimeRack`. M27-A PR #1099 is merged and separately
restores adaptive watch cards in WEATHER overview.

W2a adds an **operator-controlled smart deck** under HOME. It uses
existing `ActionButton` styling in a 40px row immediately above the
unchanged bottom submode rail:

- **ROTATE OFF/ON** enables an **opt-in** 30-second automatic panel swap.
- **MODE MIXED/AUTO/PINNED** changes the candidate selection.
  - AUTO: random next panel from all operational HOME panels.
  - MIXED: random next panel, giving bookmarked panels 3x weight.
  - PINNED: random among favorites only, or holds when none other is eligible.
- **HOLD/RESUME** stops/restarts automatic swaps so content stays
  readable. Manual NEXT and tab selection remain available.
- **☆/★ FAVORITE** toggles one stable HOME panel route. It is disabled
  for OVERVIEW and MAGICK because those aren't part of the six-panel
  operational swap pool.
- **NEXT** performs a manual random swap even if ROTATE is off or HOLD
  is selected. The policy prevents immediately repeating the current
  panel.

Six eligible original panel routes are:
`home/auto`, `home/quick`, `home/snapshot`,
`home/history`, `home/runtime`, `home/health`.

All content still comes from the one pre-existing `StationHome`
instance. The actual `StationHomePolicy.rankRelevant` watch is not
replaced; this new randomizer chooses **which whole section is shown**,
not which individual alert or measurement is promoted. The original
global NWS alert indicator is not changed by rotation or HOLD.

Stable favorite panel routes, deck mode, HOLD and ROTATE state are kept
as **in-memory session preferences on `StationSubjectNavigator`** so
moving between HOME, other subjects, INDEX and temporary CLASSIC does
not unexpectedly reset them while the owning navigator remains alive.
No disk backing is claimed.

New pure policy: `StationHomeDeckPolicy.js`. It filters duplicate,
invalid and foreign favorite IDs; no new polling, provider, cache,
FileView writer, storage schema or credentials.

## HOW TO USE

After operator review, merge and separately controlled local deployment:

1. Open Weather Station → SUBJECTS → HOME.
2. Choose a HOME submode on the existing bottom row.
3. Use `ROTATE // ON` for automatic 30-second swapping, `MODE` to
   choose AUTO/MIXED/PINNED, `☆ FAVORITE` for the current submode,
   `HOLD` to pause, and `NEXT` to swap immediately.
4. To keep a panel displayed, use HOLD or turn ROTATE off.

All controls are opt-in. HOME stays on the chosen tab until an explicit
NEXT, manual tab choice, or enabled rotation triggers navigation.

## VERIFY

Tests under `tests/weather/test_home_deck_w2a.js` check:

- Exactly six operational HOME swap destinations, none in other subjects.
- Stable favorites by route ID with sanitization, deduplication,
  toggle and deterministic injected random selection.
- AUTO/PINNED/MIXED semantics, no immediate repeat, empty/one-pin hold.
- The timer does not navigate when hidden, in INDEX, on another subject,
  disabled or held.
- Original one-HOME renderer, ranking/watch timer and bottom tabs remain.
- Preferences are hoisted to the persistent navigator, not duplicated
  in each submode or written to any disk store.
- No new service, process, FileView or dossier capture.

Dedicated workflow also reruns W1 landing, W1r left rail, M27-A subject
panel test and original HOME relevance policy. **At PR creation, W2a CI
was not yet observed; verify the exact final-head checks before merging.**

## WATCH OUT FOR

- **Favorite pins are session-only**, not persistent through a full
  Quickshell process restart. The originating Favorites service is still
  an AppControl-specific compatibility surface; do not fabricate a
  canonical shared favorite store. Durable, opt-in persistence is a
  separate owner/format decision.
- This W2a pin applies to a whole HOME *workspace section*, not one
  specific `AUTO RELEVANT` card or a per-source favorite. Follow-up
  W2b can address card-level pinning with explicit source identity,
  stale/unavailable handling and a vetted store.
- Rotation does not fetch new data or increase provider polling;
  switching panels does not re-create the original HOME component.
  The existing ranker remains deterministic and distinct from W2a
  randomized *panel* rotation.
- The RUNTIME tab is the existing source operating catalog, **not**
  a verified Linux-wide process inventory. Do not claim full PID
  parity without a separate AppControl/Process integration.
- The 160px left rail and original bottom submode tab row remain
  untouched. W2a reduces HOME's content viewport by 40px; actual
  Fedora/Sway sizing and mouse acceptance require operator-controlled
  visual verification.
- No CLASSIC → SUBJECTS transient selection bridge was added because
  CLASSIC is a temporary migration source, not a permanent dual UI.
- This is the first bounded W2 increment; full favorite persistence,
  per-card pin decay, dynamic source explanation, and richer graphs
  remain unimplemented.

## CHECKLIST

- [x] Re-read Syntagma AGENTS, working guide and permissions
- [x] Verify M27-A merged and current W1/W1r HOME ownership
- [x] Check for concurrent Weather PR collision
- [x] Implement opt-in session smart deck using existing UI primitives
- [x] Preserve original HOME ranker, alerts and data lifetimes
- [x] Create pure policy tests and focused CI
- [ ] Final PR-head CI passed
- [ ] Operator review/merge
- [ ] Native Fedora/Sway UI geometry and focus acceptance
- [ ] Persistent favorite backing with confirmed store ownership
- [ ] Card-level pinning, source age and ranking explanation

## NEXT

Inspect CI logs and resolve only W2a-scoped test or UI issues. After
merge and operator acceptance, progress to W2b native card-level
favorites and provenance, validating the relevant shared storage owner
before any disk writes. Carry forward W1 and M27-A tests.

## DECISIONS

GitHub feature branch only. No local user-filesystem modification,
package installation, Quickshell restart, live provider activation,
archive migration, auto dossier capture, production deployment, PR
merge or live Hospital registration.
