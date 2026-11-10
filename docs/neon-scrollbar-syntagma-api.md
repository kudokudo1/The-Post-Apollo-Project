# Syntagma // NeonScrollBar reusable API

**Status:** reusable API on `main`; box-side alignment is the operator-approved default (2026-10-16). Earlier viewport-relative geometry and the 23-rule scrollbar grammar remain available for intentional exceptions.

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

The defaults are vertical, right edge, **box-side geometry**, **4 px** edge spacing, and **2 px** clearances at the usable box's top/bottom. Auto-hide, cyan rail, magenta handle, progressive interaction glow and click-to-jump are unchanged. The original **5 px viewport-relative** endpoint insets remain intact for deliberate `geometryMode: "viewport"` consumers. The existing `handleStyle`, `handleGlowStyle`, opacity and decorations remain.

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

## Track placement: box side versus content viewport

The scrollbar now defaults to `geometryMode: "box"`: the **track** belongs to the usable side of the containing box, not to the rows/cards or the Flickable's padded viewport. It uses its mounting parent as the box by default, including when `mountingParent` moves the bar out of a Column. When the pane has direct visible header/footer siblings inside that box, the track begins after the header and ends before the footer. Otherwise it fills the box side with `boxTopInset: 2` / `boxBottomInset: 2` (and 2 px horizontal start/end clearances). Right/left edge spacing still uses the independent `edgeInset` family. Only the track changes extent; the moving handle still represents the Flickable's scroll position and range.

For a more complex nested layout, set `geometryHost: someSection` to identify the exact usable box. If the resolved parent is a scrolling Flickable **or its generated contentItem** (whose height can exceed the viewport), or `trackTopExtension > 0` is intentional, the safe legacy viewport behavior remains the fallback; `geometryMode: "viewport"` explicitly preserves it in any host. Horizontal rails use the same box-side policy. Do not choose the top of a large menu when it would cross unrelated headers or controls: supply the correct enclosing section or explicitly use the viewport mode.

```qml
NeonScrollBar {
    flickable: cardList
    geometryMode: "box"          // default; section side, not card height
    boxTopInset: 2               // default, independent of viewport padding
    boxBottomInset: 2
}

// Intentional compact/specialty indicator:
NeonScrollBar {
    flickable: compactList
    geometryMode: "viewport"     // original 5px viewport endpoint policy
}
```

**Content reservation stays with the host.** This change does not resize a Flickable, claim a new pointer hit area, or move the 10/16 px physical bar width. Host layouts must still reserve `reservedExtent` (plus chosen breathing room) next to their content. Custom rails, overlapping siblings, scrollable outer containers, and decorative extensions need live validation.

For a pane using **`geometryMode: "viewport"`** whose scrollable viewport already accounts for endpoint clearance, configure **`viewportHasEndpointClearance: true`**. The scrollbar then does not insert duplicate insets, while preserving the **5px top/bottom defaults** (and horizontal **5px start/end defaults**) for panes without external endpoint clearance. Individual `topInset`, `bottomInset`, `leftInset`, and `rightEndInset` remain available for dedicated geometry.

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


## Positioner-hosted scrollbars must remain inside their visual box (2026-11-10)

