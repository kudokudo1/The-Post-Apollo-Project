# UI2.2c // Mounted public Runtime status region

DEVELOPMENT ACTIVE / PRODUCTION HOLD.

## IMPLEMENTATION
UI1 #7155881685 explicitly accepted UI2 ownership of PublicConversationFixture; UI1 owns ForestW host/geometry. Reuse merged/reviewed PublicRuntimeStatusView (#2624) below existing history status; shared transcript anchors below it. The literal sample history remains literal, not R5 history. Inactive operation label collapses to zero. No new renderer or controller.

## HOW TO USE
Owner-only public fixture seam on the existing Loader item: set runtimeTreeKey exact CHERRY, runtimeViewOpen from independently eligible current lifetime, runtimeCurrentCorrelation whole fresh owner-issued ref (null on loss); wait runtimeInitialized and runtimeEligible, explicitly openRuntimeLifetime(ref), then synchronous void receiveRuntimeUnit(unit); on INVALIDATED use invalidateRuntimeLifetime(originalRef). runtimeState/runtimeStatusText readonly. Never infer current correlation from incoming unit. Current lifecycle closes via viewOpen/currentCorrelation/Tree/visibility/Loader loss; no delayed unscoped close API. New tokens required across Loader destruction; owner must independently observe actual currentness and provenance, never rely on UI flags. No automatic open or history fetch. Runtime status is distinct from fixed preview history and not delivery or cancellation acknowledgement.

## VERIFY
Extend actual native composed preview test to nine ordered phases, keep original transcript, disabled composer, focus and geometry checks; explicit test-only public status units, long wrapped label in 300x160, stale prior withdrawal/invalidation/open, Tree loss, unload/reload, default-off/no auto-open. Stage exact new dependency bytes in existing native workflow. CI pending. Actual R5 producer to reactive component already tested separately (#2630, 4 R5+11 UI2 tests); this is not a new host, does not claim a real R5 callback into mounted ForestW or live two-turn panel. No actual installed transport.

## WATCH OUT FOR
ForestW host unchanged; UI1 owns full actual panel verification. Runtime host placement and cross-process design require DOC2F/DOC3F agreement; no new socket, model, private journal or protected authority. Existing Workshop matcher failure separate UI1. #2630 independent final review pending. No SEND/STOP activation.

## NEXT
UI1 review exact fixture and run actual ForestW native full/compact geometry/lifecycle with approved dependency; DOC2F use reviewed seam from disposable owner host only; DOC3F review exact callback placement/currentness, Nurse2F independent review, operator acceptance. Preserve memory/resource HOLD.
