# Weather Station // W2b Durable HOME Favorites and Card Provenance

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Weather Station / CLASSIC → SUBJECTS HOME Intelligence Migration  
**STAFF:** External Hospital-compatible ChatGPT, no verified live Hospital registration  
**ASSIGNMENT:** W2b namespaced durable panel and per-card bookmarks, with real source provenance and strict refusal on corrupt storage.  
**BASE:** `main` @ `56982637c2e0a298910b3c87c976045237aa2d07`.

## IMPLEMENTATION

W2a PR #1101 merged to main. Its original six HOME panel routes,
MIXED/AUTO/PINNED rotation, HOLD, manual NEXT and 30-second timer are
preserved. It previously retained panel favorites only in memory.

The established `services/favorites/FavoritesStore.qml` owns
`appcontrol-favorites.json` with `favoriteKeys`,
`favoriteDetailActionKeys`, `favoriteMonitorBoxKeys`, and
`favoriteTaskMetricKeys`. Those fields are AppControl-specific and
not a Weather HOME bookmark schema. W2b **does not change this store**.

W2b introduces a dedicated Weather-owned record:

```json
{
  "schema": "post-apollo.weather-home-favorites.v1",
  "version": 1,
  "revision": 2,
  "panelRoutes": ["home/auto", "home/runtime"],
  "cardKeys": ["sky|next-hours"]
}
```

The one writer is `services/weather/WeatherHomeFavoritesStore.qml`,
mounted exactly once by `WeatherStationW.qml`. Its namespaced file is
`Quickshell.dataDir + "/weather-home-favorites-v1.json"`. It uses real
`Quickshell.Io.FileView` with atomic writes, separate from AppControl
favorites, Weather last-known cache, event archive, dossier archive and
provider/history stores. The file contains **stable IDs only**, never
a saved observation value, last-read status, cache or trusted liveness.

`WeatherHomeFavoritesPolicy.js` validates the exact version, revision,
six valid panel paths and bounded (32 maximum) provider+card keys.
Malformed/unsupported/duplicate entries cause fail-closed refusal; the
original bytes remain untouched. No initialization or source refresh
writes an empty file. A write can occur only from an explicit FAVORITE
button, and is acknowledged to the UI after `FileView.onSaved`.
Write failure blocks further updates rather than confirming a phantom
pin. No automatic retry, migration or background recovery is attempted.

The W2a panel FAVORITE button now writes the namespaced record.
`StationSubjectNavigator` retains transient ROTATE, MODE and HOLD,
but mirrors the saved `panelRoutes` after file load/save. These panel
pins survive a complete Quickshell restart.

The original `StationHome` and `StationHomeMetricCard` gain an
**optional** per-watch-card ☆/★ button and a separate source provenance
line. Their existing ranked 60-second AUTO watch logic and content are
unchanged. CLASSIC does not receive a storage handle; thus its cards
remain unmodified visually and never write favorites. Both SUBJECTS
HOME and WEATHER OVERVIEW see the same saved card bookmarks.

`StationHomeCardProvenancePolicy.js` derives card keys from the current
`source|id` pair and reads *current* `StationHome.sourceHealthRows`.
It displays the current source category, rank and source health/age
only when a suitable source mapping exists. Composite NOAA space cards
have no single accurate freshness clock, and are marked **FRESHNESS
UNVERIFIED**, not falsely labelled live. Saved pins that fall out of
the current top-three watch remain visible as identity-only
**NOT IN WATCH** buttons. Clicking those buttons can unpin them; no
previous measurement is replayed or fabricated.

## HOW TO USE

After operator review, merge and separately authorized desktop update:

1. Open Weather Station → SUBJECTS → HOME, and select AUTO or another
   operational submode. Use the existing ☆ FAVORITE in the HOME smart
   deck to save/remove that entire panel across restarts.
2. In HOME → AUTO or WEATHER → OVERVIEW, the ranked watch cards now show
   ☆/★ at their top-right. Click to pin/unpin the particular
   provider-native card identity.
3. Source category, current relevance score, provider health and sample
   age (when verifiable) appear below the card. The additional
   **PINNED CARD IDS** lane allows removing saved cards even when they
   are not currently ranked in the top three.
4. A corrupt/unsupported preference file produces a visible
   **HOME BOOKMARKS UNAVAILABLE** warning and disables writes. It is
   preserved for recovery, never overwritten automatically.

ROTATE remains opt-in. HOLD and NEXT do not modify disk state or
freeze the provider's live observations.

## VERIFY

Dedicated workflow
`.github/workflows/weather-home-favorites-w2b.yml` runs:

- `node --test tests/weather/test_home_favorites_w2b.js`: strict
  version/schema/identity policy, source-age honesty, single writer,
  integration wiring and bad-input refusal.
- W2a, W1 and M27-A existing HOME regressions.
- `bash scripts/weather/verify_home_favorites_fedora_w2b.sh`:
  disposable Fedora 44, Quickshell 0.3.2, Xvfb native click on
  actual `StationHomeMetricCard` pin ActionButton; real namespaced
  FileView save; second Quickshell process readback; invalid-JSON and
  future-version refusal without changing the original bytes. It also
  rejects accidental writes to `appcontrol-favorites.json`.

At handoff creation **the W2b CI outcome is not yet verified**.
Read the latest PR head workflow results before claiming success.

## WATCH OUT FOR

- W2b adds only explicit preferences, **not a weather observation
  archive**. Pinned source cards retain their identity but must derive
  age, relevance and value from currently available sources.
- `sourceHealthRows` is a live view of current Weather/NOAA services;
  provider-specific clocks differ. Composite source cards cannot
  claim a single accurate age.
- The new persistent store is Weather-scoped. No AppControl Favorites
  file, event archive, dossier capture, source cache or History store
  schema is modified.
- The new pin ActionButton is optional and defaults disabled, so
  CLASSIC HOME and other `StationHomeMetricCard` uses are not
  automatically changed.
- The Fedora X11 runner verifies native event and disk behavior but
  not live Fedora Silverblue/Sway appearance, Stage Director focus,
  real network freshness or user acceptance.
- If the existing `weather-home-favorites-v1.json` file is malformed,
  unsupported, or encounters a failed write, no automatic repair or
  retry occurs. Recovery is a separate approved operation.

## CHECKLIST

- [x] Syntagma / OPERATE and current GitHub preflight
- [x] Verify W2a merged and original Favorites ownership
- [x] Independent Weather schema and fail-closed single writer
- [x] Wire persistent panel routes through SUBJECTS without
      duplicating FileView or AppControl ownership
- [x] Optional per-card pin and source provenance, no stale value replay
- [x] Focused Node contracts and native disposable Fedora harness
- [ ] Latest-head CI verified green
- [ ] Operator review and PR merge
- [ ] Native Fedora/Sway visual and input acceptance
- [ ] User final acceptance for CLASSIC → SUBJECTS parity

## NEXT

Review CI logs. Correct only observed W2b test/runtime problems;
preserve the independent store schema and original runtime ownership.
After accepted merge, check actual live panel geometry and whether
W2c should add detailed card explanation drawers or a richer
source-driven HOME deck without replacing the existing ranker.

## DECISIONS

Remote repository only; no local Fedora writes, shell restarts,
production deployment, live provider activation, automatic dossier
capture, shared AppControl Favorites mutation, PR merge or live
Hospital registration. Saved pins contain identities, not evidence
that a provider was live when the user pinned it.
