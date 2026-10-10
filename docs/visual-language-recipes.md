# Post-Apollo visual-language recipes (first additive pass)

This is the approved semantic contract for the first visual-effect components.
It is not a directive to replace all QML shadows or normalize every widget.

| Component | Responsibility | Canonical starting point |
| --- | --- | --- |
| `HaloGlow` | Unopinionated rectangular shadow renderer | Caller defines role and stacking |
| `ModeButtonCloseHalo` | Ordinary mode-button rear perimeter | AppControl: spread 3, active opacity .50, z -1 |
| `ModeButtonWideHalo` | Mode-button **front** wash | AppControl: spread 10, active opacity .09, z +1 |
| `ActionButtonHalo` | Ordinary action-button rear perimeter | Shared ActionButton's state colors/opacities |
| `ChassisGlow` | Window/menu chassis exterior | **Git**: spread 6/.21 and 12/.05 |
| `TextHashGlow` | Sampled text/icon halo, teardown-safe | radius 10, samples 9, opacity .84 |
| `QuietText` | Low-priority supporting/diagnostic text | white at opacity .42, no default glow |
| `SecondaryText` | Supporting readable text | white at opacity .68, no default glow |
| `VisualLanguage` | Shared approved numerical defaults | All above |

## Non-negotiable distinctions

- **Magenta foreground text or icon always glows magenta.** Halo, border,
  chassis, and fill colors are independent; an orange perimeter stays orange.
- **ModeButtonWideHalo belongs in front** of the mode-button face; close halo
  belongs behind. Keep them as *two direct children* of the button. Placing
  both inside one nested Item changes their stacking relationship.
- **Git's chassis numbers are the default.** This does not mandate Git's
  action hover behavior, which must ultimately follow AppControl.
- **AppControl is the model for mode icon/name hierarchy.** The icon carries
  strong state color and glow; the supporting name can stay dim white.
- The **CPU++ 90 ms scale response** is an acceptable optional behavior.
- **Text importance and control availability are separate axes.** QuietText
  is not a synonym for disabled. Existing ActionButton layered availability
  controls remain authoritative until intentionally consolidated.
- Red can represent error, criticality, danger, destructive action, extreme
  telemetry, complex/risky graph topology, and established brand identities.
  Do not reclassify existing red graphs as errors merely because they are red.
- The dark, busy desktop is a valid intended environment. Do not force
  opaque rectangles behind every quiet label; record light-background
  dependencies rather than treating every failure as a design defect.
- `SafeDropShadow` protects sampled-source lifetimes. Use it for new
  source-attached text/icon effects. Do not replace it with unguarded
  `layer.effect: DropShadow` during cleanup.

## Consumer contract

Use `ModeButtonCloseHalo` and `ModeButtonWideHalo` directly inside each
mode-button Rectangle. They inherit that Rectangle's size automatically via
`anchors.fill: parent`. Supply `selected`, `hovered`, `pressed`, and
`keyboardSelected` from the existing widget; do not let a glow own input
or navigation logic.

Use `TextHashGlow` next to the exact text/icon item and supply
`safeSource` plus `foregroundColor: source.color`. It automatically
resolves white to cyan, yellow to orange, green to Omnitrix, and
magenta **always** to magenta. Other pairings may be configured unless
the foreground is magenta.

Use `ChassisGlow` behind an actual frame geometry. It does not supply
window policy, panel opacity, keyboard focus, borders, or content layout.
Existing `WindowPanelFrame` can later adopt these tokens through a
dedicated, tested migration. Its current per-widget overrides are untouched.

Use `QuietText` and `SecondaryText` only when those semantic roles
are appropriate. Do not convert a product/app identity or consequential
action description to QuietText simply because it was gray before.

## Controlled rollout

1. Add these components, templates, and static contracts without changing
   any existing widget or shared component implementation.
2. After reviewing runtime examples, pilot selected **mode-button** halo
   instances and compare renderings/screenshots before broader rollout.
3. Reconcile Git's **ordinary action** behaviors separately from its
   loading/progress and keyboard-selection features.
4. Later audit other compatible effect/quiet-text variants, retain
   specialized recipes, and delete redundant ones only after parity checks.

Do not automatically homogenize graph rendering, branded icons, special
state treatments, notification backing surfaces, or error salience.

## CPU++ main-mode pilot (review before wider adoption)

The pilot changes **only** the four (data-driven) CPU++ main mode buttons in
`widgets/CpuPlusW.qml`:

- The two local mode halos become `ModeButtonCloseHalo` and
  `ModeButtonWideHalo`, following AppControl's close-behind/wide-front rule.
- The Gohu icon uses `TextHashGlow` with AppControl's idle/hover/selected
  radius, samples and intensity. The specialized thermal icon keeps its
  distinct four-glyph construction but now glows magenta when selected.
- The small mode name uses `QuietText` and AppControl's subdued white
  priority (0.34 idle, 0.48 active, 0.42 pressed). Its faint white glow is
  configured independently.
- CPU++'s original **90ms scaling**, hover/selection/press fill and border,
  blinking faces, click callbacks and mode switching are unchanged.
- **All other CPU++ controls, shared instrument bodies and chassis remain
  untouched.** The chassis still uses its prior stronger glow until its own
  separately approved rollout.

Expected visible difference: a more prominent selected icon, much quieter
mode name, subtle front-facing wash, and no idle mode-box perimeter glow.
Screenshots are required before treating this pilot as visually approved.
