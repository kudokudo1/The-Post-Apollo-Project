# UI2.3e // Connected public history presentation seam

Development active / production HOLD. Based on accepted history architecture in DOC4F #7159925055, DOC3F #7159931749 and R6a #2661; wire freeze still pending. No transport implementation.

## IMPLEMENTATION / HOW TO USE
Existing PublicConversationFixture retains one history controller and shared feed. Explicit beginConnectedHistory() irreversibly removes literal sample for this Loader lifetime. Owner independently sets whole historyCurrentScope (exact CHERRY, safe generation/revision, distinct 32-hex public session/view aliases), then explicitly attachHistoryScope(ref) after matching accepted history offer. No automatic page. openHistoryPage(ref,requestId,limit) or nextHistoryPage with fresh 32-hex parent page ID and 1/2 limit; read historyPendingRequest and historyNextAfter; owner dispatches only through approved future boundary. receiveHistoryPage(ref,frame) applies matching scope only; existing controller validates pending request, revision/cursor and page. Old scope refused before controller, current invalid/refused page clears snapshot, no reopen on same refused lifetime; use fresh view. Refusal scoped via refuseHistoryScope(ref); independent owner null/change or visibility loss clears. 64 view lifetime cap local, owner retains freshness across Loader instances. No sample fallback; separate explicit new preview. Actual Process/Loader/action fencing and public provenance remain owner responsibility; no incoming page sets expected scope. Operation status independent of history mode. SEND/STOP locked.

## VERIFY
Existing native preview test extends nine phases to fourteen; original assertions preserved, literal clear, two pages, current revision/view change, stale page/refusal/open, scoped refusal, no reuse/fallback and unload. Synthetic public alias pages, not actual R6 child or Mind alias generator; no transport, model, raw IDs or real history. CI pending. UI1 full panel retest and DOC2F/DOC4F/DOC3F exact seam review required.

## NEXT
Review R6a final revisions; connect actual host alias/page action through approved process owner; independent review and operator acceptance. No shared chassis edit or protected release.
