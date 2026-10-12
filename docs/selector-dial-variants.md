# SelectorDial optional free-position variants

The original `SelectorDial` defaults to `selectorMode: "discrete"` and retains the approved Git IGNITION / OPERATION / TARGET behavior. Decisions 010 and 042 add **opt-in** bounded, free-position variants. These are not automatically inserted into the live Git menu.

## Continuous numerical values

Use `selectorMode: "continuous"`, `minimumValue`, `maximumValue`, `currentValue`, `valueDecimals` and `valueStep`. `options` and `displayOptions` are optional reference labels, **not detents**. The full pointer angle is preserved on release; the emitted numeric value is rounded only to the selected decimal precision. The parent must update `currentValue` in response to `valueRequested(value)`.

```qml
SelectorDial {
    labelText: "TEMPERATURE"
    selectorMode: "continuous"
    minimumValue: 0
    maximumValue: 300
    currentValue: root.temperature
    valueStep: 1
    valueDecimals: 2
    options: ["0", "150", "300"]
    onValueRequested: function(value) { root.temperature = value }
}
```

## Named zones

Use `selectorMode: "zones"`, `options` for named regions and `currentIndex` for the committed zone. The parent must echo `selectionRequested(index, value)` by updating `currentIndex`. Dragging stops at the actual release angle inside the selected zone, not necessarily at the label midpoint. Clicking a named label rotates smoothly to that zone's midpoint, then commits. Hover and moving-preview do not issue requests.

```qml
SelectorDial {
    labelText: "HEAT"
    selectorMode: "zones"
    options: ["low", "medium", "high"]
    currentIndex: root.heatZoneIndex
    onSelectionRequested: function(index, value) { root.heatZoneIndex = index }
}
```

Both free-position variants use a bounded arc, default `arcSweepAngle: 300` degrees and computed `arcStartAngle: 90 + (360 - boundedSweep) / 2` (clamped sweep at most 359°); the value or zone at the end is clamped, not wrapped. Mouse drags follow the pointer within these bounds; an intentional flick may coast with friction until settling or reaching an endpoint. Keys and wheel steps are mechanical, and the resulting operation is emitted only after the movement has finished. Existing loading/progress and glow roles are independent.

## Manual visual fixture

`tests/fixtures/SelectorDialVariants.qml` provides two locally controlled dials. It is loaded on demand from **Git → GitHub → Workflow Factory → Mixer → VARIANTS // VIEW**. The original Git dials remain intact and return when the preview closes; the fixture operates only on its own local values, never Git settings or workflows. It is not mounted directly into `shell.qml`.

Verify: the numeric pointer can stop between 0/150/300 labels; fractional readout updates; keys/wheel move the pointer and commit once; LOW/MED/HIGH zones highlight as the pointer passes; a release between labels remains at the release angle even after the owning fixture echoes a zone change. Repeat with mouse flick, click, interrupt, and disabled state. Live Qt visual acceptance remains distinct from source-level checks.


### Default inactive gap direction // six o'clock

The **unused 60° sector** is centered straight down at **6 o'clock** (Qt Quick screen angle +90°), *not* offset to either lower side. For the standard 300° active sweep, start = 120° (bottom-left), end = 420° (= 60°, bottom-right); the excluded sector wraps across the lower 60°..120° angles. Both the TEMPERATURE and HEAT // ZONES fixtures inherit this shared centered default. A specialized control may still override `arcStartAngle`; changing only `arcSweepAngle` automatically keeps the unused wedge centered downward.

Runtime acceptance: verify MIN/LOW and MAX/HIGH sit symmetrically above the unused sector on left/right, and that the pointer cannot move into the bottom gap. Neither the free numerical range, named-zone semantics, nor the original discrete Git dials should change.
