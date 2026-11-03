# Weather Station // M27-A CLASSIC → SUBJECTS HOME Relevance

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Weather Station / CLASSIC → SUBJECTS Capability Parity  
**STAFF:** External Hospital-compatible ChatGPT, not connected or registered in live Hospital  
**ASSIGNMENT:** First bounded implementation from the read-only migration audit: restore HOME's existing AUTO RELEVANT display in SUBJECTS WEATHER overview.  
**BASELINE:** `main` at `c19f13c8f66c09d5489a154a9f7470906b848159`.  
**SCOPE:** `StationWeatherSubjectPanelPolicy.js`, its existing M2b regression test, Weather teardown CI step, and this handoff.

## IMPLEMENTATION

Before M27-A, `weather/overview` instantiated the real `StationHome`
but permitted only `header`, `alerts`, and `snapshot` sections.
Its adaptive `AUTO // RELEVANT` cards existed in the shared HOME component
but were deliberately invisible in SUBJECTS.

M27-A permits `relevant` on that exact route:

```js
"weather/overview": {
  page:"home",
  sections:["header","alerts","snapshot","relevant"]
}
```

This **does not** invent a second ranking implementation. The existing
`StationHomePolicy.rankRelevant`, `StationHome.refreshWatch`, native
`watchItems`, `activeWatchIds` hysteresis, and 60-second relevance timer
remain the owner. The original `StationHomeMetricCard` renderer becomes
visible in the new WEATHER overview. No fetcher, background poller,
FileView, cache writer or dossier capture is introduced.

No CLASSIC HOME feature is disabled. Its existing `workspaceSection`
switch and all original sections retain their empty-`subjectRoute`
behavior. This is a migration/cutover increment, not retirement.

**Intentional subject partition:** `StationWeatherSubjectPane` currently
passes `spaceService: null` to HOME; NOAA solar/geomagnetic observations
remain COSMOS-owned. Therefore the WEATHER AUTO RELEVANT row will rank
WEATHER, SKY, and air-quality signals but cannot show CLASSIC's COSMOS
space-alert cards. That is **not full cross-domain HOME parity** yet.
The eventual SUBJECTS dashboard's cross-domain recommendations and
panel-swapping/favorites are separate feature work.

## HOW TO USE

After this branch is reviewed and merged, open the Weather Station's
**SUBJECTS → WEATHER → OVERVIEW**. Scroll to `AUTO // RELEVANT` beneath
the existing weather snapshot. With live source data, the existing HOME
ranker chooses candidate cards; with missing data, it shows its baseline
state rather than fabricating readings.

No local `git pull`, Quickshell restart, system package installation or
test against the operator's workstation was performed by this worker.
Deployment and real-menu visual acceptance remain separate.

## VERIFY

Source-contract checks are wired into
`.github/workflows/weather-teardown-contracts.yml`:

- Existing `test_station_home_policy.js` verifies relevance ranking.
- The updated `test_weather_subject_panels_m2b.js` verifies that the
  exact WEATHER overview exposes `relevant` while unrelated routes
  exclude it; CLASSIC's original section visibility survives; the
  shared renderer uses the same `watchItems` and
  `StationHomePolicy.rankRelevant`; no new fetcher/writer is introduced.
- Existing broad Weather teardown tests still run.

**At documentation creation, GitHub CI had not yet been observed.**
Do not claim green checks without inspecting the final PR HEAD.

## WATCH OUT FOR

- The original adaptive relevance ranking is not the proposed
  stochastic/random swapping of larger HOME workspaces. Do not conflate
  those features. The original CLASSIC `workspaceSection` switch still
  exists but is not yet a SUBJECTS-first workspace switcher.
- The original source-health rack, full runtime rack, quick cards and
  history are available through their current CLASSIC or dedicated
  SUBJECTS routes; this PR intentionally does not dump every large
  section into WEATHER overview.
- COSMOS observation cards are not smuggled into the WEATHER-only pane.
  Cross-domain ranking requires a separate explicitly-owned overview
  architecture that uses shared source data without duplicate polling.
- 103/103 CLASSIC panel IDs have a destination in the subject route
  catalog, but that count measures *routing*, not verified feature parity.
- Existing M26-F EARTH continuity verification was merged into main at
  `c99fd68309d19c1957a2daf9a289336dd5644dd0`.
  There is no reason to create a permanent CLASSIC↔EARTH selection bridge
  solely for a legacy interface destined for retirement.

## CHECKLIST

- [x] Re-read canonical Syntagma AGENTS and OPERATE rules
- [x] Recheck current GitHub head / Weather ownership and existing HOME switch
- [x] Restore AUTO RELEVANT in WEATHER OVERVIEW using original component
- [x] Preserve COSMOS ownership and CLASSIC section behavior
- [x] Extend existing M2b regression and teardown CI
- [ ] Verify all required CI on final branch head
- [ ] Operator review and merge
- [ ] Native Fedora/Sway visual and interaction acceptance
- [ ] Separate HOME workspace swapping/favorites/dossier parity milestone
- [ ] Full CLASSIC retirement only after complete capability matrix acceptance

## NEXT

Check GitHub CI, fix observed test/contract regressions without widening
scope, and preserve rollback/recovery via the feature PR. For the next
migration increment, inventory HOME's `workspaceSection` swapping,
source-status/runtimes and favorites separately from the new WEATHER
overview before deciding on the subject-native dashboard architecture.

## DECISIONS

Bounded GitHub changes only. No local machine mutation, shell restart,
shared collector rewrite, new archive writer, automatic dossier
capture, live Hospital registration, production activation or
unauthorized merge.
