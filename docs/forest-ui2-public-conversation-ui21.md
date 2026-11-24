# Forest UI2.1 // Public conversation presentation fixture

DEVELOPMENT ACTIVE / PRODUCTION HOLD. External Hospital-compatible UI2, Nurse 2F review required. No live registration implied.

## IMPLEMENTATION
Additive candidate under widgets/forest/ui2 only. PublicSessionDisplay validates the proposed Mind public-only envelope and four-field OPEN display projection independently of the existing seven-field journal validator. It correlates the requested/current view and rejects the entire malformed snapshot; it never authenticates source or grants access. Public provenance must come from the disposable fixture host, not a schema label. PublicConversationFixture is an embeddable Item with fixed literal public sample messages, reusing the existing ConversationFeed and disabled composer. No Window, live connection, host trust or send/stop handler. No changes to ForestW, ForestChatList, shared controls or existing validators. UI1 insertion/ownership agreement is still required before shared edits.

## HOW TO USE
Source-only preview component; not reachable from the installed widget. No workstation action. Run node tests/forest/test_ui21_public_display.js in an isolated repository checkout.

## VERIFY
CI covers existing producer-to-four-field adapter compatibility, intact raw validator, stale view, record bounds, malformed input, whole-snapshot refusal and fixture source gates. No native Qt/Quickshell rendering claim.

## WATCH OUT FOR
The public display schema remains a proposal, not an authenticated wire contract. The fixture never accepts arbitrary external messages. Structural validation is not a disclosure grant. No history, private titles, credential, inference, new database, real SEND/STOP, fake runtime state or retry. Existing ForestW draft input remains untouched. Native visual acceptance requires UI1-approved insertion and a disposable preview.

## CHECKLIST / NEXT
Nurse 2F exact-head review; UI1 explicit ACCEPT/REVISE/HOLD for candidate paths and insertion. DOC2F fixed status/STOP/unknown mapping, DOC4F canonical context/history snapshot, DOC3F actual disclosure and withdrawal. All shared files remain frozen until narrow agreement. Production HOLD.

## DECISIONS
Reused existing ConversationFeed instead of creating a second chat widget. Public fixture uses its locked composer; no simulated live inference. This is a presentation-only staging PR, not a first-Tree runtime or deployment.
