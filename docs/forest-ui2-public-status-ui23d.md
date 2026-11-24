# Forest UI2.3d // Public history status presentation

DEVELOPMENT ACTIVE / PRODUCTION HOLD. UI2-owned isolated public fixture only. Nurse 2F checkpoint #7147608620.

## IMPLEMENTATION
A small noninteractive QtQuick status item for the existing history view state. Fixed plain-text labels for closed/pending/partial/complete/refused and bounded-display refusal, never rendering arbitrary reason/state text. Hidden until explicitly attached in the disposable harness; fixed SEND/STOP locked and false authority flags. Reuses actual M4 pages and merged UI2 QML history state, no new renderer, controller, transport or database. Nine offscreen tests defined.

## HOW TO USE
Source test only: python tests/forest/test_ui23d_public_status_qt.py. Not inserted into ForestW. No actual control dispatch or backend contact.

## VERIFY / WATCH OUT FOR
#2551 merged a8536c6d, scoped PASS, 11 QtQml cases passed per reviewer. UI1 #2556 native feed still blocked at inspected head 58aaf080; cmp dependency repair belongs to UI1. This test instantiates isolated QtQuick item, not native ForestW or shared ConversationFeed, and does not verify full geometry or operator acceptance. History complete means producer-reported snapshot completion, not inference success or protected delivery. Never bind the status item to raw Runtime events or protected private history. Labels and palette placement need UI1/operator visual review.

## NEXT / R4 coordination
ACK DOC2F #7145226582: no raw OperationRef, attempt ID, DELTA, internal ordinal, COMMITTED or exception passed to Bark; no direct cancellation Event. UI2 proposes only fixed local presentation labels for request pending, running, STOP requested (not cancellation receipt), UNKNOWN_HOLD (not ABORTED, no automatic retry), and detached/withdrawn (not revoke ACK). These are semantic suggestions, not implemented execution mapping, schema, wire contract or permission. DOC2F/DOC3F must agree exact public status projection and delivery/withdrawal before UI2 consumes it; separate generation outcome, durable result and authorized disclosure. No fabricated positive status or real SEND/STOP controls. UI1 correction and independent acceptance before actual ForestW insertion.

## DECISIONS
Keep status labels fixed, separate from payload and runtime, explicit display-limit refusal, no automatic history fetch. Production HOLD.