> **Status:** Proposed technical rule and diagnosed Git CHANGES host defect.
> Implementation in `GitChangesView.qml` belongs to the Nurse 3r
> [scrollbar-coverage PR #252](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/252),
> not this documentation-only branch. Operator desktop verification is pending.

**Issue:** A standard scrollbar can appear **below the menu or outside its
containing box** even when its target `Flickable` has `clip: true`. The
`NeonScrollBar` component is reparented by default to the target's
`flickable.parent`. If that parent is a Qt Quick `Column`, `Row`,
`Grid` or other auto-positioning container, the scrollbar itself becomes a
layout child and can be placed *after* the viewport. Flickable clipping does
not constrain a scrollbar that is no longer inside the Flickable.

**Proposed host-side rule:** The **track** and the moving **handle** must
remain within the usable section of the same bordered menu box as the
scrollable content. A normal vertical track must use the shared component's
right-side box placement, 4px edge inset, 2px box-top/bottom clearances, and
its approved star/bar artwork for the owning module. Only an explicitly
authorized extension such as `trackTopExtension` may protrude beyond the
normal box. Do not silently widen the pointer/drag area to include glow.

When a scrollable pane is inside a `Column` or another positioner, use a
**non-positioning overlay parent** and bind the geometry to the **actual
scroll viewport/section**, not to a full window, a scroll-content `Column`,
or the positioning parent's content height:

```qml
// Example only: verify the parent hierarchy of the actual host first.
NeonScrollBar {
    flickable: changesScroll1
    handleStyle: "star"                 // Git/Hospital established variant
    mountingParent: changesScroll1.parent.parent // must be a non-positioner
    geometryHost: changesScroll1       // exact scrollable box
    // geometryMode: "box" is the default.
}
```

The preferred alternative is a dedicated non-positioning `Item` viewport
wrapper that owns the Flickable and the scrollbar as separate overlay siblings.
The host must reserve `reservedExtent` next to list content, preventing the
rail/handle from obscuring the last characters or row actions. Do not solve
the problem by setting `clip: false`, pushing tracks outside the window, or
modifying `NeonScrollBar` defaults to compensate for one incorrectly mounted
host.

**Git CHANGES audit:** At the source checkpoint
`79b67639f194df6f8a70cce3c87f219b6a041287`, the bars bound to
`changesScroll1`, `2`, `3`, `4`, `6`, and `7` are declared under
`Column`-hosted Flickables without an explicit `mountingParent`; their
default reparenting can turn each rail into a Column layout child.
`changesScroll5` uses a different Rectangle parent and must be reviewed
individually, not blindly normalized.

**Verification required:**

1. Inspect the resolved `scrollbar.parent` at runtime. For a normal
   overlaid track, it must **not** be an auto-positioned Column/Row child.
2. Force content longer than the viewport, and measure actual track
   `x`, `y`, `width`, `height` against the bordered scroll section. Include
   header/footer clearance and do not count shadow padding as hit geometry.
3. Check all relevant Git CHANGES submodes (FILES/preview, HUNKS/lines,
   STASHES/preview, CONFLICTS), window resize, empty states, auto-hide,
   keyboard focus and nested-wheel containment.
4. Keep Git's star-shaped handle, configured glow and source palette.
   Do not alter staging, commit, stash or conflict execution paths.
5. Run the canonical NeonScrollBar source/native tests and a host-level
   native geometry regression. Live Quickshell/operator visual acceptance
   remains separate from CI.

**Ownership/relationship:** This extends the existing box-side geometry,
host-owned reservation, positioner mounting and audit-04 deliberate-extension
contracts on this page. It is a *host mounting rule*, not an instruction to
rewrite the shared `NeonScrollBar.qml` renderer or another worker's owned
`GitChangesView.qml` without handoff.


## Compact CPU++ rounded scrollbars: stage 1 before star migration (2026-11-10)

> **State:** staged implementation, awaiting CI and operator visual acceptance.
> The operator explicitly requested to **repair and inspect the rounded bars
> first**, and only then consider star-shaped indicators. Do not conflate the
> two milestones or silently alter the global bar shape.

**Shared rule (proposed for visual acceptance):** Every independently
scrollable list must expose a position indicator when its content exceeds
the available viewport. It must sit **inside its own bordered panel**, use
the shared `NeonScrollBar` geometry, reserve real space between the bar
and text/buttons, and be centered crosswise within its own slim track.
Do not align an indicator to the whole window when only a subpanel scrolls.
Do not place its parent inside a Qt auto-positioning `Column`/Row.

**CPU++ stage-1 concrete layout:**

- Normal vertical bars use `handleStyle: "bar"` even if a separate owner
  later changes Git/Hospital to `"star"`.
- Use `geometryHost: theActualFlickable` so the track sits within the
  *scrollable viewport*, with the shared 2px top/bottom and 4px right inset.
  In a positioner-backed pane, wrap the scrolling viewport in a
  **stable non-positioning Item** that is the single Column child, and mount
  the scrollbar as the Flickable's sibling inside that same Item. This
  avoids stale `mapToItem` origins when the Column reflows. Leave pinned
  controls outside the viewport wrapper.
- Reserve at least 24px total from the scroll area width before drawing
  list-row text, cards, or action controls. The current bar's physical
  width is still 10px and the visible 7px handle is centered inside it.
  Glow does not add input-hit width; verify the actual breathing room.
- The new opt-in `maximumBarHandleHeight` limits how long a **rounded**
  handle can become. For this initial CPU++ proposal, it is `42` px.
  Default `0` retains the entire preexisting proportional-length behavior
  everywhere else, including other widgets' scrollbars.
- A capped handle intentionally gives up an exact visual fraction
  of content visible, but its **vertical position** must still accurately
  reflect the scroll ratio from start to end, and track click/wheel/drag
  behavior and auto-hide must remain unchanged. Never fake a center
  position: only cross-axis centering is automatic.
- Multiple viewports in one menu each own their own indicator. In
  Favorites++, COLLECTIONS and the main INDEX share the left bay but
  have distinct scroll ranges; the middle saved-item list gets a third
  bar. The bottom source-filter row stays pinned and is controlled by its
  original left/right arrows, rather than gaining a competing vertical bar.
- In LOCATION, the left Explore editor, middle pinned search results,
  middle saved places, and right Home editor keep independent scroll bounds.
  In particular, the saved-places track cannot run alongside the pinned
  FIND PLACE query above it.
- `widgets/CpuPlusW.qml` THERMAL/SYSTEM rail placement is a
  separate owner-controlled seam in Nurse 3r's open scrollbar PR
  [#252](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/252).
  Do not overwrite that worker's host edits without a handoff.

**Verification gates before changing the handle shape:**

1. Native QML: capped-bar property clamps to 42px without altering the
   default proportional length when unset; verify scroll positions at
   0%, 50%, 100% and keyboard/wheel/drag limits.
2. Host tests: long and short lists in Favorites++ and LOCATION; no
   indicator when scrolling is unnecessary; each bar inside its pane
   below pinned headings, not outside the menu or on top of text.
3. Runtime desktop: review normal, hovered and pressed colors, rail
   placement, resized CPU++ modes, multiple active lists, and scrolling
   at the bottom.
4. **Operator visual acceptance of rounded stage 1**, then a separate
   authorized stage-2 PR can change selected handles to `"star"`.
   Do not make that design decision on the operator's behalf.

**Relation to existing rules:** This adds an opt-in rounded handle cap and
CPU++ mounting recipe without changing the approved 23-rule NeonScrollBar
API, the box-side geometry defaults, Git/Hospital star convention,
deliberate extended rails, or the shared component's hit width.
