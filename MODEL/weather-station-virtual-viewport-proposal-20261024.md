# Weather Station / Stage Director // Virtual Viewport (P)

> **STATUS // P: STRONG PROPOSAL, NOT APPROVED IMPLEMENTATION.**
> **RECORDED //** 2026-10-24. **SOURCE //** Operator design discussion.
> **PATIENTS //** Post-Apollo-SwayPx (compositor relationship) and The-Post-Apollo-Project (Weather Station UI and renderer host).
> **OWNER / ACCEPTANCE //** Operator. **WORKER //** Replaceable. No live Hospital Room or Assignment is assumed.
> **MIRROR //** This proposal is intentionally retained in both repositories, not a universal Syntagma rule:
> [SwayPX proposal](https://github.com/kudokudo1/Post-Apollo-SwayPx/blob/master/MODEL/weather-station-virtual-viewport-proposal-20261024.md) |
> [Post-Apollo proposal](https://github.com/kudokudo1/The-Post-Apollo-Project/blob/main/MODEL/weather-station-virtual-viewport-proposal-20261024.md).
> Each link becomes a permanent default-branch reference only after its separate PR is merged. While reviewing drafts, use their PR branch versions.

## 1 // Intent

Make a small fixed Weather Station terminal window behave as a **viewport into a much larger, continuously updating scene**. Keep the actual Kitty terminal and AstroTerm application alive at a larger stable rendering size. Let the operator drag to pan, scroll to zoom, recenter, and optionally use buttons without expanding the Weather Station chassis or showing stray content around its edges.

The accepted current Weather terminal bay is approximately **824 x 494 logical pixels** inside a **1000 x 700** Station. Larger scene dimensions such as 1600 x 1000 are illustrative, not accepted defaults. Keep the panel footprint and the approved terminal bay unchanged in the initial experiment.

The same UI/navigation contract should later serve MAP (real geographical renderer and layers), star charts, satellite/radar maps, or other registered scene sources. A map does not have to be drawn using Kitty merely because AstroTerm is.

### Preferred option (P)

**Option 2 + shared viewport interface:** a real, larger Kitty surface remains rendered by Kitty, and a future Stage Director compositor capability clips, pans and scales it behind the Station's viewing region. Quickshell provides controls and state; SwayPX owns the actual scene clipping/transformation/input remapping. Preserve the current shader pipeline rather than recreate it.

**Retained alternatives, not silently discarded:**
- **Option 3A:** capture a live Kitty surface and composite the resulting texture into a clipped Quickshell scene. Kitty and its rendered shaders still exist, but capture/copy/synchronization/input forwarding may be costly.
- **Option 3B:** a native map/star renderer replaces the terminal for that specific viewer. Best for native semantic maps and feature-level zoom but does not directly reuse Kitty effects.
- Merely drawing opaque rectangles over an oversized Kitty is **not** accepted as a clipping mechanism: off-panel pixels and pointer interaction could still leak.

## 2 // Responsibilities and authority

| System | Existing role / planned ownership |
| --- | --- |
| **Kitty** | One genuine terminal process, larger stable character grid, AstroTerm lifecycle, terminal-compatible effects, real application input in INTERACT mode |
| **Stage Director / SwayPX** | Currently SD0 *shadow observer* only. A separately authorized future stage would own parent/child scene identity, clipping, camera transform, compositing order, visibility and coordinate-correct pointer delivery |
| **Quickshell Weather Station** | Owns the panel chassis, title/rail/footer, controls, viewport rectangle, selected domain, PAN/SELECT/INTERACT state, UI events and presentation toggles |
| **Viewer adapters** | Map/image/news/astronomy renderers maintain their own content, source health and semantic zoom; common camera gestures do not imply common rendering engines |

**No current authority transfer:** The Stage Director development branch **stage-director/scene-registry-v1** classifies weather-screen and observes compositor geometry; it explicitly does not mutate geometry, focus, lifecycle, clipping or input. Its Weather profile includes an old 780 x 416 reference and is not the new target. A future Stage Director assignment must be separately scoped and authorized. This proposal cannot activate SD1, merge code, or replace SwayFX on the live desktop.

**Known Post-Apollo seams to inspect later:**
- **widgets/weather/WeatherStationW.qml**: PanelWindow; output binding; visual chassis alpha hole and input Region subtraction.
- **widgets/weather/StationChassisCutout.qml**: four painted strips around a transparent opening. This currently clips the *panel artwork*, not the Kitty window.
- **widgets/weather/StationTerminal.qml**: Kitty launch, single weather-screen actor identity, observed fit, view state and Sway geometry.
- **widgets/weather/StationTerminalGeometry.js**: output/global geometry and workarea translation.
- **Post-Apollo-SwayPx/sway/stage_director.c** and **sway/stage_director_profile_weather_station.c** on the Stage Director development branch: observer baseline to verify against current branch/owner before doing compositor work.

## 3 // Viewport and interaction contract (proposed)

Represent the viewport as an authorized rectangle in compositor-global logical coordinates, separate from Kitty's full source bounds and separate from a **camera** with offset and zoom. No automatic Kitty OS-window resize during pan or zoom. One initial scene-size selection/resize may be needed; verify AstroTerm behavior first.

- **PAN:** left-button drag moves the camera over the larger source; wheel zooms about the current pointer; dragging/scrolling must not be injected as terminal keystrokes.
- **SELECT:** use the established Shift-as-Select convention for selection where a scene supports hit testing; otherwise report unavailable rather than pretending semantic selection exists.
- **INTERACT:** explicitly route keyboard and relevant pointer actions to the real Kitty application with correct translated coordinates, while preserving escape/release and cross-widget focus ownership.
- **Controls remain:** zoom plus/minus, recenter, 100% reset, interaction mode, and optional scale readout. Buttons supplement, not replace, gestures.
- **Navigation safety:** clamp camera boundaries, preserve position/zoom when switching modes as appropriate, restore known-good framing, allow keyboard escape from capture, and do not use an unbounded resize or redraw loop.
- **Rendering isolation:** outside the authorized viewport the full Kitty scene is not displayed and cannot receive unintended pointer input. The overlay alpha hole and input routing must agree with what the compositor paints.
- **Display behavior:** derive positions from live output and layer-shell workarea geometry. Cover differing output origins, fractional scale, output hotplug, DPI changes, desktop gaps and panel open/close transitions; do not hardcode a primary display identifier.

**Zoom has two meanings:** compositor/image zoom magnifies existing Kitty characters and pixels; it does *not* add astronomical stars or geographic information. Semantic zoom requires the underlying AstroTerm/astronomy or map renderer to recalculate or load additional details. Keep the two capabilities explicit.

## 4 // Shader / CRT preservation

The operator has an existing Kitty Metapollo/TV-style CRT and signal-effects pipeline and wants to preserve it. **The actual local shader files, Kitty build/flags and enable/disable interface have not been inspected for this proposal.** Names and behavior must be verified from the running machine before wiring presets.

For Option 2, Kitty performs its usual terminal rendering and shader passes; the compositor then presents a transformed and clipped portion of the resulting real surface. This is the preferred path for reusing scanlines, phosphor, bloom, interference, tearing/static and other pre-existing Kitty presentation effects **without rebuilding the stack**.

Potential visual difference: if Kitty's CRT curvature, scanline pitch or vignette is defined across the *whole larger source*, zooming or cropping also zooms/crops those effects. If the operator later wants viewport-local glass/border effects or constant-pixel scanlines, treat that as a small additional compositor/Quickshell pass, **not** a mandatory reimplementation of the original Kitty shader stack.

Proposed user settings: **CLEAN**, **CRT**, **SIGNAL**, each with a clear OFF/fallback and no forced re-launch. Actual live toggling is conditional on verifying existing Kitty/shader capabilities and performance.

## 5 // Prototype gates and recovery plan

| Gate | Bounded experiment | Acceptance evidence |
| --- | --- | --- |
| **V0: inventory** | Inspect current compositor branch, scene ownership, the local Weather Kitty wrapper and actual shader pipeline; reproduce AstroTerm input/redraw corruption | Known failing keystroke/repaint case, versioned source and isolated reproduction; no live mutation without local approval |
| **V1: isolated clip** | One real Kitty actor at a stable larger size; compositor clips it to an unchanged viewport; no controls yet | Zero visible bleed outside Station and zero stray pointer targets; correct stacking, alpha, secondary monitor and close/reopen |
| **V2: pan** | Pointer drag updates camera offset only, without resizing/relaunching the terminal | Smooth live animation; one terminal actor; correct frame rate and bounded CPU/GPU use; no repaint corruption |
| **V3: wheel zoom + input** | Pointer-centered zoom, bounds, reset and PAN/SELECT/INTERACT input-coordinate translation | Accurate hit testing/focus at each scale; keyboard exit and no unexpected clicks |
| **V4: shaders** | Preserve Kitty CRT pipeline and optional disable/enable control | Clean versus CRT versus signal display comparisons and performance evidence; no duplication of passes unless operator chooses |
| **V5: reusable viewers** | Same viewport control grammar for actual interactive MAP renderer and other scene sources | Native map pan/zoom data behavior, truthful provider detail levels and state preservation; no forced terminal rendering for maps |

All gates need tests and a live operator visual/reliability check; CI/source review is not runtime acceptance. Feature-gate compositor mutations, retain the original panel and Kitty geometry as rollback, and preserve SD0's observer-only mode as safe fallback.

**Abort / revert on:** input deadlock, focus theft, unbounded render/capture loops, black/invalid surfaces, visible bleed, display-loss behavior, compositor crash, or sustained performance degradation. A broken viewport must not prevent ordinary Weather Station operation.

## 6 // Open decisions (do not silently decide)

- Exact full Kitty source dimensions and their relationship to character-cell geometry; AstroTerm redraw behavior after initial resize.
- Whether zoom is allowed while in INTERACT mode, or restricted to PAN.
- Mouse gesture overlap with program input, focus capture and escape rules.
- Whether shaders run fully before or partly after viewport transform; which existing passes can toggle live.
- State persistence, cursor/selection hit testing and snap/overscroll behavior.
- The new compositor IPC/API contract and SwayPX/Quickshell ownership handshake.
- Which scene sources need real semantic zoom, versus pixel zoom only.
- Stage Director implementation assignment/owner and deployment authority.

## 7 // Hospital-compatible handoff

### IMPLEMENTATION
Documentation-only strong proposal duplicated in the two owning repositories. No compositor clip, Quickshell controls, Kitty changes, runtime reload or service changes are implemented by this record.

### HOW TO USE
Start with this proposal and the owning repository's MODEL index; inspect current main/master, active Stage Director branch and open assignments before selecting a bounded proof-of-concept gate. Work from the existing Weather Station and Stage Director interfaces.

### VERIFY
Evidence at drafting: source showed an 824 x 494 Weather terminal bay with Quickshell transparency/input subtraction and an external Kitty window; Stage Director SD0 had observational scene modeling but no composition or input authority. The operator reported AstroTerm redraw trouble during terminal input. Current binary behavior, custom Kitty shader source and actual compositor clipping behavior remain unverified.

### WATCH OUT FOR
Clipping the panel image is not clipping external Kitty. Do not fake a clip with window overlap. Avoid duplicate terminals, input leakage, rasterized-only zoom presented as additional map/star data, second rendering pipelines and unilateral Stage Director authority expansion. Preserve active ownership and other workers.

### CHECKLIST
- [x] Record operator intent, preferred architecture and retained alternatives
- [x] Separate compositor, Quickshell, Kitty and viewer ownership
- [x] Define gestures, shader preservation, tests, risks and rollback
- [ ] Operator approves an implementation milestone
- [ ] Scope/owner and live baseline independently verified
- [ ] V0-V5 individually tested, accepted and recorded when built

### NEXT
Operator may authorize **V0 + V1** as a bounded prototype after owner/preflight checks, prioritizing a real oversized Kitty under a true clip with safe rollback. Do not jump directly to a giant shared renderer implementation.

### DECISIONS
**P = strong proposal only.** Preferred Option 2 compositor-clipped genuine Kitty + reusable viewport contract, mouse gestures first-class, optional buttons, existing CRT effects preserved as far as technically viable. Final implementation/architecture acceptance remains with the operator.
