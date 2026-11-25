# UI2.2b // Reactive Runtime status presentation seam

DEVELOPMENT ACTIVE / PRODUCTION HOLD. Nurse2F #7154099488 assignment. Reuses merged and independently reviewed UI2.2a, R4a/R4b. No duplicate consumer, runtime producer or renderer.

## IMPLEMENTATION / HOW TO USE
UI1 may instantiate PublicRuntimeStatusView in the existing conversation status area after exact seam agreement. Its implicitHeight is zero when no label, otherwise the wrapped fixed label height; give it the actual available width, preserve M4 history label and chat viewport. Set viewOpen from the real public preview lifetime, treeKey from exact presentation Tree, currentCorrelation from independently observed host-issued local correlation (replace entire plain object, never mutate in place). Null on detach/currentness loss. Wait initialized before explicit openLifetime(ref). No automatic open on visibility or currentness restoration. receiveUnit(unit) is synchronous, void, only for approved R4b local units. invalidateLifetime(ref) scopes owner INVALIDATED to that lifetime. closeLifetime is local presentation closure, not cancellation or revocation. These functions establish no authority. Do not bind currentCorrelation to a received status packet or expose raw host IDs. UI1 owns placement and actual geometry, DOC2F owns host currentness/callback, DOC3F reviews actual placement/provenance.

## VERIFY
New offscreen QtQuick tests use actual merged R4b disposable callback on same owner thread to actual QML item and independent existing M4 fixture history. No new transport. Test defaults, close/tree/detach, stale old status/withdrawal/open/invalidation, current sequence gap, callback failure after paint and owner clear, changed currentness before callback, 100 fragment suppression, wrapped label/collapse and history independence. 11 cases defined; CI pending. This is actual reactive QML, not installed ForestW geometry or physical operator acceptance. No real inference, private text or protected output. R4c historical reviewed merge #2610 has diverged ancestry from inspected main bf0306d2 and its test file returned 404 there; notify Runtime/Nurse rather than restoring their files or claiming it exists on current main.

## WATCH OUT FOR
Currentness is externally observed, not authentication; no asynchronous queue or retained mutable reference. Owner must re-resolve at delivery and clear affected correlation on INVALIDATED even after paint. Stale scope cannot open/clear a new lifetime. Existing JS consumer limits retained. Runtime state never refreshes or mutates M4 history. Long labels wrap, no arbitrary content. Actual compact ForestW geometry and local public host placement must be separately reviewed. SEND/STOP locked; production HOLD.

## NEXT
UI1 exact insertion and actual panel tests, DOC2F R5 fixture host using existing approved callback, DOC3F placement review, Nurse2F exact-head review and operator visual acceptance. No shared files modified.
