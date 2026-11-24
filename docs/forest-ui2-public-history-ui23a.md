# Forest UI2.3a // M4 public history display

Development ACTIVE / production HOLD. UI2 owns presentation only; DOC4F owns M4/B1/B6. Nurse 2F review required.

## IMPLEMENTATION
Accept merged M4 #2530's exact public history envelope and cursor semantics. Independent pure UI2 page adapter correlates request ID, Tree, view generation, session ID, revision, requested cursor and page limit. Strict record shape, exact ordinal continuity, unique turn IDs, role, UTF-8 limits, control rejection, compact candidate JSON bound; entire invalid page refused. Return copied plain-text ConversationFeed message fields, completion flag, and explicit next cursor. Does not append pages, fetch them, retry, assert authentication or render private records. Revision bounds ordinal but need not equal turn count. Completion is the host's fixture report, not independently proven by UI. No shared files modified.

## HOW TO USE
Source testing only: node tests/forest/test_ui23a_public_history.js. Actual M4 producer interop uses in-memory disposable SQLite and fixed sample messages. No model calls, transport, user journal, native QML or actual ForestW insertion.

## WATCH OUT FOR
A caller can fabricate valid records. Only host-owned fixture provenance establishes public classification; this parser cannot grant access or prove actual committed storage. No raw provisional event; no automatic next page or retry. A future view controller must clear old pages on reattach, use a fresh request ID per explicit page and preserve same session/revision/view binding; cross-page ID/ordinal continuity and bounded accumulation need separate verification. Actual protected delivery remains DOC3F-owned. UI1 transcript-only ConversationFeed API not on inspected main; #2529 merged but insertion still HOLD.

## NEXT
UI1 shared feed seam, narrow ForestW preview patch and independent native visual review. Coordinate page controller with DOC4F and runtime status with DOC2F; protected output remains HOLD. No deployment or merge.

## DECISIONS
Use actual M4 fixture rather than invent a competing history producer. Keep single-page projection bounded and no hidden fetch or cache.
