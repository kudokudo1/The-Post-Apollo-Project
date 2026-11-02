# Weather Station // M25 separate persistent dossier archive

**State:** draft implementation on stacked branch; unmerged and not locally
activated. M24 is the dependency in PR #1047.

**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / Cross-Domain Dossier  
**Worker:** external Hospital-compatible ChatGPT, not live-registered  
**Assignment:** M25 separate one-writer source for explicitly captured dossier
history, keeping the existing provider-native archive untouched.

## Ownership and architecture

The operator's `ok go` continued the recommended **separate, single-owner
cross-domain dossier store** path. This M25 draft adds:

- `services/weather/WeatherDossierArchivePolicy.js`: pure document policy.
- `services/weather/WeatherDossierArchiveStore.qml`: only FileView writer for
  `Quickshell.dataDir + "/weather-dossier-archive-v1.json"`.
- Existing M22 preview -> M23 admission -> M24 in-memory JSON codec -> M25
  standalone archived document. No source-native archive changes.
- UI: **WEATHER > MAP > select event > EVENT CONTEXT > SAVE DOSSIER**.
  This is a separate action from existing **ARCHIVE** (provider-native).
- `shell.qml` creates one new archive owner; WeatherStationW and
  StationDiscovery pass its reference to the selected context card.

## Data and refusal contract

An explicit SAVE DOSSIER action calls `DossierCapturePolicy.stage(...,
Date.now(), true)`; only a successful stage reaches the M25 store.

The M25 store refuses capture during loading, saving, unsupported schema,
file read errors, file write errors, or invalid M23/M24 packet. It uses
`FileView` atomic writes and does not auto-capture on map selection,
provider arrival, or widget load.

The M25 document is `post-apollo.weather-dossier-archive.v1` with a
monotonic integer revision and an append-only ordered array of independently
source-identified records. Every row embeds the M24 validated transport
packet, preserving provider-native event IDs, receive/source/review/capture
times and non-causal limitations. On reload, **every row** must pass the
M24 validation and source-event/identity checks. The parser rejects
unsupported versions, corrupt JSON, unexpected fields, missing or duplicate
sequences, and nested packet tampering.

No silent pruning, deduplication, or rewriting of older records.

## Provisional safety ceilings, NOT final operator retention

- **64 records** maximum per archive document.
- **1,800,000 characters** maximum for the archive's canonical JSON string.
- At capacity the store returns an error and **keeps every existing record**.

These values are implementation guardrails to avoid uncontrolled memory/file
growth, **not** an approved retention horizon, pruning rule or backup policy.
There is no automatic deletion. Operator may refine the limits and controls
before final acceptance.

## Save and recovery evidence

`SAVING` marks a requested atomic FileView write. `SAVED` follows the
FileView `onSaved` callback only. **It is not a proof of disk readback.**
A later normal startup parses the file again, validating every record.
Corrupt/unsupported documents fail closed and are not overwritten.

This version does not implement export/delete, restore-from-backup,
an fsync/durable-commit guarantee, retry after ambiguous failure,
or a separate post-write immediate readback. Do not claim those features.

## Concurrent ownership and branch topology

At implementation start, **M24 PR #1047 remained open** with 3/3 CI green.
M25 branched directly from its head
`06d6e1b185fa4dbcd1cdad8ec24181a3af304a01`.

**M25 must target M24's head branch until M24 lands**, or be rebased
afterward. Do not merge M25 into main first. M0 subject-first navigation
PR #1048 changes only policy/docs/tests and was isolated from M25.

## Verification and acceptance

Focused:
`node tests/weather/test_weather_dossier_persistent_m25.js`

M25 tests confirm strict per-record readback by parsing synthetic on-disk
JSON, source identity, time preservation, rejection of corrupted/unsupported
records, capacity fail-closed, and wiring to UI. CI also runs M13–M24
regressions and the full Weather Station teardown.

This test is **not** a live Quickshell write/restart or visual acceptance.
Before considering operator final acceptance, test a disposable isolated
Quickshell dataDir, atomic save, restart reload, corrupt-file refusal and
UI geometry. Do not restart the operator's live shell without approval.

## Next

1. Verify M25 focused CI and full teardown, repair observed regressions.
2. Have operator review and merge M24 first, then retarget/rebase M25 if needed.
3. After M25 approval and merge, run disposable runtime storage/restart tests.
4. Design backup/export/delete/retention with explicit operator decisions.
5. Verify interactions with subject-first navigation before UI activation.

**No local Fedora files or live shell were changed.**
