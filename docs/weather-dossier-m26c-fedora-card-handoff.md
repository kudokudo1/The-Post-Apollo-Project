# Weather Station // M26-C Fedora Native Event-Context Card Acceptance

**STATE:** Verified in isolated Fedora 44 CI; draft PR #1083 unmerged at this checkpoint.  
**PATIENT:** `The-Post-Apollo-Project`  
**ROOM:** Weather Station / Dossier Graphical Interaction Verification  
**STAFF:** External Hospital-compatible ChatGPT worker, not live Hospital registered  
**ASSIGNMENT:** Test the production event-context card's real SAVE DOSSIER pointer path into the independent FileView writer, without changing production files or the operator's desktop.  
**BASELINE AT START:** `main` @ `d66e9e8e1e06180681f2e899ad2db29696c55f0e`  
**VERIFIED HEAD:** `b421848b056791641c9fe60a0a1e636650053ac6`

## IMPLEMENTATION

M26-A verified M25's JavaScript callbacks with simulated FileView IO.
M26-B (merged PR #1080) used real Quickshell 0.3.2 in disposable Debian
CI to verify FileView save, separate-process reload and corrupt-file
write refusal.

M26-C executes **the actual production** `StationEventContextCard.qml`,
its shared `ActionButton.qml` and `WeatherDossierArchiveStore.qml` in
an isolated Fedora 44 Quickshell **0.3.2** process. Fedora's default
quickshell package was 0.2.1 at this checkpoint; the CI-only workflow
selects version 0.3.2 from COPR `errornointernet/quickshell`.
Nothing is installed on the operator's Fedora machine.

A disposable `Xvfb` virtual X11 server and `xdotool` supply native
left-clicks to the actual ActionButton MouseArea; no QtTest signal
shortcuts or direct calls to the card's `dossierSaveRequested` signal.
The fixture supplies a synthetic GDACS event and uses actual M22 preview,
M23 admission, M24 serialization and M25 FileView persistence. The
script creates isolated `HOME` and XDG directories in `/tmp`, copies
only required production code into a temporary Quickshell configuration,
and deletes the test tree at exit. No production `shell.qml`, provider
network request, live compositor, personal files or data migration.

## HOW TO USE

GitHub Actions invokes:
`bash scripts/weather/verify_dossier_card_fedora_m26c.sh`

This is an isolated CI test script, **not** a local deployment procedure.
Do not run against the operator's live Fedora host without scoped
permission.

## VERIFY // OBSERVED GITHUB EVIDENCE

At head `b421848b056791641c9fe60a0a1e636650053ac6`,
**3/3 pull-request workflows succeeded**:

- Weather M26-C Fedora Xvfb dossier ActionButton:
  [run 41584160530](https://github.com/kudokudo1/The-Post-Apollo-Project/actions/runs/41584160530)
- Weather Station Teardown Contracts: run 41584160489
- Meta Apollo Grammar: run 41584160383

The successful native job reports:

```text
Quickshell 0.3.2 (distributed by Fedora COPR)
M26C_UI_PASS // DISABLED_POINTER_IGNORED
M26C_UI_BOOT // ROOT_COMPLETED
M26C_UI_READY // SAVE x=78 y=189
M26C_UI_ARMED // POINTER_CLICK_NOW
M26C_UI_REQUEST // count=1
M26C_UI_PASS // ENABLED_POINTER_SAVED
M26C_UI_PASS // SOURCE_ARCHIVE_SEPARATE
M26C_UI_PASS // ON_DISK_DOSSIER_IDENTITY_VERIFIED
M26C_UI_PASS // FEDORA_XVFB_CARD_POINTER_STORAGE
```

The script verified exact `gdacs | GDACS-M26C-CLICK` provider-native
identity, archive revision 1, a single record, and preserved
`incidentMerge:false` / `persistence:NONE` semantics. It also verified
that **no source-native** `weather-event-archive-v1.json` was created.

### Diagnostic recovery

The first fixture used QtTest `TestCase`; synchronous `Qt.quit()`
aborted with `QtTest/TestSchedule.qml` during an active signal handler.
Deferring quit avoided the crash but the test exited before its conditional
assertions ran. Switching to standalone `FloatingWindow` plus virtual
X11 pointer events avoided that scheduler issue.

Fedora suppressed QML `console.log()` debug output by default. This
made healthy fixture startup appear silent and caused marker timeouts.
The final runner sets `QT_LOGGING_RULES="qml.debug=true"` and passes
`--log-rules "qml.debug=true"` to Quickshell, making the actual
startup, readiness, click and save markers observable. These were
**test harness/environment findings**, not established production bugs.

## WATCH OUT FOR

The validated scope is **card-level pointer-to-persistence integration
in a Fedora 44 Xvfb CI container**.

It does **not** establish:
- Full `StationDiscovery.qml` MAP event selection or event feed behavior.
- Production menu dimensions, Sway/Wayland focus, Stage Director hosting
  or composited rendering.
- The operator's local custom Quickshell build, graphics/input hardware,
  existing archive data, backup/export/retention or crash/power-loss
  durability.
- Operator final acceptance or live Hospital registration.

No production files were modified by M26-C. Other workers remain owners
of subject-based WEATHER and EARTH navigation.

## CHECKLIST

- [x] M26-B verified merged before implementation
- [x] GitHub `main` and ownership preflight
- [x] Actual production card and ActionButton loaded
- [x] Isolated Fedora 44 Quickshell 0.3.2 and Xvfb runtime
- [x] Disabled real pointer ignored
- [x] Enabled real pointer saved exactly once
- [x] FileView output verified from disk
- [x] Independent source-native archive unchanged
- [x] Focused Weather, teardown and grammar CI passed on verified head
- [ ] PR #1083 merged
- [ ] Full MAP surface and operator Fedora/Wayland acceptance

## NEXT

Review and land the **test-only** PR #1083 when authorized.
For the next graphical acceptance milestone, stage an isolated
`StationDiscovery.qml` MAP event selection, preserving source identity,
provider lifecycle ownership and actual card control availability.
Separate local Fedora/Sway checks require explicit operator permission.

## DECISIONS

No local machine change, restart, user data access, persistence-policy
change, automatic capture, production source edit, cross-domain incident
merge, or merge was performed in this assignment.
