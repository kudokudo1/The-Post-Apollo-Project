# Weather Station // M28-C SUBJECTS TOOLS Terminal Cutover

**PATIENT:** `kudokudo1/The-Post-Apollo-Project`  
**ROOM:** Weather Station / CLASSIC → SUBJECTS Full Capability Migration  
**STAFF ROLE:** External Hospital-compatible repository worker, no verified live Hospital session/registration  
**ASSIGNMENT:** Transfer the existing STAR MAP and all seven context-console launches from CLASSIC-only controls into `SUBJECTS → TOOLS → TERMINAL` while preserving exactly one Kitty/Sway actor controller.  
**BASE:** `main` @ `99c03c633253ccdc70418d067bfc8d113f8ed630`.

## IMPLEMENTATION

Existing terminal authority already belongs to exactly one
`widgets/weather/StationTerminal.qml` instance in
`WeatherStationW.qml`. That owner controls fixed binary/Kitty arguments,
the configured `weather-screen[-mode]` Wayland app ID, confirmation by
Sway tree, bounded verified geometry, input-mask and
`StationChassisCutout`, and exact app-ID close. M28-C does **not**
instantiate a second terminal, use separate Kitty IPC, or introduce
another session manager.

Previously, TOOLS terminal routes only displayed a passive button that
called `legacyPageRequested`, switched out of SUBJECTS to the CLASSIC
TERMINAL or HOME page, and required a second header click. M28-C
replaces that redirect with a typed launch request:

`StationToolsSubjectPane` → `StationWorkspaceSurface` /
`StationSubjectNavigator` → `WeatherStationW.launchSubjectTerminal(mode)`
→ **existing root `StationTerminal.openTerminal()`**.

- `TOOLS → TERMINAL → STAR MAP` emits exactly `terminal` and uses
  the original `weatherstation-starmap` launcher, identity and viewport.
- `TOOLS → TERMINAL → CONSOLES` supplies the original seven
  context choices: HOME, GROUND, SKY, SPACE, MAP, NEWS and RADIO.
  Their existing Kitty app IDs and title derive from the same
  `StationTerminal.sessionMode`, and every console still uses the
  original plain Bash rather than inventing a new TUI.
- The target mode is allowed only on the matching canonical
  `tools/terminal/*` route, when the Weather Station is open,
  SUBJECTS is active, INDEX is closed, and the original actor is idle.
  Arbitrary strings, wrong-route requests, duplicate launches and
  concurrent starts are rejected by the root.
- The root sets `contextTerminalRequested`, preserving SUBJECTS
  mode and `subjectNavigator.currentPath` while temporarily showing
  the existing terminal viewport above the workspace.
  On the existing **CLOSE** header action, the exact-actor cleanup
  runs, the terminal overlay is hidden and the selected TOOLS route
  becomes visible again.
- The terminal hole masking check now compares the actor's pinned
  session mode with the active SUBJECTS terminal request rather than
  the unrelated legacy `currentView`. The original source of
  verified Kitty geometry and one transparent window cutout remain.
- Original CLASSIC terminal and context-launch controls are
  intentionally preserved until the final approved migration/deletion.
  This is a transfer of existing behavior, not a duplicate implementation.

No data provider, source refresh cadence, event/dossier writer, radio,
weather feed, source store, compositor package or terminal binary has
been changed.

## HOW TO USE

After review, merge and separately authorized desktop deployment:

1. Open Weather Station → SUBJECTS → TOOLS → TERMINAL → STAR MAP.
   Click **LAUNCH STAR MAP**. The existing root Kitty/STAR MAP bay
   appears without opening CLASSIC.
2. For the old context terminals use SUBJECTS → TOOLS → TERMINAL →
   CONSOLES. Select the context mode (HOME, GROUND, SKY, SPACE, MAP,
   NEWS or RADIO), then click **LAUNCH CONTEXT CONSOLE // MODE**.
