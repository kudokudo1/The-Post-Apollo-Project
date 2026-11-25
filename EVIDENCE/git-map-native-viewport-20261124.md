# DOC 3 // G2a native virtual viewport candidate

## Scope
G1 PR #2566 exact head 26e6cb263807be5f631f0baf2db81c951abf6c30
passed all three PR workflows. G1 remains open; G2a is a stacked draft
against its branch, not a live merge or deployment. No GitW, BranchMap,
journal, recovery or CPU++ control changes.

## Implementation
- GitMapPageBridge: explicit manifest/directory activation, one external
  read-only page subprocess at a time, visible-first queue, event-turn
  coalescing, exact snapshot/repository/epoch/sequence validation via G1.
  Five-second helper timeout plus one-second termination allowance;
  eight-second terminal-evidence watchdog faults the bridge and refuses
  reuse on missing terminal signals. Stale in-flight reads may finish
  before the new destination is served, but do not publish old data.
- GitMapVirtualViewport: fixed logical scroll extent, Flickable.StopAtBounds,
  existing NeonScrollBar, fixed row height, viewport-sized Canvas, bounded
  row pool (visible height plus one). Data arrival cannot assign contentY.
  Row taps are checked against press-time ordinal/SHA/snapshot/epoch.
  Missing and failed data retain their position and expose retry; footer
  distinguishes loading/failure/end. Frontier-based lane segments are
  reconstructed per page, not by loading all preceding commits.
- Disposable actual Quickshell offscreen test using a 100,000-row index,
  delayed initial page, injected bottom-page failure/retry, exact final
  SHA selection, and repository switch during outstanding page work.
  Includes binding-loop/runtime-error detection.

## Unverified
CI pending. Fixture uses programmatic scroll jumps, not physical wheel,
touchpad or star drag events. Native frame timing, graphics memory,
complex merge graph appearance, clipped wide graphs, close/reopen and
new-snapshot anchor adoption need further tests. Initial reader is one
child at a time, not cancel-and-replace; a stale slow request can delay a
new viewport for up to the helper deadline. No active-index lifecycle,
persistent cache retention or automatic index generation. Live rendering
and operator acceptance remain HOLD. Existing map is unchanged.

## Next
Verify exact-head CI, fix fixture/renderer issues, add native gesture and
cross-page complex graph tests; then G3 explicit persistent index owner
and GitW integration with old map fallback. No data migration or live
machine mutation.

## G2b follow-up

Exact G2a head 952e9f0c0d486ad5424ea260a35fc6b1d403aaa9:
3/4 workflows passed; native workflow 45515916574 failed before instantiation
because Qt QML rejected JavaScript object spread in the G1 policy (Node
accepted it). Replaced spread with explicit Object.assign and property
assignment in the stacked candidate. The G1 PR remains at its prior head;
this compatibility correction is part of G2, and must not be omitted when
reconciling the stack. Added a contract for no-op state updates, reader
terminal wakeup and explicit unavailable rows after reader fault.

Expanded native fixture requires actual outstanding old-repository page,
checks merge frontier/parent identity across a page boundary, hides and
shows the candidate item without changing its scroll position, and runs a
separate Xvfb/xdotool input exercise (star drag to bottom, wheel at bottom,
reverse wheel, drag to top, wheel at top). The workflow reruns the G1
contracts as well as offscreen and X11 fixture variants. This is synthetic
input in disposable X11, not native Wayland touchpad acceptance; pixel-level
wide graph rendering, frame timing, production integration, and generation
anchor adoption remain unverified. New-head CI pending. No live changes.
