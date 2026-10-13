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

For a pane whose scrollable viewport already accounts for endpoint clearance, configure **`viewportHasEndpointClearance: true`**. The scrollbar then does not insert duplicate insets, while preserving the **5px top/bottom defaults** (and horizontal **5px start/end defaults**) for panes without external endpoint clearance. Individual `topInset`, `bottomInset`, `leftInset`, and `rightEndInset` remain available for dedicated geometry.

## Content clearance is a host layout responsibility

`reserveSpace: true` is the default. Following the operator-approved width correction (audit 01/02), the **physical cross-axis width** remains **10 px** for bar style or **16 px** for star style, including the original 7/14 px handle artwork. Glow clearance must not enlarge the scrollbar or its pointer interaction region.

The three independent measurements are `crossExtent` (physical scrollbar width), `effectiveGlowPadding` (effect-space recommendation, not physical width), and `reservedExtent` (what the host reserves for content). Default reservation is physical width plus the independent **4 px edge inset**: **14 px** for bar or **20 px** for star. `reserveGlowSpace: true` permits a host to reserve additional glow clearance without changing the scrollbar's physical width or input region. **A sibling scrollbar cannot safely rewrite its Flickable's anchors or margins.** The host should reserve the zone using anchors or padding, as AppControl's existing examples already do.

```qml
// Bind an existing host pane's content edge to the scrollbar zone.
// Example when the pane is separately laid out:
anchors.right: scrollbar.left
anchors.rightMargin: 5
```

Use `reserveSpace: false` for an intentional overlay. The component does not automatically mutate host geometry. **Audit issue 04 is operator-decided: preserve the original extended rail.** When `trackTopExtension > 0`, the component does not clip that intentionally protruding rail; standard tracks retain the `containGlow` policy. The host must still provide an appropriate surrounding glow-safe area. This exception preserves Git Repository's `trackTopExtension: 33` without changing the physical scrollbar width. Runtime rendering remains to be verified. Audit 06 (inactive fading) remains visually undecided by the operator; preserve surface-specific layered appearance pending actual Quickshell comparison. **Audit 09 is decided: containment throughout the inner list is the default, and chaining is an opt-in variant.** Review effect clipping in the runtime before accepting the sizing.

## Visibility modes

| `visibilityMode` | Behavior |
| --- | --- |
| `"auto"` | Visible whenever the associated content overflows; otherwise hidden (default effective policy) |
| `"persistent"` | Always present; explicit mode uses inactive `0.34` root opacity and no input when the content fits |
| `"reveal"` | Shown in response to enabled hover, scrolling, focus and active drag triggers |
| `"contextual"` | Host sets `contextVisible` |

`visibilityMode: ""` preserves the existing `autoHide` property: `true` means auto and `false` means persistent. In legacy `autoHide: false` mode, **no extra root-level inactive fade is applied** so existing Workflow Library and Repository Profile per-layer opacities remain unchanged. The shared root opacity (`0.34`) applies only when the host explicitly opts into `visibilityMode: "persistent"`; operator has deferred final visual selection for audit 06.

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
| `nestedScrollMode` | `"contain"` | `"chain"` (explicit variant) |
| `captureNestedPaneWheel` | `true` | `false` when the host already owns wheel routing |
| `chainFlickable` | `null` | Explicit outer Flickable for opt-in scroll-boundary handoff |
| `horizontalWheelMode` | `"convert"` | `"directional"` |
| `reverseWheelDirection` | `false` | `true`, wheel direction only |
| `useSystemScrollSensitivity` | `true` | `false` to use `wheelStep` |
| `keyboardEnabled` | `true` | `false` |

**Operator decision 09 — stop at the end:** When the scrollable pane is genuinely nested inside another Flickable, a scoped WheelHandler on that *inner pane* handles the wheel anywhere inside the list and always consumes the event, even when the inner content cannot move farther. The outer pane stays still. Standalone panes preserve Qt's native wheel behavior by default. `nestedScrollMode: "chain"` explicitly opts back into passing scroll remainder to `chainFlickable`; host-level full-pane chaining would need separate coordination. This is not permission to extend the invisible hit zone around the thin scrollbar.

Nested-pane pointer/wheel behavior depends on actual QML event dispatch. The static source contracts are insufficient to certify its runtime behavior: test event blocking at both top and bottom while a visible outer pane surrounds the list.

Keyboard `Keys.onPressed` supports arrows, Page Up/Down, Home/End **when the scrollbar itself owns focus**. Focus-owning panes should call **`scrollbar.handleFocusedPaneKey(event)`**, which uses the official Qt `Window.activeFocusItem` attached property and skips text-input focus owners as well as Ctrl/Alt/Meta shortcuts. The component never force-focuses itself. Tab order remains the host's responsibility. Focus-reveal still watches the currently focused scrollable pane, not a global window.

## Geometry and backward compatibility

- Vertical default placement: right; left is supported.
- Horizontal default placement: bottom; top is supported.
- `minimumHandleHeight` is capped by actual track length, including for very short tracks.
- Bar/star style remains switchable through the existing `handleStyle` API.
- Handle-hover glow requires pointer containment in the handle's X and Y bounds, not merely in the track.
- Press/drag glow uses each consumer's **own idle and hover recipe**, progressing upward only when idle-to-hover already increases. Equal idle/hover glow intentionally remains equal on press; an explicit positive pressed opacity/spread override remains possible. Specialized controls may opt into `"distinct"` visuals.
- `autoHide`, `wheelStep`, `clickToJump`, `preserveDragOffset`, `handleGlowStyle`, `railDecoration`, and handle/rail aliases remain available.

**Verification required before main:** run the existing `tests/components/test_neon_scrollbar_contracts.py`, the new `tests/components/test_neon_scrollbar_syntagma_contracts.py`, QML compilation/lint where supported, resize and fade tests, pointer and wheel tests in both orientations, keyboard focus isolation, and review of all legacy consumers. Static contract tests do not prove Qt runtime behavior.
