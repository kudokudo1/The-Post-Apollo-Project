# Weather Station // M26-A disposable dossier restart validation

**Patient:** `The-Post-Apollo-Project`
**Room:** Weather Station / Persistent Dossier Recovery
**Worker:** External Hospital-compatible ChatGPT
**Assignment:** Exercise the actual M25 QML JavaScript callback bodies against a
disposable filesystem, without touching the live Quickshell runtime.

## Implementation and scope

- M25 recovery PR #1053 is merged into main; M24 #1047 and subject navigation
  M1 #1051 have also merged.
- Test: `node tests/weather/test_weather_dossier_disposable_restart_m26.js`.
- The test reads the actual `WeatherDossierArchiveStore.qml` implementation,
  extracts `capture()`, `acceptLoaded()`, `eventCount()`, `latest()`,
  `onLoadFailed`, `onSaved` and `onSaveFailed` callbacks into an isolated
  JavaScript VM and executes them with real M22–M25 policy code.
- **A mock FileView** queues text; the disposable test owns an ordinary
  temporary file, writes via temp-file + rename, then calls the real QML
  `onSaved` body. Test-created files live only in an OS temporary directory
  and are removed at the end.
- The suite covers initial absent-file load, explicit save, a busy second
  request, successful write callback, process-style instance recreation,
  reloading exact saved bytes, appending a second dossier, false success
  prevention after synthetic save failure, and read-only refusal for corrupt,
  empty and unsupported-version files.

## Precise verification boundary

**Verified when CI passes:** strict M25 state transition logic and serialized
document recovery, executed against actual disposable filesystem bytes under
the test harness.

**Not verified by this harness:** Qt's `FileView` asynchronous write timing,
Quickshell engine behavior, native atomicWrites implementation, disk fsync,
power-loss durability, full desktop UI, graphical geometry, or user acceptance.

No live Fedora filesystem was modified. No actual
`Quickshell.dataDir/weather-dossier-archive-v1.json` was accessed.
No data was auto-captured from the real world.

## Native acceptance gate

A separate **operator-approved** disposable Quickshell session must be run
using an isolated configuration and data directory, without touching the
existing shell. Check actual SAVE DOSSIER click, FileView callback, restart
and raw-file readback, corrupt-file refusal, focus and geometry. Do not use
`pkill quickshell`, overwrite live settings, or pull/reset the user's
working tree just for verification.

A source merge establishes code availability, not local installation or
runtime acceptance.

## Ownership, rollback, recovery

M26 changes only the test harness, CI configuration and this documentation.
It does not modify Weather or TASKS production source, persistence policy,
archive file, quotas or any control surface.

- Test source: `tests/weather/test_weather_dossier_disposable_restart_m26.js`
- Focused CI: `.github/workflows/weather-dossier-disposable-restart-m26.yml`
- Full teardown: `.github/workflows/weather-teardown-contracts.yml`
- M25 service: `services/weather/WeatherDossierArchiveStore.qml`
- M25 archive policy: `services/weather/WeatherDossierArchivePolicy.js`
- M24 JSON codec: `widgets/weather/StationDossierSerializationPolicy.js`
- M23 admission: `widgets/weather/StationDossierCapturePolicy.js`
- Baseline: `main` at `5b02eb1fea1155861c9da0503ad7c447ce6bf380`.

TASKS focus-contract failure on M25 head was unrelated and did not affect
Weather CI, and remains under its owner. Merge M26 only after CI and operator
approval; no production or live runtime activation is part of this test.
