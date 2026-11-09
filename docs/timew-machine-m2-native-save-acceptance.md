# MACHINE M2 // Native automatic SAVE acceptance gate

**Room:** TimeW MACHINE / desktop recovery  
**Patient:** The-Post-Apollo-Project  
**State:** Native CI test candidate, not operator desktop acceptance  
**Predecessor:** merged PR #1637 (automatic read-and-save coordinator), merged PR #1625 (native floating-window compatibility)  
**Scope:** Real stock Sway, private headless compositor, no user data

## Verification mechanism

The existing isolated two-output test in
`tests/timew/test_machine_geometry_headless_sway.py` now performs a real
capture-and-save transaction after it has launched two identically identified
tiled foot windows and one floating foot window.

It calls the merged `MachineCaptureSaveV2.capture_and_save` with an injected
Sway runner which binds all six read requests to the test's private
`swaymsg -s <private ipc socket>` endpoint. The test's `XDG_DATA_HOME`
is temporarily redirected to the same disposable temporary directory, where
the merged `MachineGeometryStoreV2` writes the atomic v1+v2 records.

The test then reopens the saved UUID using both v1 and v2 readers and
confirms:

- exact output count and workspace geometry in two virtual monitors;
- two distinct checkpoint-local window keys for the repeated app ID;
- floating window preservation and measured nonzero rectangles;
- both legacy-compatible and geometry records exist and are loadable;
- the raw user desktop is never inspected, and any environment override is
  restored in `finally` before the test ends.

## Isolation and guardrails

The test refuses execution outside `CI=true` and `GITHUB_ACTIONS=true`.
It strips inherited Sway/Wayland/DBus environment details and uses a fresh
headless Sway child and private XDG runtime directory. Its only clients are
three disposable `foot` windows. No `TimeW.qml` activation, browser profile
inspection, terminal user session, production checkpoint migration or
compositor move on the operator machine occurs.

This is a **real stock Sway** headless integration check, not a Fedora/SwayPX
visual/runtime acceptance. Sway's three IPC queries are sequential and are
rechecked; this is not a provably atomic compositor snapshot. Browser tabs,
saved note editing and accurate post-reboot restoration remain future gates.

The new test is run by the existing `TimeW MACHINE M2 native headless geometry
capture` workflow because the changed source test is already an explicit
trigger and is already CI-only.

**Required next:** exact-head CI PASS, separate UI integration review, SwayPX
runtime validation and operator visual acceptance. No merge or production
activation without the required authorization.
