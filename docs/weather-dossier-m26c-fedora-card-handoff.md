# Weather Station // M26-C Fedora Virtual-X Native Card-Click Smoke

**Patient:** `The-Post-Apollo-Project`  
**Room:** Weather Station / Dossier Graphical Interaction Verification  
**Staff:** external Hospital-compatible ChatGPT, not live registered  
**Assignment:** native Fedora 44 test of actual event-context card and
ActionButton pointer into independent FileView, isolated from live desktop.  
**Baseline:** `main` @ `d66e9e8e1e06180681f2e899ad2db29696c55f0e`.

## IMPLEMENTATION

M26-A verified M25 QML JavaScript callbacks using a mock FileView.
M26-B (merged PR #1080) exercised real Quickshell FileView save/restart
and corruption refusal in a disposable Debian runner.

M26-C adds a **real production `StationEventContextCard.qml`** and
`ActionButton.qml` smoke in a Fedora 44 container. It copies the
component directory, card, and M22–M25 storage/admission code into a
throwaway configuration, launches actual Quickshell in a throwaway
**Xvfb X11 server** and sends real mouse clicks using `xdotool`.
No production `shell.qml`, provider network, personal data, or real
Wayland desktop is involved.

The test verifies:
1. With `SAVE DOSSIER` disarmed, native left-click must not fire the
   `onDossierSaveRequested` signal or write a file.
2. After a separate timer arms the button, an actual X11 click at the
   ActionButton's QML-computed coordinates must trigger exactly one
   explicit dossier request, with correct M23 staging and M25 persistence.
3. Real FileView saved callback and disk bytes must report the exact
   selected `gdacs` provider-native event ID, and preserve non-incident
   semantics.
4. The distinct source-native `ARCHIVE` button remains unavailable;
   its archive file must not be written.

The fixture originally used QtTest's TestCase. Fedora's Quickshell
0.2.1 was observed aborting when the TestSchedule handler was exited
synchronously; after deferring shutdown, QtTest exited before the
conditional test executed. Those fixture-only attempts did **not**
establish a production issue. M26-C now uses separate Xvfb/xdotool
to avoid QtTest's application lifecycle entirely.

## HOW TO USE

GitHub CI: `bash scripts/weather/verify_dossier_card_fedora_m26c.sh`.
This script intentionally requires installed `quickshell`, `Xvfb`,
`xdotool` and Node. It creates its own isolated `HOME`, XDG directories
and X server. It cleans these up at exit.

**Do not run on the operator's live Fedora Silverblue host without explicit
permission**. This is a CI acceptance test, not a local-install instruction.

## VERIFY

The test requires the marker
`M26C_UI_PASS // FEDORA_XVFB_CARD_POINTER_STORAGE` followed by full
Weather teardown / grammar success. The runner checks actual JSON bytes
and assures no source-native archive file is created.

If virtual X or the old Fedora package lacks a Qt module, report a CI
compatibility blocker instead of weakening the pointer contract or
altering production QML.

## WATCH OUT FOR

This is a **card-level smoke**, not the full StationDiscovery MAP,
production menu geometry, real Sway/Wayland focus, Stage Director,
the operator's custom Quickshell build, physical mouse input, or live
deployment. It exercises native X11 pointer propagation in CI.
Do not overstate that distinction.

The branch modifies **only** test fixture, script, CI workflow and this
handoff. Other Weather workers may modify WeatherStationW and map
surfaces independently; do not overwrite their source.

## CHECKLIST

- [x] M26-B merge and source rechecked
- [x] GitHub ownership and main preflight
- [x] Real card and ActionButton fixture
- [x] Disposable Fedora Xvfb server and native pointer runner
- [ ] Native Fedora virtual-X smoke pass
- [ ] Operator merge/review
- [ ] Full MAP and local graphical acceptance separately

## NEXT

Inspect CI evidence. Fix only isolated test/environment issues.
If actual product QML fails, report the symptom and obtain scope approval
before changing production code or shared components.

## DECISIONS

Test-only GitHub branch. No local machine modification, production edit,
live Quickshell restart, merge, automatic capture, storage migration or
final user acceptance.
