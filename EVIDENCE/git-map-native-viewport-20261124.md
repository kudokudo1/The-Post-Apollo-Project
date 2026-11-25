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
