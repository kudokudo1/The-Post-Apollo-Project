# F5 RANGE // standalone Quickshell acceptance

RANGE is the fourth opt-in `SelectorSlider` profile. It does not show up in
the Git or Hospital menu, and the demo makes no external system changes.
F0–F4 INDEX, VALUE, STEP and Dial/IndexRail behavior remain as accepted.

After pulling the latest tested `main` into `~/.config/quickshell`, run:

```sh
quickshell -p "$HOME/.config/quickshell/SelectorRangeTest.qml"
```

**Use the root-level `SelectorRangeTest.qml` file.** Running a nested
`tests/...` file as the configuration root breaks Quickshell imports.

## What to try

- [ ] Both mock controls appear: FILTER initial `20–75%`, THERMAL
      initial `-15 to 45°C`; each has two distinct LO/HI handles.
- [ ] Drag LO upward toward HI. PRE changes while OWNER stays still.
      Drag beyond HI: handles **meet but never cross** (zero-width legal).
- [ ] Drag HI downward toward LO. The same hard stop applies.
- [ ] Release: OWNER updates to the previewed interval exactly once;
      no flick to the old interval and back.
- [ ] Drag the cyan/orange highlighted band between the two handles:
      **both ends move together**, preserving the interval width.
      Shift+drag anywhere on the track also moves the whole interval,
      even when too narrow to grab the band.
- [ ] At hard track endpoints, the interval moves no farther and remains
      within the numeric domain.
- [ ] Escape while holding a handle cancels an uncommitted preview.
- [ ] Clicking a handle and using Left/Right chooses LO/HI; Up/Down or
      the wheel moves that endpoint by the configured numeric step.
- [ ] The LO/HI colors, labels, fill and glow remain legible, including
      when both handles occupy one value.
- [ ] Git REPO/REMOTE still show live context as you drag, Hospital FLOOR
      retains LIVE FLOOR OFF/ON, and VALUE/STEP demos remain unchanged.

**Decision 036 is still paused.** F5 does **not** impose any separate
minimum/maximum span. A zero-width interval is allowed, limited only by
the overall domain endpoints. The hard collision policy is implemented;
future push/cross alternatives are documented capabilities, **not**
pretended to be complete in this first F5 slice.

This is a demonstration with synchronously acknowledged mock owner values;
source/CI checks cannot substitute for operator Quickshell runtime testing.
