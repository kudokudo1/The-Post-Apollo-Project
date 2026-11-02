# WEATHER STATION // M23 DOSSIER CAPTURE ADMISSION

STATE // DRAFT CONTRACT, NOT DURABLE STORAGE
PATIENT // `The-Post-Apollo-Project`
ROOM // Weather Station / Cross-Domain Dossier
PROVIDER // OpenAI / ChatGPT (external Hospital-compatible)
ASSIGNMENT // M23 read-only admission policy, explicitly bounded
BASE // `main` at `20c3c9aa92c57ee896465fba04d7e092ebbf3bb6`

## Mechanism

M22 constructs an ephemeral dossier preview from **already-loaded** MAP data.
M23 `StationDossierCapturePolicy.js` checks this candidate before any
future durable archival feature can be considered. The `review()` method
returns `ready`, `reason`, `characterCount` and `saved:false`.
The `stage()` method requires `explicitRequest === true` and returns
a bounded in-memory **UNSAVED_REVIEW_ONLY** packet. Neither method writes.

M19–M21's `WeatherEventArchiveStore.qml` is unchanged and remains the one
writer for operator-requested **provider-native event** snapshots. M23 is
not a replacement, migration, or second writer.

## Admission invariants

- Exact selected source `gdacs | usgs | eonet | firms` and provider-native
  event ID; no cross-source incident merge or duplicate nearby identity.
- Preview format and explicit `VOLATILE_PREVIEW_ONLY` semantics are required.
- Review age is at most 15 minutes; unknown source times are retained as
  `-1` (never parsed as a date), and capture/review time is distinct.
- Bounds are exactly M22's: six nearby, three operational, eight timeline,
  eight relationship entries. Count mismatches and overflow are rejected.
- Frame coverage must not become pixel interpretation. NOAA NWPS gauge identity
  and <=100 km event distance must remain explicit. Nearby independent
  records must stay within 250 km.
- Every relationship must retain reason and limitation, without causal or
  same-incident assertions. Timeline records retain provenance and freshness mode.
- A whitelisted plain-data copy excludes unknown fields and raw frame bytes;
  the returned packet is memory-only and bounded to 24,000 JSON characters.
  This character limit is **not** an on-disk size/quota decision.

## UI

WEATHER > MAP > select a supported event > EVENT CONTEXT:
the dossier preview includes an M23 admission line, either
`REVIEWABLE // NOT SAVED` or a specific blocking reason.
There is **no new SAVE/ARCHIVE action**.

## Verification

`node tests/weather/test_weather_dossier_capture_m23.js` validates:
identity, provider attribution, bounds, time sentinels, staleness,
no-write semantics, mutation isolation, frame/gauge gates and rejection
of invented incident claims.

A focused M23 GitHub workflow runs M13–M22 regressions.
The full Weather teardown also invokes M23. Neither is a graphical
Quickshell runtime test.

## Pending operator decisions before M24 durable storage

1. **Ownership:** separate dossier store vs extension of existing event archive
   (avoid two writers for one file; preserve the source-native event archive).
2. **Retention/quota:** archive event and revision caps, time horizon, and how
   to handle truncation, export, delete and schema migration.
3. **Capture UX:** explicit action, confirmation/readback, visibility of
   `QUEUED | SAVING | SETTLED | ERROR`, and whether to deduplicate unchanged
   evidence while preserving the original provider-observed time.
4. **Recovery:** atomic write, validation after restart, corrupt/unsupported
   schema refusal, rollback and concurrent request sequencing.
5. **Semantics:** do not assert cross-provider incident identity,
   historical attribution, radar pixel interpretations or NWPS catchments.

These choices are **proposals**, not decisions or permissions. Do not create
a persistent file or auto-capture data until the operator authorizes it.

## Recovery pointers

- Candidate: `widgets/weather/StationDossierCapturePolicy.js`
- Volatile source: `widgets/weather/StationDossierPreviewPolicy.js`
- MAP wiring: `widgets/weather/StationDiscovery.qml`
- UI: `widgets/weather/StationEventContextCard.qml`
- Tests: `tests/weather/test_weather_dossier_capture_m23.js`
- Existing M19 owner: `services/weather/WeatherEventArchiveStore.qml`
- Existing provider archive policy:
  `services/weather/WeatherEventArchivePolicy.js`

Current GitHub PR and CI, current ownership, and local visual acceptance must
be rechecked when work resumes. Merge is not runtime acceptance.
