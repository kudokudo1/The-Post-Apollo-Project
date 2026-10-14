✦︎✦︎✦︎ Meta Apollo Logos //

# F1 INDEX // REAL GIT REMOTE PILOT

> STATE // staged candidate; runtime verification required before wider rollout
> SCOPE // real REMOTE selection only. REPO and Hospital FLOOR remain legacy.

## Operator verification

This stage follows the operator's successful INDEX LAB confirmation: mock COMMIT
readout waits for release. The next test is the existing real REMOTE selector,
not an automatic migration of all selectors.

1. Open Git menu > CONTROL. Confirm the `LIVE REMOTE // OFF` control is visible.
2. With OFF, the live REMOTE slider behaves exactly as before: index crossings
   request selection immediately. The lab remains separate.
3. Click `LIVE REMOTE // OFF` so it reads `LIVE REMOTE // ON`. This enables
   the preview-release mechanics **only for REMOTE**.
4. Drag the **real** REMOTE slider across rows without releasing:
   the selected remote branch should remain unchanged, and preview indicator
   may show a candidate position.
5. Release at a different remote: it should now select that remote exactly once.
   Verify its displayed selection and target context agree.
6. Wheel and Up/Down on the REMOTE slider: one actual remote selection step per
   input, not an accumulating drag or repeated post-release request.
7. Cancel an unfinished drag using Escape: no new remote should be selected.
8. Switch `LIVE REMOTE // ON` back to OFF. Confirm legacy immediate selection
   works again. Leaving CONTROL or closing Git automatically resets it to OFF.
9. Verify REPO retains immediate selection and Hospital FLOOR retains its
   previous mechanics, colors, glows, activity and layout.

## Limits and safety

- The mock INDEX LAB never calls Git services. In contrast, the live REMOTE
  pilot **does** call the existing `gitService.selectRemote(index)` when a
  selection commits; this changes the target context for subsequent Git work.
- Selecting a remote branch is NOT a push or pull; nevertheless ensure the
  remote you intend is selected before invoking any later Git action.
- Existing activity lights are grounded in real remote activity data.
- No real REPO migration, Hospital migration, VALUE/STEP/RANGE expansion,
  or automatic UI approval is included here.
- Operator visual and behavioral verification is required, separate from CI.
- If any regression appears, toggle OFF and exit the menu; do not proceed to
  Hospital. Revert this narrowly scoped change if the selector does not load.
