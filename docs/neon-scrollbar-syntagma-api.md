# Syntagma // NeonScrollBar reusable API

**Status:** implementation candidate on `nurse3r/syntagma-neon-scrollbar`. The operator-approved design intent remains the 23-rule scrollbar grammar, not this candidate alone.

**Scope:** this document describes the shared component API. Existing consumer-specific colors, dimensions, shadows, decorations and display-only states must be retained during the separate consumer migration stage. Do not infer runtime acceptance from static checks.

## Use the existing component

```qml
NeonScrollBar {
    id: scrollbar
    flickable: contentFlick
    orientation: Qt.Vertical
    placement: "right"
    visibilityMode: "auto"
}
```

The defaults are vertical, right edge, **4 px** edge spacing, **5 px** top/bottom insets, auto-hide without overflow, cyan rail, magenta handle, progressive interaction glow, and click-to-jump. The existing `handleStyle`, `handleGlowStyle`, opacity, geometry and decoration properties remain.

A horizontal instance uses the same component:

```qml
NeonScrollBar {
    flickable: horizontalFlick
    orientation: Qt.Horizontal
    placement: "bottom"      // optional: top
    horizontalWheelMode: "convert" // optional: directional
    reverseWheelDirection: false
}
```

For a pane whose scrollable viewport already accounts for endpoint clearance, set `topInset: 0` and `bottomInset: 0` explicitly to avoid double spacing. Horizontal equivalent: `leftInset` and `rightEndInset`.

## Content clearance is a host layout responsibility

`reserveSpace: true` is the default. Following the operator-approved width correction (audit 01/02), the **physical cross-axis width** remains **10 px** for bar style or **16 px** for star style, including the original 7/14 px handle artwork. Glow clearance must not enlarge the scrollbar or its pointer interaction region.

The three independent measurements are `crossExtent` (physical scrollbar width), `effectiveGlowPadding` (effect-space recommendation, not physical width), and `reservedExtent` (what the host reserves for content). Default reservation is physical width plus the independent **4 px edge inset**: **14 px** for bar or **20 px** for star. `reserveGlowSpace: true` permits a host to reserve additional glow clearance without changing the scrollbar's physical width or input region. **A sibling scrollbar cannot safely rewrite its Flickable's anchors or margins.** The host should reserve the zone using anchors or padding, as AppControl's existing examples already do.

```qml
// Bind an existing host pane's content edge to the scrollbar zone.
// Example when the pane is separately laid out:
anchors.right: scrollbar.left
anchors.rightMargin: 5
```

Use `reserveSpace: false` for an intentional overlay. The component does not automatically mutate host geometry. **Audit issue 04 is operator-decided: preserve the original extended rail.** When `trackTopExtension > 0`, the component does not clip that intentionally protruding rail; standard tracks retain the `containGlow` policy. The host must still provide an appropriate surrounding glow-safe area. This exception preserves Git Repository's `trackTopExtension: 33` without changing the physical scrollbar width. Runtime rendering remains to be verified. Likewise, audit 06 (inactive fade) and audit 09 (whole-pane nested chaining) are still open for operator visual/behavioral review. Review effect clipping in the runtime before accepting the sizing.

## Visibility modes

| `visibilityMode` | Behavior |
| --- | --- |
| `"auto"` | Visible whenever the associated content overflows; otherwise hidden (default effective policy) |
| `"persistent"` | Always present; inactive `0.34` root opacity and no input when the content fits |
| `"reveal"` | Shown in response to enabled hover, scrolling, focus and active drag triggers |
| `"contextual"` | Host sets `contextVisible` |

`visibilityMode: ""` preserves the existing `autoHide` property: `true` means auto and `false` means persistent. This avoids breaking the seven migrated consumers that already set `autoHide`.

For reveal-based scrollbars, `revealMode: "combined"` is the default. Alternatives include `"hover"`, `"scroll"`, `"focus"` or joined combinations such as `"hover+focus"`. Reveal areas and handle-only hover glow are intentionally distinct.

```qml
NeonScrollBar {
    flickable: contentFlick
    visibilityMode: "reveal"
    revealMode: "combined"
    fadeDuration: 500         // 500ms hold, then 500ms fade
    gradualFadeIn: false      // immediate appearance
}
```

The scrollbar remains visible while any reveal trigger or active drag is present; the hold/fade cycle begins when the last trigger ends. A new trigger cancels an exit transition. Fade changes opacity, not reserved layout geometry.

## Input and interaction configuration

| Setting | Default | Variant |
| --- | --- | --- |
| `interactionStyle` | `"progressive"` | `"distinct"` with `pressedHandleColor` / `pressedHandleScale` |
| `trackClickMode` | `"jump"` | `"page"` (rare) |
| `scrollChaining` | `true` | `false` |
| `chainFlickable` | `null` | Explicit outer Flickable for scroll-boundary handoff |
| `horizontalWheelMode` | `"convert"` | `"directional"` |
| `reverseWheelDirection` | `false` | `true`, wheel direction only |
| `useSystemScrollSensitivity` | `true` | `false` to use `wheelStep` |
| `keyboardEnabled` | `true` | `false` |

`chainFlickable` is **explicit**: the component must not guess ownership of arbitrary nested parents. The component's own wheel events consume as much movement as the inner Flickable can use, pass the remainder to the configured outer Flickable, and otherwise release the event at a boundary. It does **not** rewrite the Flickable's native scrolling outside the scrollbar zone; host coordination is still needed during integration.

Keyboard `Keys.onPressed` supports arrows, Page Up/Down, Home/End **when the scrollbar itself owns focus**. Focus-owning panes can call `scrollbar.handleKey(event.key, event.modifiers)` while respecting native text inputs and other child controls. The component never force-focuses itself. Tab order remains the host's responsibility.

## Geometry and backward compatibility

- Vertical default placement: right; left is supported.
- Horizontal default placement: bottom; top is supported.
- `minimumHandleHeight` is capped by actual track length, including for very short tracks.
- Bar/star style remains switchable through the existing `handleStyle` API.
- Handle-hover glow requires pointer containment in the handle's X and Y bounds, not merely in the track.
- Press/drag glow is stronger than hover. Specialized controls may opt into `"distinct"` visuals.
- `autoHide`, `wheelStep`, `clickToJump`, `preserveDragOffset`, `handleGlowStyle`, `railDecoration`, and handle/rail aliases remain available.

**Verification required before main:** run the existing `tests/components/test_neon_scrollbar_contracts.py`, the new `tests/components/test_neon_scrollbar_syntagma_contracts.py`, QML compilation/lint where supported, resize and fade tests, pointer and wheel tests in both orientations, keyboard focus isolation, and review of all legacy consumers. Static contract tests do not prove Qt runtime behavior.
