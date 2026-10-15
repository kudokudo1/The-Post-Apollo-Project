✦︎✦︎✦︎ Meta Apollo Logos //

> **ARCHIVED PILOT INSTRUCTIONS // 2026-10-15:** The Git INDEX LAB, LIVE REMOTE and LIVE REPO controls have been retired from the live Git UI by operator request. Git REPO/REMOTE continue to update the real repository and branch information immediately during dragging. This file documents the completed experiment; the reusable `SelectorSlider` preview-release mode and standalone lab fixture remain available for future work.

# F1 // INDEX LAB // GIT-FIRST RUNTIME CHECKPOINT

> STATE // implementation candidate; **not** operator-machine runtime verified
> SCOPE // Git menu only; Hospital FLOOR untouched
> OWNER // Nurse 3A / Team 3; PR must remain reversible until operator acceptance

## Purpose

Test the approved INDEX-profile preview/commit mechanics against the actual
visual identity of the two existing Git selectors, **without executing repo
or remote changes from the test**.

In the Git menu's **CONTROL** view, click `INDEX LAB // TEST`. The lab
appears between the real REPO and REMOTE sliders. Use its two **mock** sliders
with local labels/indices; the mock selectors have no GitService, GitHub
service, or Hospital dependencies. The current REPO and REMOTE are unchanged
and remain live, so use them only if intending an actual selection.

Click `INDEX LAB // CLOSE` to dismiss the lab. Changing away from Git CONTROL
also closes it. If it obstructs the control view, close it before work.

## Operator observation checklist

- [ ] Git menu loads normally; open Git CONTROL and click INDEX LAB // TEST.
- [ ] Real REPO and REMOTE have their original colors, ruler, handle geometry,
      activity lights and clickable behavior.
- [ ] Lab REPO (magenta/orange) and REMOTE (orange/cyan) resemble the two live
      selectors; report any differences before changes go into live sliders.
- [ ] Press and drag a lab handle; yellow PRE // label follows the *candidate*
      while COMMIT readout remains unchanged.
- [ ] Release the pointer; the mock COMMIT readout changes once to the final
      choice, with no Git repo/remote navigation or service operation.
- [ ] Click the track away from the handle; movement animates rather than
      teleports. Begin dragging mid-animation; verify the handle does not jump.
- [ ] Press a handle, move it, press Escape while still holding, and release:
      the committed choice should remain unchanged.
- [ ] Wheel over a mock slider; test Tab focus and Up/Down keyboard stepping.
- [ ] Try dragging beyond track ends; the handle stays on the track.
- [ ] Close/reopen lab and Git menu; ensure no overlays remain stuck.
- [ ] Navigate to Hospital and verify FLOOR remains unchanged (no new
      interaction mode was enabled in Hospital).

## Known boundaries of F1 pilot

- `indexInteraction: "preview-release"` is an **opt-in prototype**; legacy
  behavior remains the default. It should not be applied to the live Git
  sliders until this lab passes and the operator approves a separate
  compatibility migration.
- This pilot tests INDEX only, not numerical VALUE, STEP or dual-handle RANGE.
- Existing preview/committed visual styling and animation remain subject to
  the operator's visual acceptance. No claim of complete implementation of
  decisions 001–035 is made.
- This is a UI fixture, not an automated behavioral test. CI, source syntax
  checks, and operator runtime feedback are separate evidence types.

## Fail-safe

If the lab causes a load error or obstructs work, revert the pilot change or
switch back to the pre-pilot main revision; do not edit Hospital FLOOR to
compensate. Stop rollout until the regression is fixed. No Git repo/remote
behavior should be migrated in this pilot.
