# Automotive instrument // reusable Post-Apollo component

Operator-approved D5d scope: the automotive face is a passive reusable component, not a new recorder or control owner. Its first consumer is CPU++ storage SAMPLE/REPORT, through SelectorDial's existing rotary input.

## Component API

Import `qs.components` (or the existing relative components directory).

| Property | Supported values | Default |
|---|---|---|
| armStyle | tapered, industrial, capsule | tapered |
| armReach | 65–95 normalized design units, capped including stroke | 95 |
| gaugeStyle | segmented, continuous, dualRail, radialTeeth | segmented |
| scaleStyle | ticks, sparse, numbers, none | ticks |
| chassisStyle | square, chamfered, rounded | square |
| chassisClearance | logical pixels per side, 0–40 | 10 |
| faceDiameter | logical pixels | 116 |
| showChassis / showScrews / showGlow | booleans | true |
| showValue / showSetValue | booleans | true |
| accentColor / structuralColor | semantic colors | orange / cyan |
| fraction | normalized remaining/capacity fraction, clamped 0–1 | 1 |
| rotationDegrees | caller-supplied angle, clockwise from top | 360 × boundedFraction |
| valueText / valueUnit / setText | display data | 0 / empty / empty |
| scaleMinimum / scaleMaximum | scale labels, one full revolution (no duplicate endpoint) | 0 / 5 |
| flash | externally observed event emphasis | false |

```qml
AutomotiveDial {
    armStyle: "tapered"
    armReach: 95
    gaugeStyle: "dualRail"
    scaleStyle: "ticks"
    chassisStyle: "square"
    chassisClearance: 10
    accentColor: Colors.cyan
    fraction: 0.64
    valueText: "3.2"
    valueUnit: "SEC"
    setText: "SET // 5 SEC"
}
```

The arm may enter the outer gauge but never exceed the 95-unit radial envelope within the 108-unit face radius. The recessed display stays behind the centrally mounted rotating arm; temporary occlusion is deliberate. No printed scale numbers by default. All four gauge styles remain supported; do not invent a second dial implementation to vary the visual appearance.

`InstrumentChassis` is separately reusable: faceDiameter, clearance, chassisStyle, showScrews, structuralColor. The square default plate is diameter + 20 logical pixels with four symmetric screws. The existing original rotary SelectorDial receives the mounting treatment by default; opt out with showInstrumentChassis: false. Its interaction, modes, ranges, and footprint remain unchanged. SelectorDial exposes stopwatchArmStyle, stopwatchArmReach, stopwatchGaugeStyle, stopwatchScaleStyle when stopwatchFace is true, plus the common chassis properties.

SAMPLE and REPORT retain their owner-provided countdown fraction, observed flash, exact configuration, capture locking and calibration request. The smallest digital layout remains unchanged. No independent clocks, background processes, or new capture ownership. Future presets should store these property values rather than duplicate components.

Native CI and operator visual acceptance are required before declaring the appearance accepted. This document records implementation API in the owning repository; promotion into Syntagma's canonical catalog requires its own documentation ownership check.

## Responsive rendering contract (D5d-b)
Allocate width and height rather than shrinking a 216px texture using Item.scale. AutomotiveDial draws each Canvas at actual face dimensions; normalized coordinates are transformed while painting, not after rasterization. The shared chassis has explicit square-ended high-contrast Phillips cross recesses. The visible face chooses large (>=150px), medium (>=105px), small (>=72px), or compact detail automatically; ticks and gauge segment density reduce before sacrificing legibility. The actual segment count is exposed as segmentCount; litSegments reflects that count. The normalized reach limit remains 95. The upper and lower digital windows are chamfered, with unit text at least 9 logical px. SelectorDial additionally renders an unobstructed value/unit below the plate; the rotating arm remains in front of the recessed windows. CPU++ uses real width/height and retains the original digital control path below a 92px plate allocation (72px face). Original rotary hardware keeps its established angle/input geometry, while the mounting plate and external labels use actual allocated size. Future consumers must allocate geometry directly rather than apply parent scale; external downscaling can still degrade any component. No new background timer or process. Native visual and resource acceptance remain required.
