# Weather Station // M26-C Fedora Offscreen Card Pointer Smoke

**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / Dossier Graphical Interaction Verification  
**Staff:** external Hospital-compatible ChatGPT; no live Hospital registration  
**Assignment:** native Fedora 44 test of actual event-context card, ActionButton pointer, independent FileView writer; no live desktop mutation  
**Baseline:** `main` @ `d66e9e8e1e06180681f2e899ad2db29696c55f0e`.

## IMPLEMENTATION

M26-A verified the M25 store's QML JavaScript callback bodies against a
disposable filesystem. M26-B then exercised **actual Quickshell FileView**
save/restart/refusal in Debian CI, merged as PR #1080.

M26-C adds one more bounded integration test: the **actual production
`StationEventContextCard.qml`** and its imported `ActionButton.qml`,
inside a visible, offscreen Qt `Window` in a disposable Fedora 44
GitHub Actions container. The shell copies components, weather card and
M22–M25 storage/admission policies into temporary XDG directories.
It loads no production shell, news provider, map service or personal data.

The QML `QtTest.TestCase` locates the ActionButtons by their displayed
labels and attempts actual native pointer clicks:

1. Verify `SAVE DOSSIER` is visible but disabled before the fixture
   explicitly enables capture; clicking it must request no write.
2. Verify independent `ARCHIVE` remains unavailable, and cannot be
   implicitly activated by dossier capture.
3. Enable the dossier button after the separate dossier store opens
   as an empty archive; click it with QtTest's native mouse event helper.
4. Assert one `onDossierSaveRequested` call, one native `dossierSaved`
   callback, and one persisted dossier with exact source-native ID.
5. Confirm no `weather-event-archive-v1.json` source-native archive file
   was written by this cross-domain save path.

The test script removes the temporary tree on exit; there is no live
`~/.config/quickshell`, shell restart or Wayland compositor connection.

## HOW TO USE

CI: `bash scripts/weather/verify_dossier_card_fedora_m26c.sh`.

This is intentionally a GitHub CI test. Do **not** deploy to or execute
on the operator's live Fedora Silverblue host without separate local
permission. The script is sandboxed, but review still matters.

## VERIFY

At PR creation, Fedora native CI was not yet confirmed. A successful result
must show `M26C_UI_PASS // FEDORA_OFFSCREEN_CARD_POINTER_STORAGE` in the
CI logs and pass the M25 source regression. If QtTest cannot issue a mouse
event in offscreen mode or Fedora's Qt/QML module dependency is missing,
report a test-environment blocker, not a production bug.

## WATCH OUT FOR

This is an **isolated event-context CARD-level smoke**, not the full
`StationDiscovery.qml` map, production UI geometry, Wayland focus,
Stage Director embedding or the operator's custom Quickshell binary.
The fixture reproduces the card's M23 admission and save signal wiring
and uses real M22–M25 policies and the actual M25 FileView store.

Avoid changing `StationEventContextCard.qml` and `WeatherStationW.qml`
without coordinating Weather workers; this test owns only its fixture,
script, CI workflow and handoff.

No retention/pruning/export policy is changed, and no automatic capture
or cross-source incident merge is introduced.

## CHECKLIST

- [x] M26-B merged and source rechecked
- [x] Fresh GitHub `main` / concurrent owner preflight
- [x] Actual-card isolated Fedora fixture
- [x] Disposable XDG runner
- [x] Fedora package CI workflow
- [ ] Fedora native test passes
- [ ] Operator merge/acceptance
- [ ] Full MAP inspector and local visual acceptance separately

## NEXT

Diagnose Fedora test environment and resolve only fixture/CI issues. If
the production card itself fails to load, document the exact Qt error
and request a production owner decision before widening scope.

## DECISIONS

Test-only GitHub work. No Fedora user-host change, production source edit,
live Quickshell restart, merge, Hospital registration or final acceptance.