3. The terminal takes over the main content viewport temporarily.
   Use the existing Weather Station header **CLOSE** to close *only*
   the confirmed matching Kitty actor. You return to TOOLS without
   losing its selected subject route.

The separate Weather Station dismiss action still closes the station
and any active terminal as before.

## VERIFY

`tests/weather/test_tools_terminal_cutover_m28c.js` invokes the
actual root `launchSubjectTerminal` function in a controlled JS
context to prove:

- All eight original mode identities, no new IDs or commands.
- Valid route/mode and active station admission only.
- No second launch, no CLASSIC `currentView`/route change.
- Deferred launch canceled when route, host, mode or visibility changes.
- The original single `StationTerminal`, Sway geometry, input-mask,
  `StationChassisCutout`, exact-actor CLOSE, and one terminal authority.

The revised `tests/weather/test_tools_subject_panels_t1.js` preserves
the original TOOLS health, source catalog, history, storage, location
and provenance contracts while replacing the obsolete expectation
that terminal buttons must open CLASSIC.

`scripts/weather/verify_tools_terminal_controls_fedora_m28c.sh`
uses disposable Fedora 44, Quickshell 0.3.2, Xvfb and *native pointer
clicks* on the real `StationToolsSubjectPane`: select the NEWS
console, activate its launch button, then activate STAR MAP.
The fixture intercepts typed launch **signals** and never contacts
Sway or starts Kitty, so tests cannot manipulate the operator's actor.
W1 and W1r navigation regressions are rerun.

**At document creation, GitHub CI had not yet been observed.**
Do not report native Fedora/Sway compositor integration or final
acceptance as proven by an Xvfb signal test.

## WATCH OUT FOR

- This preserves the original Sway/Kitty compositor-specific actor
  implementation and known Stage Director geometry limitations.
  Fedora/Xvfb proves the controls emit a single request, not that Sway
  positions a real Kitty window correctly inside the live overlay.
- TOOLS controls do not own a new process or shell. The existing
  terminal root intentionally hides the SUBJECTS workspace while
  active, then restores it after close. The header's exact-actor
  CLOSE is the sole operator close action while the overlay is up.
- An incomplete or unregistered Kitty window, missing Sway output, or
  invalid mask geometry is still an existing runtime risk. M28-C does
  not claim to repair those broader Stage Director issues.
- The original CLASSIC route/index quick links remain pending separate
  migration. Removing them before accepted capability parity could
  break unrelated modes and sources.
- All console modes are closed-list identities; do not pass article
  text, filenames, free-form commands or shell interpolated values
  into the root terminal launch function.
- Do not infer live user Fedora/Sway verification or approval merely
  because a native disposable CI test passed.

## CHECKLIST

- [x] Read current Syntagma/OPERATE/AGENTS and GitHub HEAD/ownership
- [x] Identify existing sole StationTerminal and exact-actor controls
- [x] Replace TOOLS terminal CLASSIC redirect with subject-native launch
- [x] Preserve all seven original context console modes and STAR MAP
- [x] Retain root geometry, alpha cutout, app ID and exact-actor cleanup
- [x] Add source-level tests, native click fixture and CI
- [ ] Verify all final-head GitHub checks
- [ ] Operator review/merge
- [ ] Local Fedora/Sway Kitty and input-mask acceptance
- [ ] Transfer the remaining legacy INDEX links and full CLASSIC parity
- [ ] Final CLASSIC deletion/retirement explicitly accepted

## NEXT

Inspect GitHub CI and fix only M28-C findings. Before any production
CLASSIC deletion, independently verify that launching and closing a
real Kitty from SUBJECTS TOOLS returns to its route without terminal
stranding, stray window kill or geometry leakage. Continue with
the remaining INDEX/legacy page jump migration and capability audit
only after the terminal owner is accepted.

## DECISIONS

Only bounded GitHub branch/PR edits. No user-local file write,
checkout/pull/reset, Quickshell restart, package install,
compositor command execution, automatic dossier capture, source
provider change, forced PR merge, production activation or live
Hospital registration.
