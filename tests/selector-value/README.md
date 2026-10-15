# F2 VALUE // Standalone Quickshell manual test

This is an **isolated** two-slider test harness. It has no Git, Hospital,
audio-service, brightness-service or system-operation wiring. It does **not**
appear as a button in any production control menu.

After syncing the tested branch or its eventual merge into a Quickshell
working tree at `~/.config/quickshell`, run in a terminal:

```sh
quickshell -p "$HOME/.config/quickshell/SelectorValueTest.qml"
```

`-p` launches a configuration by QML path. **The entry point must be
at the root of `~/.config/quickshell`**, because Quickshell resolves
`components/` and `tests/fixtures/` relative to its configuration root.
The previous nested `tests/selector-value/shell.qml` path caused
`qrc:/qs-blackhole` by placing both dependencies outside the config root.

This runs a separate mock test window, not your regular `shell.qml`
configuration. Exit the test process with Ctrl+C in the terminal.

If the old command was copied previously, replace it with the exact one
above after pulling updated `main`. If the shell still reports an error,
send the complete `caused by` chain.

## Acceptance checklist

- [ ] The isolated demo window opens without QML import/binding errors.
- [ ] **VOLUME** starts at 35%, **TEMP** starts at 18.5 °C.
- [ ] Dragging changes the large **OWNER** readout *during* the drag,
      rather than only when releasing. No flick to a stale position.
- [ ] The filled center track runs from the bottom/minimum to the thumb's
      current value; maximum is at the top.
- [ ] The handle stays bounded at 0–100% and -40..160 °C at endpoints,
      even while the pointer leaves the track.
- [ ] Wheel steps 5% and 2.5 °C; focus with click, Up increments, Down
      decrements. Numeric values reflect the specified decimal precision.
- [ ] A track click moves to the numeric position; grabbing an already
      moving handle does not teleport it.
- [ ] Disabled/invalid domains do not emit numeric requests (this edge case
      is covered by source-contract checks; no visual toggle is provided).
- [ ] The standard Git REPO/REMOTE selectors still update live branch maps
      while dragging; the Hospital FLOOR control is unchanged.

## Scope / next gate

This is a first working vertical **VALUE** recipe, not an assertion that
horizontal orientation, customizable track origins, dynamic label collision,
flick inertia, STEP detents or RANGE dual handles have been implemented.

The mock OWNER state responds synchronously; an asynchronous real device
controller requires a separate acknowledgement/race test before migration.
The operator's visual/runtime acceptance is still needed. Do not wire F2
into actual volume/brightness controls until a specific owner is chosen.
