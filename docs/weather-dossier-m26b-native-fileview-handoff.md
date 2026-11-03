# Weather Station // M26-B Native Quickshell FileView Verification

**State:** draft native CI smoke, awaiting CI execution and operator acceptance  
**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / Persistent Dossier Recovery  
**Worker:** external Hospital-compatible ChatGPT (not live Hospital-registered)  
**Assignment:** native FileView save/restart/corruption verification, no live desktop mutation  
**Base at start:** `main` @ `dfebb7b1ec89814be83a3475fe1596afd398e156`

## IMPLEMENTATION

M26-A was a JavaScript callback test with simulated FileView IO. M26-B
starts a **real Quickshell binary** in a disposable Debian GitHub Actions
container using an isolated `ShellRoot` QML configuration.

The test runner copies only these production source files into its temporary
config under `/tmp/weather-m26b-native.*`:

- `services/weather/WeatherDossierArchiveStore.qml`
- `services/weather/WeatherDossierArchivePolicy.js`
- `widgets/weather/StationDossierPreviewPolicy.js`
- `widgets/weather/StationDossierCapturePolicy.js`
- `widgets/weather/StationDossierSerializationPolicy.js`

A fixture `tests/weather/fixtures/M26NativeDossierShell.qml` calls a
single explicit M23 dossier stage and M25 capture, observes the actual
`dossierSaved` signal, then exits. A new Quickshell process reopens the
same isolated data directory to validate stored provider identity and
sequence number. A third process attempts to load corrupt JSON and proves
capture is refused while the corrupt bytes are unchanged.

Only the script-owned temporary `HOME`, `XDG_DATA_HOME`,
`XDG_CONFIG_HOME`, `XDG_CACHE_HOME` and `XDG_RUNTIME_DIR` are used.
`DISPLAY` and `WAYLAND_DISPLAY` are unset; Qt uses the
`offscreen` platform. There is **no PanelWindow**, compositor interaction,
external provider polling or production `shell.qml`. An outer timeout
terminates a hung Quickshell, and the script deletes its own temporary tree.

## HOW TO USE

CI runs:

`bash scripts/weather/verify_dossier_native_m26b.sh`

Native Quickshell must be installed. **Do not run the script against the
operator's live desktop without separate explicit local-machine approval.**
The script is written to sandbox itself, but a test should still be reviewed
before execution on a live operating system.

The expected terminal marker is
`M26_NATIVE_PASS // ISOLATED_FILEVIEW_SAVE_RELOAD_REFUSAL`.

## VERIFY

- M25 recovery PR #1053 merged, with dossier store present on `main`.
- M26-A #1057 merged with all five associated CI workflows successful.
- This M26-B workflow runs `debian:unstable`, installs packaged Quickshell,
  Qt's QPA platform plugins and Node, then runs M26-A regression before the
  native FileView lifecycle probe.
- Native CI pass **has not yet been observed** at PR creation.
- If the native runner cannot load the offscreen Qt platform or package
  dependencies, report a CI/environment blocker rather than claiming
  FileView behavior was tested.

## WATCH OUT FOR

A native save/load pass verifies actual FileView behavior for the Debian
Quickshell package within this isolated test. It **does not** verify the
operator's Fedora Silverblue Quickshell build, local graphical UI geometry,
mouse/focus interaction, power-loss durability, backups, or a production
installation. The version printed by CI is part of the test evidence.

There is a separate Weather EARTH subject-workspace worker; do not edit its
view files or activation seams in this test-only milestone.

## CHECKLIST

- [x] Verify M26-A and M25 main state
- [x] Inspect Weather and concurrent PR ownership
- [x] Native Quickshell fixture and temporary-XDG runner
- [x] GitHub Actions Debian native job
- [ ] Native CI pass
- [ ] Operator review / merge
- [ ] Local visual and production-build acceptance if approved

## NEXT

Resolve any observed test-runner compatibility problems. Keep M26-B
test-only; do not modify production FileView logic without a verified
runtime failure and separate scoped approval. After native CI pass,
consider operator-approved visual and Fedora runtime verification.

## DECISIONS

No production source changed. No local files, live shell, persistent user
archive, main branch or live Hospital assignment was modified. No merge.
