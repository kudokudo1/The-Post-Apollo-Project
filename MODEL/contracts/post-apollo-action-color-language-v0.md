# Post-Apollo action-color language // operator direction v0

STATUS: Explicit operator design intent captured on 2026-11-03; **documentation only**. Not a live global theme change, pixel normalization, or authorization to edit other feature owners' UI. Begin color implementation only after required controls are present and operator agrees to the scope.

## Purpose

The operator navigates by **area plus action color**, rather than reading every button. Current Social Organization controls are visually too uniform (cyan borders/text, similar rectangles), making unrelated actions hard to distinguish. Keep current button sizes, spacing, geometry and general layout for now. Tiny pixel offset, textbox and font normalization across Post-Apollo is deferred to a separately reviewed future change.

## Semantic roles (intent, not hardcoded hex codes)

- **Red:** cancel, close, delete, destroy, remove or other explicitly negative/stop actions. Distinguish a cancel/close press from orange important-action emphasis.
- **Green:** refresh, reload, documentation, successful verification/healthy check.
- **Yellow:** save, archive, move, resize, or other record-management and transformation actions.
- **Orange:** important *primary action for the current field/area*, context-specific direct command.
- **Magenta / purple:** current user intent or focus: active typing, exact selected/activated control, focused operation. Strongest attention for the thing being directly manipulated, not every hover.
- **Blue / cyan:** navigation, ordinary secondary commands, low-stakes routing. Reserve cyan instead of applying it to all actions and text fields.
- **White / neutral:** routine information, less important labels and passive affordances.

Use existing ActionButton's idle/hover/pressed/selected fill, foreground, border, content glow, soft/wide halo, opacity and disabled-state options to reinforce *roles*. Keep text labels and accessible focus/contrast cues so color is not the only signal, including for users with color-vision differences.

## Interaction consequences

A direct click must give immediate visual acknowledgement and meaningful saving/busy/confirmed/failed feedback. Repeated clicks express genuine intent, but never bypass destructive-action confirmation, one-write-at-a-time locks, revision conflicts, permissions, or duplicate prevention. Show pressed/queued/working visibly; do not silently multiply mutations.

No global ActionButton, Colors, font, size, opacity or halo code is modified in the current Control 5 PR. First complete the button-function list; then review actual contexts and group by semantic role, seeking authorization for shared-system changes and coordinating other owners.

## Decisions / open questions

The above mapping comes directly from operator feedback and is the initial semantic specification. Specific hue values, gradients, glow intensity, fade timing, focus-ring behavior and exceptions will be decided in the future color-coordination implementation, after the remaining controls are usable. Preserve current small button geometry until a separate pixel-normalization assignment.
