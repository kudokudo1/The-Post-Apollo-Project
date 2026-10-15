✦︎✦︎✦︎ Meta Apollo Logos //

# F1 INDEX // REAL GIT REPO PILOT

> STATE // opt-in implementation candidate, not operator runtime certified
> PRIOR ACCEPTANCE // Git REMOTE ON: correct selection only on release; OFF and ON: no flick (2026-10-15)
> SCOPE // real Git REPO; Hospital FLOOR remains legacy

## What this changes

The Git CONTROL page has three separate controls along its top:
- **LIVE REPO // OFF** (left of INDEX LAB)
- **INDEX LAB // TEST** (middle; mocked values only)
- **LIVE REMOTE // OFF** (right; already verified with real remote selection)

The REPO control is OFF at each menu open. When ON, dragging the actual
REPO slider previews index changes. Releasing sends exactly one request
through its existing `gitService.selectRepo(index)` handler, which switches
the active repository and refreshes Git data. The component's DEFAULT remains
legacy; no Hospital switch is activated.

## Operator live comparison

1. Sync approved branch/merged main, reload Quickshell. Open Git > CONTROL.
2. Keep LIVE REPO // OFF. Select a different repository using the actual
   REPO slider and verify immediate selection still works, without flick.
3. Turn LIVE REPO // ON. Starting at one real repository, press/drag to
   another, but DO NOT release yet. The actual current repository and loaded
   Git data should stay on the original repository; preview moves instead.
4. Release. Verify the active repo changes to the intended repo ONCE and the
   Git surface refreshes to that repository without flick, late rollback,
   extra refresh loops, or accidental follow-up selection.
5. Repeat with track click, rapid drag, top/bottom endpoints, and while Git is
   refreshing. If owner data changes mid-drag, the component should cancel
   the stale preview instead of committing an outdated index.
6. Compare the REPO slider's magenta/orange identity and movement against
   previously accepted REMOTE. Check that REMOTE's orange/cyan activity
   indicators still represent real data.
7. Turn REPO OFF and verify legacy behavior again. Navigate away from CONTROL
   or close the menu; returning should show REPO OFF and REMOTE OFF.
8. Confirm Hospital FLOOR remains entirely unchanged.

## Precautions and stop rules

- **LIVE REPO // ON is real, not a mock.** A committed selection changes the
  active repo and downstream Git context; verify the repo name before any
  subsequent Git action. Do not test by pushing, pulling, resetting, or
  committing anything. No such operation is triggered by the slider itself.
- If a selection jumps to a different repository from the one released, or
  refresh loops/selection flick reappear, turn REPO OFF and report exact
  sequence. Do not proceed to Hospital.
- This is a targeted proof of functionality, visual identity, and input feel.
  No blanket certification of all SelectorSlider capabilities is implied.
