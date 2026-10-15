✦︎✦︎✦︎ Meta Apollo Logos //

# F4 // SELECTOR DIAL ↔ SLIDER PARITY AUDIT

> DATE // 2026-10-15
> AUTHORITY // Read-only architecture audit, not runtime migration approval
> SOURCE // `components/SelectorDial.qml` blob `f1fd52fe200dba8151e67d8c44fac9655fc65d0e`
> SOURCE // `components/SelectorSlider.qml` blob `78956baa67f9334b2a7711dc49518b50f1359ec4`
> BASE // current `main` inspected after F3 PR #282
> RUNTIME // F2 VALUE and F3 STEP standalone demos operator-accepted; this audit makes no claim that the Dial itself was retested today

## Operator-approved meaning

The operator explicitly prefers Git REPO, Git REMOTE and Hospital FLOOR's
original **immediate real-context updates** during dragging: branch maps,
names and floor data must change while they explore those indexes. A tiny
isolated numeric preview cannot replace that information.

F2 VALUE's continuously changing values looked and worked well.
F3 STEP's discrete detents were perceptible under very smooth movement:
operator praised the subtle stop per step rather than abrupt snapping.
**Preserve this exact perceptual balance; do not amplify detent jolt.**

## Semantic common ground

| Meaning | SelectorDial | SelectorSlider | Parity judgment |
| --- | --- | --- | --- |
| Owner authority | `currentIndex` or `currentValue` supplied by owner | Same, and `indexRequested` / `valueRequested` are requests | **Aligned**: don't fake external acknowledgment |
| Candidate vs committed | `previewIndex`, `pendingIndex`, `previewNumericValue` or visual angle | `previewIndex`, `pendingStepValue`, live VALUE position | **Aligned conceptually**, distinct mechanics |
| Numeric limits | `minimumValue`/`maximumValue`, clamping & precision | Same bounds plus validity guard; Step quantization | **Aligned intent**, not identical code |
| Keyboard/wheel | Arrows call `stepIndex`; rotary wheel steps | INDEX, VALUE, STEP each use mode-appropriate step | **Aligned purpose**, preserve individual mappings |
| Cancel/interruption | `stopMotion` clears pending animation/inertia; canceled rotary motion snaps to owner | INDEX/STEP cancel preview; VALUE does not roll back already-live requests | **Aligned contract**, mode-specific effects |
| Real operation status | Explicit loading/error/progress supplied by owner | Activity points supplied by owner; component does not infer work from motion | **Aligned: external truth is owner-driven** |
| Colors/focus/glow | Independently configured dial marker/labels and focus ring | Independently configured rail/handle/activity and focus border | **Aligned grammar**, do not force same shape or hue |

## Deliberate differences to preserve

### Geometry

Dial is circular: full rotary discrete mode and bounded `continuous`
or `zones` modes. Bounded defaults are a 300° active arc and a 60°
inactive gap centered at six o'clock. Slider is vertical/linear with a
physical pointer track, handle and ruler. `IndexRail` is separate and
remains outside this family migration.

### Commit timing

- **Slider INDEX legacy** (Git REPO/REMOTE): emits selection requests as
  the pointer crosses items, showing real context updates while dragging.
- **Slider INDEX preview-release** (opt-in): candidate position previews;
  owner-request follows pointer release. Hospital retains its unobtrusive
  LIVE FLOOR switch; Git test switches were removed by operator direction.
- **Slider VALUE** (opt-in): emits numeric value requests during movement.
- **Slider STEP** (opt-in): detent candidate during movement, commits owner
  value on release; wheel and arrows request one discrete step.
- **Dial discrete**: rotary motion may flick and settle; index request
  follows settling or explicit option/keyboard/wheel request animation.
- **Dial continuous/zones**: angular position is free within its bounded
  arc; a completed rotation/settle emits the resulting numeric value or
  zone selection. Do **not** silently convert Dial continuous mode to
  Slider VALUE's live-reporting default.

### Motion

The Dial uses intentional angular velocity, decaying inertia, bounded
angular motion and option angular equivalence. Slider STEP uses smooth
position-to-detent easing without angular inertia. The F3 runtime pass
means subtle discrete stopping is *desirable*, not insufficient feedback.

### Readout

Dial has center operation-state feedback and its own `readoutText` /
`selectedValue` presentation. Slider has fixed owner value and, for
preview modes, optional candidate presentation. Exact text placement is
application-specific; preserve independent committed/candidate meaning
rather than forcing identical labels onto circular and linear forms.

## Audit flags for future independent verification

1. Test Dial's numeric `valueRequested` on release and keyboard/wheel
   settling with a live owner before claiming exact parity; today only
   code behavior was inspected.
2. Verify cancellation, stale owner acknowledgments and mid-animation
   interception *per mode*, especially asynchronous owners. Static
   source checks do not prove runtime races impossible.
3. If two live consumers later need identical clamping or precision
   behavior, consider a minimal pure numeric helper. Avoid creating a
   new shared QML base class solely to achieve conceptual symmetry.
4. The project's F2/F3 future orientation/fill/readout variants are
   still separate feature decisions; do not infer their completion
   from these two successful isolated demonstrations.

## Verdict / authority

**F4 READ-ONLY AUDIT PASS.** Common selection meanings are consistent
enough for a shared family vocabulary. Geometry, motion, inertia and
commit timing remain intentionally distinct. **NO DIAL REFACTOR OR
SLIDER MIGRATION RECOMMENDED NOW.**

F5 RANGE stays deferred, including unresolved Decision 036.
This report itself makes no QML, Git, Hospital, IndexRail or Dial edits.
