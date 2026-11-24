# Forest UI2.3c // Public history QML view state

DEVELOPMENT ACTIVE / PRODUCTION HOLD. UI2-owned presentation only.

## IMPLEMENTATION
Reuse the merged UI2.3b controller and actual M4 public fixture to expose reactive QML state, message list, pending page reference and completion. Primitive presentation context properties trigger explicit controller observation; attach/detach resets displayed and pending state without automatically opening or fetching. Explicit page functions only, no transport or permission. New offscreen QtQml harness loads actual M4 fixture pages and asserts two-page presentation, scope change invalidation, detach, stale response, refusal and close. Eleven focused tests defined. No second renderer or shared QML edits.

## HOW TO USE
Source test only: python tests/forest/test_ui23c_history_view_qt.py in an isolated checkout with the documented PySide6 range. No installed control or new live data path.

## VERIFY / WATCH OUT FOR
#2540 merged c25a5ecc, reviewed exact 3f8112ff (scoped PASS), M6 #2542 merged dab7ba0e. #2539 shared feed merged 6b4878b6 at reviewed red head; existing REVISE remains effective, no assumption of acceptance. This candidate tests QtQml state, not actual ConversationFeed/Quickshell rendering or ForestW geometry. The future host must update attachment/context properties on actual lifetime changes and separately establish provenance and authority. QML objects and returned messages are local presentation state, not protected storage. Existing controller bounds/refusal semantics unchanged. No actual sender, model, database opener in QML, automatic request or retry.

## NEXT
Independent review and exact CI; UI1 resolves shared feed failures before adapting the fixture or inserting into ForestW. Coordinate integrated public acceptance with DOC4F and host event mapping with DOC2F. Protected output remains DOC3F-owned.

## DECISIONS
Use actual QML property changes to exercise lifecycle rather than add another history controller or renderer. Retain existing defaults and no real history/permissions.
