# F3 STEP // standalone numeric-detent verification

This is a **standalone mock window**, not a button in Git or Hospital.
It uses the same reusable SelectorSlider component as F1/F2 but opts in
to the `step` profile. No real Git, audio, temperature, or floor operations.

After pulling the implementation into `~/.config/quickshell`, run:

```sh
quickshell -p "$HOME/.config/quickshell/SelectorStepTest.qml"
```

**Important:** the entry file is at the Quickshell configuration root
(alongside `shell.qml`). Do not move it under `tests/` and invoke `-p`
there; doing so breaks QML component imports with `qs-blackhole`.

## Operator visual and interaction checks

- [ ] Window opens; ZOOM owner starts at 40% and TEMP owner at 35 °C.
- [ ] Drag either handle through the numeric detents. **PRE** follows
  distinct discrete values while **OWNER** remains on the original
  selection until mouse release.
- [ ] Release: OWNER changes once to the correct previewed detent;
  the handle does not flick to the old position and back.
- [ ] Click elsewhere on the track: thumb moves to a detent, committing
  that value on release rather than jumping unpredictably.
- [ ] Press Escape during a drag, then release: OWNER does not change.
- [ ] Wheel and Up/Down step one detent at a time with no inertia.
- [ ] The handle stays within the track at the numeric endpoints and
  the detent tick positions match selected numeric values.
- [ ] The center track fills from minimum/bottom to the selected value.
- [ ] No changes appear in Git REPO, Git REMOTE, Hospital FLOOR, or the
  standalone F2 VALUE demo.

The source-contract test also covers a numeric interval that is not a
multiple of its detent spacing: the final shorter interval is kept
reachable rather than silently dropping the maximum.

**This is an F3 first slice, not a certification of all combinations.**
The component still needs actual visual/runtime operator approval before
F3 can be treated as complete or integrated with live systems.
