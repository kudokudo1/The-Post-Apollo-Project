# Weather Station // M26-E Native Multi-provider MAP Identity

**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / MAP-to-Dossier Multi-provider Verification  
**Staff:** External Hospital-compatible ChatGPT worker, not live Hospital-registered  
**Assignment:** Verify all four provider-native MAP marker paths and composite dossier identity using actual Quickshell pointer events, without touching production sources or live desktop.  
**Baseline at start:** `main` @ `d510b4e6225ce2dfc08bc48435f44640b52a3da9`.

## IMPLEMENTATION

Extends M26-D (PR #1087, merged) without changing any production QML.

The M26-E fixture instantiates the real `StationDiscovery.qml`,
`StationEventContextCard.qml`, existing `ActionButton`, and the actual
single-owner `WeatherDossierArchiveStore.qml`. It runs Fedora 44,
Quickshell 0.3.2 and disposable Xvfb with real `xdotool` pointer clicks.

Four separate Quickshell processes run sequentially in **one isolated
XDG data directory**, with the same synthetic provider-native ID
`M26E-SHARED` for each independent event:

1. GDACS: source `gdacs`, row from test-only GDACS service stub.
2. USGS: source `usgs`, test-only retained seismic source object.
3. NASA EONET: source `eonet`, test-only discovery-service stub.
4. NASA FIRMS: source `firms`, test-only manual-hotspot service stub.

The three test service files replace only temporary copies of their
production counterparts, not files in the repository. `stationOpen:false`
keeps actual weather network polling inactive. All event observations are
synthetic and must not be mistaken for real emergencies or telemetry.

For each provider, a genuine pointer click selects a real MAP marker,
the existing MAP controller computes source-specific selected context,
the dossier preview and M23 admission must agree on both provider and
native event ID, and **selection must not write** the archive. A second
real pointer click on SAVE DOSSIER performs the actual M25 FileView
write. The process then closes and the next provider loads the same
persisted file.

The runner reads the disk after **each** save. Expected revisions are
1, 2, 3, 4 with four distinct composite keys, no duplicates, no cross-
source incident merge, no implicit archive writes, and no changes to
`weather-event-archive-v1.json`. A provider's existing records must
not be counted under another provider sharing the exact same ID.

## HOW TO USE

GitHub Actions workflow:
`.github/workflows/weather-dossier-multiprovider-m26e.yml`

Runner:
`bash scripts/weather/verify_dossier_multiprovider_fedora_m26e.sh`

Run **only** in the isolated CI environment unless the operator
separately authorizes the necessary local-machine changes. The script
makes its own temporary HOME/XDG roots and starts/stops a private
virtual X server; it does not operate the live Post-Apollo shell.

## VERIFY

At creation, M26-E native CI was **not yet run**. Only count a pass if
the latest head's focused CI logs include:
`M26E_PASS // FOUR_PROVIDER_MAP_SELECTIONS_DISTINCT_AND_PERSISTENT`
and all four per-source identity confirmations, and Weather teardown
and grammar checks have succeeded.

M26-D previously passed full GDACS MAP click and saved JSON validation.
That earlier success does not substitute for M26-E's additional sources.

## WATCH OUT FOR

This is synthetic **four-source marker selection** on an isolated Fedora
Xvfb display, not real provider network data or final production
acceptance. It does not test the full WeatherStationW subject rail,
the operator's custom Fedora Silverblue Quickshell binary, Sway/Wayland
input/focus, Stage Director containment or crash/power-loss durability.

The source identity test uses an identical synthetic ID across different
providers intentionally; the real providers' ID formats differ. A
`sourceId|eventId` composite key must remain distinct regardless of
that collision.

No provider logic, Widget, service, store schema, retention settings,
user data, TASKS or shared shell files are changed in M26-E.

## CHECKLIST

- [x] M26-D merge and live source inspected
- [x] Syntagma / Hospital source, ownership and GitHub HEAD preflight
- [x] Four source-specific fake data providers confined to disposable CI
- [x] Actual MAP marker → dossier review → save button fixture
- [x] Same-ID cross-provider collision and per-restart raw disk assertions
- [x] Focused Fedora CI workflow and documentation
- [ ] Latest-head multi-provider native CI pass
- [ ] Operator merge and acceptance
- [ ] Real provider and local Wayland/Fedora acceptance separately

## NEXT

Read native job logs, fix only test-runner/fixture issues within scope,
and preserve observed product bugs for owner review rather than rewriting
production source under an unrelated test assignment.

## DECISIONS

Test-only branch. No production edits, live system mutations, archive
migration, automatic capture, cross-source incident merge, PR merge,
or live Hospital registration.
