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

## Green-family semantic recipes (operator decision 003)

**Green is a two-token family, not three separate hex colors.**

- **Omnitrix** is `Colors.omnitrix` (`#00F782`), the brighter primary green.
- **Sub-Omnitrix** is `Colors.green` (`#9ECE6A`), the original palette
  green and quieter alternate. It helps prevent too many competing strong
  green elements in a dense area.
- Pairings and layered glows are **rendering treatments**, not newly
  invented palette tokens. The relationship is analogous to yellow/orange
  and dark/black: related colors with distinct responsibilities.

The operator established these **three semantic recipes**:

| Identity / role | Base / foreground identity | Glow identity | Intended use |
| --- | --- | --- | --- |
| **Audio / systems** | Omnitrix (`Colors.omnitrix`) | Omnitrix (`Colors.omnitrix`) | Microphones, audio, mute/volume, sound, hardware, system and screen/window controls where the role fits |
| **AI / automation** | Sub-Omnitrix (`Colors.green`) | Sub-Omnitrix (`Colors.green`) | AI and automated operations; relevant Git automation controls |
| **Yes / confirmation** | Sub-Omnitrix (`Colors.green`) | Omnitrix (`Colors.omnitrix`) | Explicit affirmative and confirmation controls: related to the other greens, but more energized and visually distinct |

**Composition and interaction are separate axes.** These pairings describe
the control's green-family identity, not mandatory colors for every border,
fill, pressed face, selection ring, or adjacent decoration.

- A specialized green control can **retain its chosen green-family
  foreground/border/glow through hover or selection** while using a
  **yellow selection fill**. A selected control does not automatically
  need an orange glow; orange/magenta generic state transitions are defaults,
  not compulsory replacements for specialized identity.
- Contrasting magenta borders/glows and other purposeful multicolor
  effects remain permitted. Pressed states may have their own treatment.
  Respect intentional front/rear halo stacking, transparent positioning
  geometry, and multiple layered glows.
- Sub-Omnitrix may be used with a weak self-colored glow or without a strong
  Omnitrix halo where visual density requires restraint.
- `TextHashGlow`'s existing **green foreground -> Omnitrix glow** pairing
  remains a useful *default* (especially for confirmation). To express an
  AI/automation **green -> green** text glow, the consumer must explicitly
  request `preferredGlowColor: Colors.green`; do not globally change the
  default or erase the component's separate magenta-foreground invariant.

**Rollout / scope boundaries:**

- This section establishes **target semantic vocabulary**, not a bulk
  recoloring order or a claim that current widgets already conform.
- Preserve existing audio/systems/screen controls while documenting and
  reviewing exceptions; the operator chose Omnitrix/Omnitrix in part to
  avoid unnecessarily rebuilding that established family.
- **Git is not synonymous with AI.** Existing green Git accents also express
  staging, constructive actions, healthy state, and ordinary color variety.
  Classify the actual action before assigning a recipe; do not interpret
  every green Git occurrence as AI or every green confirmation as automation.
- Existing mixed-green AppControl mute appearances, green specialty sliders,
  and intentional magenta contrast should not be auto-recolored just because
  they differ from the default recipe. Keep source evidence and seek operator
  acceptance before changing those treatments.
- **Third-party / outside-theme greens**, including the existing Oasis
  Neovim palette, remain untouched until the operator explicitly chooses
  to unify them.
- No new QML component or palette hex is mandated by these rules. Runtime
  verification and owner coordination are required for future migrations.

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

## Dock / module grammar — approved 2026-10-11

Dock-only recipe; **not** the main-mode, action-button, or window-chassis recipe.
Git is the overall construction/stacking reference, AppLauncher the ordinary
interaction-color reference, and Wi-Fi the preferred outer **numerical**
reference. Normal dock idle color is cyan (`Colors.cyan`, `#55CFCA`), NOT
palette blue. Default glow identity: cyan idle, orange hover, magenta
pressed/open. Open overrides pressed/hover; yellow open fill remains.
**Operator reaffirmation, 2026-10-11:** This open-magenta priority is
**intentional for specialized modules too**, including Git, Hospital, and
Sessions. The shared `DockButton.openGlowColor` wins over their distinctive
idle/hover/pressed identities while the control is open; do not classify that
as a regression or remove it during color normalization.

| State | Rear halo (spread 3, z -1) | Front wash (spread 10, z +1) | Content opacity |
| --- | ---: | ---: | ---: |
| Idle | 0.40 | 0.07 | 0.75 |
| Hover | 0.50 | 0.09 | 0.95 |
| Pressed | 0.60 | 0.12 | 1.00 |
| Open | 0.86 | 0.22 | 1.00 |

**Content sample geometry:** radius 14 / 15 samples in all states as a
*provisional*, deliberately undersampled/hash-like starting point. The
operator must see the real Qt renderer before choosing final sample values;
do not smooth the effect automatically. Content glows build in opacity with
interaction. Wi-Fi's current anomalous inverted icon opacity (1/.8/.6)
is **not** the model and Wi-Fi itself remains untouched pending explicit
runtime review.

**Source/cluster ownership:** attach one independent glow to each meaningful
artwork/label/readout cluster, not a single effect over unrelated module
contents. Wi-Fi independently glows icon, SSID, signal percentage, and speed;
Clock and Volume have independent source-attached effects. One coherent
compound mark can remain one cluster. New source-attached effects should
use `SafeDropShadow`; separate them from the chassis rear/front effects.
Isolated sources may reduce glyph effect-stacking issues, but this is not
yet a verified Qt bug workaround.

**Structural white with contextual glow:** %, :, ornamental slash/separator,
stars, heartbeats and parentheses stay `Colors.white` in foreground while
the glow follows their *surrounding cluster* color unless deliberately
overridden. Decorative display separators ordinarily prefer `//` instead
of `/`; do not mechanically replace functional single slashes in paths,
URLs, code, math or meaningful separators. Mixed-glyph elements needing
separate foreground colors require a careful source/layout split and visual
verification; existing remaining widgets may not fully conform yet.

**Special identities preserved:** Git keeps yellow perimeter/orange artwork,
Hospital magenta, Social Omnitrix green, Weather orange; Clock, Volume and
Network retain their telemetry/mode-dependent colors. How the specialty
colors evolve on hover/pressed remains an operator decision, not license to
invent a generic change. Power retains its historically distinct first
Quickshell implementation and numbers; Workspaces and Tray remain composite
families; Calendar is the intentionally rounded dock and planned central
convenience bay. MediaPlayer stays dormant/unmounted. No new open behavior,
menu wiring, or live reload is implied by this source-level normalization.


### Nurse 3A targeted follow-through (2026-10-11; source review)

- Tray retains its multi-item construction and item activation while its front
  wash and sampled icon opacity use the shared dock numbers. Its icon glow now
  uses `SafeDropShadow`, without collapsing its per-item source attachment.
- Workspaces retains the independently colored, dual-layer active workspace
  glow and per-workspace controls. Only compatible exterior/front and text
  glow opacity values align to the shared numeric recipe.
- Volume's numeric readout and white structural `%` are separately sampled,
  with the percent's glow retaining the volume-level color. Launcher,
  Notifications, Calendar, Bluetooth and Git keep their complete compound
  marks while structural stars/parentheses remain white through open state.
- Wi-Fi's inverted icon opacity, Power's historical parameters, media-dock
  mounting, and unreviewed control-family widgets remain out of scope.
- These source changes require operator review of actual Qt font shaping,
  adjacent fragment spacing, glyph glow intensity and sampled-source lifetime
  before being considered visually accepted.
