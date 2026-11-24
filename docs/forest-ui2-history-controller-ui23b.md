# Forest UI2.3b // Public history view controller

DEVELOPMENT ACTIVE / PRODUCTION HOLD. UI2-owned presentation only. Builds on merged #2534 (25/25 raw, five PR workflows pass; independent review not recorded at inspection) and Mind M4 #2530 / handoff #7144442968.

## IMPLEMENTATION
createController() in existing PublicHistoryDisplay.js owns one local disposable view's bounded in-memory snapshot and pending page. Explicit open starts at ordinal zero; explicit next uses last retained ordinal, a fresh request ID and unchanged scope. receive validates using existing M4 page adapter, rejects duplicate turn IDs across pages and clears the whole snapshot on refusal/stale page. observe(currentScope) clears when Tree/session/revision/generation/local view key changes; close/reject clear immediately. Returned copies cannot change internal state. No request is issued by this module, no automatic replay or fetch; request object is a proposal for a future approved host adapter. All authority fields remain false.

## HOW TO USE
Source tests only: node tests/forest/test_ui23b_history_controller.js. Actual two-page M4 producer test uses the existing in-memory fixture. No live QML hookup, DB opener, model call, new transport or external records.

## WATCH OUT FOR
UI must call observe on current presentation-context change and close on detach; this pure controller cannot observe a native host by itself. viewKey is a local correlation only, not recipient identity or permission evidence. Retained limits are provisional 256 messages / 512 KiB sum of compact display-row JSON UTF-8 sizes (not wire or memory accounting). Exceeding either clears entire snapshot with DISPLAY_LIMIT; no silent truncation. At most 1024 unique request IDs per controller lifetime; exhaustion requires fresh attachment/view generation before replacement, not auto-retry. No real private history, provisional model output or protected permission. Candidate still lacks real native geometry and operator acceptance.

## NEXT
UI1 shared ConversationFeed transcript-only interface remains absent on inspected main. Do not edit shared files. DOC4F review cursor/revision/clear semantics; Nurse2F independent review; then explicit ForestW preview integration and future host-owned public page transport. Production HOLD.
