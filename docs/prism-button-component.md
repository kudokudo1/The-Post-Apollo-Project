# Prism // Contextual visual-language button (V1)

**Status:** operator-designed geometry; source implementation proposed. Native QuickShell visual, lifecycle and performance acceptance outstanding.

Prism is a reusable contextual visual-language dictionary trigger, not the ordinary Information button. Information explains what a feature does; Prism explains the meaning of its current colors, placements, states, gradients, glow, opacity, relationships and surrounding context. The future dictionary/popup and its semantic data are caller-owned and not implemented here. Spectrum remains a separate proposed global reference, not a synonym for Prism.

## Use

Import the shared components as the owning widget already does. Example:

```qml
PrismButton {
    width: 44
    height: 44
    selected: prismPopup.visible
    onLeftClicked: prismPopup.visible = !prismPopup.visible
}
```

The caller owns the real popup and selection binding. The button inherits ActionButton's pointer, availability and content keyboard navigation contract. Do not install a second mouse area or independently toggle selected. The accessible name is Prism. Default 44x44 is a provisional compact size; allocate a square face wherever possible. Outer halo is outside the layout bounds (roughly 9% of the smaller dimension), so allow clearance and avoid clipping ancestors. Rectangular allocations center the artwork.

## Operator decisions: recoverable artwork geometry

Screen angles: 0 is right, positive down. Use normalized icon coordinates, not a generated bitmap or a font glyph.

- Triangle vertices (43,14), (68,65), (18,65). Crisp Post-Apollo white outline, 1.5 units; opaque dark foundation with dominant white wash, 48% to 12% over its height.
- White enters at +25 degrees from x=2 to junction (42,40). All outgoing paths are straight with constant 2.5-unit core width, 90% opacity, vertical cuts at x=87. White begins with a vertical cut too.
- Outgoing beam order from top to bottom: magenta -20 degrees, cyan -2.5 degrees, orange +35 degrees. Orange is nearest the white continuation. Cyan and magenta form the closer pair. These are intentional artistic angles, not a physical ray-tracing claim.
- Entrance core is cut parallel to the left prism face; clearance is mirrored at +/-1.33 units measured perpendicular to that face, increased to +/-2.13 at face sizes <=32 logical px. Halo continues across the cut and through the solid-looking prism.
- The white beam draws over the colored beam roots. The close cyan/magenta pair blends shared coverage rather than stacking jagged colored pixels. The conversion nucleus masks intersections without broadening the beams.
- Nucleus radius 5.8 units; relatively solid inside, short soft edge. Rear/left stays white; outgoing/right changes into magenta at top, cyan near center, orange at bottom. A short horizontal blend connects them. Do NOT replace this with an all-white ball, a diffuse muddy cloud, an opaque hard line, a larger general blur, or the raster concept image that flipped the beams.
- Color values bind to the existing Colors singleton, not a second independent palette. Preserve source semantic colors; do not change the singleton.
- Closed square white border stays independent of its spectrum; the actual open state uses the standard magenta border. Outside glow only: orange at bottom-left, cyan at both top-left and bottom-right, magenta top-right. Orange -> yellow -> green -> cyan -> blue -> purple -> magenta. Stop positions 0/.17 orange, .23 yellow, .28 green, .36/.63 cyan, .69 blue, .76 purple, .83/1 magenta. No red in this transition.
- Button interior is illuminated by the artwork, not by the border. Beams dominate the light; the triangle has a noticeable but weaker external halo. Its interior remains dominated by white material wash. Incoming white must stay fully luminous through the prism until it becomes colored at the node.

## Implementation choices and verification

PrismArtwork.js computes continuous Gaussian-like glow falloff and antialiased core coverage on one bounded Canvas image. This avoids the stepped preview stroke bands and the detached sampled-source lifetime issue. Canvas is centered and oversampled up to 2x logical resolution, bounded at 256x256. No timer, process, shader-source sampling, or background service. Repaint on size, visibility, palette or explicit spectralGlowStrength change; no continuous animation or hover/press/selection repaint. The single native border is fixed at 1 logical pixel in every state and remains below both artwork layers. No duplicate overlay border or increased border thickness is permitted. The approved Prism artwork is cached once; a second cached glow-only render reuses its exact spectral exterior/beam/triangle bloom, with a small tint across the border itself. While closed, hover, press and keyboard focus increase this glow layer's opacity without rerasterizing on every pointer transition. When the actual popup/widget is open (selected), the ordinary module rule takes priority: yellow fill, magenta outline, prism artwork and glow. The same analytic geometry is cached in a magenta-on-yellow palette on first open, retained for reopening; closing restores the original closed spectral artwork. The widget structure continues to use the closed border identity, not the button's temporary open color. Disabled follows ActionButton availability opacity. The operator will judge final glow strengths and border appearance on the actual display.

Run `node --test tests/components/test_prism_artwork.cjs` for deterministic source/geometry/pixel checks. It uses a mock Canvas context, not Qt. Native verification must inspect rendering at 24/32/44/64/96px, mirrored gap and square cuts, no colored slivers in the node, white interior continuity, white border and independent glow, resize and destruction, availability and one-click activation, and measure creation/paint cost on the actual QuickShell host. The exact native glow strength and state styling remain subject to operator acceptance. No existing widget or information control is replaced in V1.

Shared semantic authority: [Syntagma icon grammar](https://github.com/kudokudo1/Meta-Apollo-Logos-Syntagma/blob/main/OPERATE/POST-APOLLO-ICON-GRAMMAR.md); this file records the technical implementation recipe, not a universal rollout authorization.

## Prism widget header and placement index

The full Post Apollo `PrismW` keeps its TASKS portrait proportions and
Trash-derived height ceiling. The owning shell wires
`PrismW.prismBorderColor` to `PrismDock.prismBorderColor`, which reads
the actual `PrismButton.idleBorderColor`. Thus the 1px outer panel border,
header title, divider, index-card borders and source label use one border
identity, not copied color values. This does **not** replace the Prism
button's multicolored ray/glow artwork with a monochrome image.

The header follows the operator's exact one-row right-to-left order:
close, reload, compact `COLOR // SYNTAGMA` badge, diagnostics, resize up,
resize down. The title uses the remaining width. At all three chassis
sizes Prism grows upward from Trash's shared bottom edge (85px above the
screen), rather than hanging from the top of the screen. The shared
`PrismBorderGlow` component reads the same spectral stops and corner
orientation as the original button, retains thin underlying border cores,
and supplies the window, internal divider, index-card and source badge
perimeter glows. Ordinary action and feature buttons retain their complete
shared component styling, including normal glow planes, unless the operator
explicitly requests an exception. The source badge has a fixed white 1px
border and spectral halo. `PrismTextGlow` adds glyph-shaped spectral halos
behind the unchanged foreground text of the title and source badge. The badge is not a
heartbeat. Reload is unavailable until it has actual data to refresh.

The diagnostic toggle owns `PrismW.indexOpen`; it switches the existing
body between the honest empty dictionary and a placement dossier. The index
renders `services/prism/PrismIndex.js`, a small source-backed registry of
**verified Prism entry points**. Initially it includes only the Post Apollo
bottom dock, with zero authored definitions. For later installations, update
the registry **in the same integration PR** as the new `PrismButton` mount
and reference a real module source path. The registry is not a background
scanner, service-health authority, or permission boundary. Do not add
uninstalled widgets or invented semantic definitions.

Validation: `node --test tests/components/test_prism_artwork.cjs
tests/components/test_prism_dock.cjs tests/components/test_prism_index.cjs`.
Native/operator visual review still determines final header spacing and
border/glow appearance.
