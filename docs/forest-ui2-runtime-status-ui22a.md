# UI2.2a // Public Runtime status consumer

DEVELOPMENT ACTIVE / PRODUCTION HOLD. Based on merged #2596 R4b, actual exact f4cbacc1, owner proposal #7152659606 and Security acceptance conditions #7152824875. Independent final R4b review not returned at inspection.

## IMPLEMENTATION
UI2-owned pure JS consumer for exact six-field local unit and seven-field status packet. Explicit open requires separate matching current local correlation (two distinct lowercase 32-hex tokens, positive safe generation); incoming units never attach. Scope changes clear locally; stale other-view or uncorrelatable units ignored; malformed current unit or gap/duplicate/invalid transition closes that lifetime. Owner INVALIDATED clear scoped to exact correlation; withdrawal irreversible; no automatic retry/replay. Bounded local reuse fence for 1024 explicit attachments per consumer, no automatic recreation. Host must independently issue new tokens and track actual currentness. Fixed labels only, all authority/action flags false; no history or model side effects.

## VERIFY / HOW TO USE
node tests/forest/test_ui22a_runtime_status.js. Recorded actual merged R4b fixture callback units (real R3/B3 disposable fake model) replayed into JS for interoperability; not a live synchronous cross-language callback or actual UI host. Additional malformed/stale/withdrawal/terminal tests. CI pending. No QML hookup, real sender or protected data.

## WATCH OUT FOR
First normal status REQUEST_PENDING; early UNKNOWN_HOLD is allowed because R4 finish/error can occur before REQUESTED. WITHDRAW may be first unit. No IDLE publication. STOP_REQUESTED is not cancellation receipt; LOCAL_COMMIT_RECORDED is not delivery. Currentness supplied by owner is not authentication. Uncorrelatable inputs cannot clear a newer view, so owner must independently invalidate the affected lifetime after callback failure. No status-driven history fetch or new assistant row. This does not prove host integration, actual callback after-side-effect recovery, native inference, C5 authority or operator acceptance. R4b final independent review and actual callback placement still required.

## NEXT
DOC2F/DOC3F review token/state/currentness semantics, Nurse2F scoped review; next actual reactive QML status presentation and agreed synchronous disposable host/consumer integration. Preserve merged ForestW preview and separate M4 state. No shared source edit or production activation.
