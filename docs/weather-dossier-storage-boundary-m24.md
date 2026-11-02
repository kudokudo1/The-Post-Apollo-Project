# Weather Station // M24-A storage boundary and recovery contract

**State:** implementation of a *memory-only serialization probe*; durable storage
architecture is **not** accepted or activated.

**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / Cross-Domain Dossier  
**Staff:** external Hospital-compatible worker, not live registered  
**Assignment:** M24-A candidate serialization / reload refusal without writing  
**Baseline at start:** `03b1ba929cec62e9914bc7e12899fa682c31fb5d`

## Mechanics

1. M22 `StationDossierPreviewPolicy.preview()` assembles currently loaded cross-domain evidence.
2. M23 `StationDossierCapturePolicy.stage(preview, time, true)` returns a bounded, **unsaved** and provenance-validated candidate. It does not save.
3. M24 `StationDossierSerializationPolicy.serialize(staged)` creates a JSON **string in memory**, under 27,000 characters, and validates the exact candidate schema.
4. M24 `inspect(jsonText)` validates a supplied JSON string with **exact** format/version, contents, source identities, limitations and bounds. It does not fetch from a file.
5. M24 `probe(staged)` verifies an in-memory round-trip. It does not prove disk readback, atomicity, persistence or crash recovery.

M24's `post-apollo.weather-dossier-serialization-probe.v0` is a **provisional transport shape**, deliberately marked `UNSAVED_TRANSPORT_PROBE_ONLY`.
It must not be interpreted as a finalized long-lived database schema.
The existing `weather-event-archive-v1.json` and its one-writer
`WeatherEventArchiveStore.qml` are unmodified.

## Validity and security boundaries

The M24 probe rejects malformed or unsupported JSON, unknown versions,
unrecognized extra fields, modified cross-source identity, duplicate nearby
identities, duplicate operational classes, coordinate or timestamp sentinels,
count mismatch, oversized payloads, and removed source limitations.
Only M23's `REVIEWABLE_NOT_SAVED` stage output is accepted for encoding.

**This is validation, not authentication.** A person who can rewrite a JSON
file could forge self-consistent content. The probe includes no signature,
cryptographic integrity claim, source authentication or proof of observation.

A source time of `-1` remains `unknown`, not a fabricated date.
The M23 15-minute admission freshness window applies when the preview is staged,
not when a historical record is replayed. M24 does not discard older valid
historical timestamps, because no retention policy has been approved.

## Future ownership decision (not yet approved)

| Option | Benefit | Risk |
|---|---|---|
| **Separate dossier file with one dedicated writer** | Independent schema and retention; no accidental corruption of provider-native archive | Adds a second storage *domain*, requiring careful registration, backup, sequencing and error handling |
| **Extend M19 source-event archive schema and its sole writer** | Reuses established atomic FileView and write queue | Blurs provider-native evidence vs cross-domain context; migration and per-event retention can silently prune related history |

**Provisional recommendation:** keep provider-native archives and cross-domain
dossiers as separate **logical data domains**. This is not authorization to
create any file, writer, path or running service.

## Operator decisions required for real persistence

- **Ownership / path:** decide whether a new single-owner store is approved.
- **Retention and quotas:** choose event count, captures per event, lifetime,
  total bytes, pruning priority and what happens to older records.
- **Explicit capture UX:** a dedicated user action with clear write state and
  confirmation/readback. M19's ARCHIVE button must not silently change meaning.
- **Concurrency / recovery:** atomic write, readback after restart,
  partial-write protection, unsupported-version refusal, conflict handling,
  backup/export and user-visible failure states.
- **Provenance:** maintain distinct provider/event identities; never treat
  nearby observations or frame coverage as proof of shared incident.
- **Local acceptance:** check actual Quickshell visual layout and runtime
  before considering operator acceptance.

Do not infer numerical storage limits from M22 (6/3/8/8) or M23 (24k characters).
Those constrain a *single review packet*, not total historical retention.

## Verify

Focused: `node tests/weather/test_weather_dossier_serialization_m24.js`  
Regressions: M13–M23 policies through focused workflow  
Full: `.github/workflows/weather-teardown-contracts.yml`

These verify source contracts in GitHub Actions, **not** a real disk write,
reload, local runtime or a permission to merge.

## Recovery pointers

- M24 codec: `widgets/weather/StationDossierSerializationPolicy.js`
- M24 tests: `tests/weather/test_weather_dossier_serialization_m24.js`
- M24 CI: `.github/workflows/weather-dossier-serialization-m24.yml`
- M23 gate: `widgets/weather/StationDossierCapturePolicy.js`
- M22 preview: `widgets/weather/StationDossierPreviewPolicy.js`
- M19 store: `services/weather/WeatherEventArchiveStore.qml`
- M23 handoff: `docs/weather-dossier-capture-m23-handoff.md`

**Next:** verify M24 focused CI and teardown, review PR, then obtain explicit
operator decisions before any persistent M25 storage work. GitHub merge is
technical, not local runtime or final acceptance.
