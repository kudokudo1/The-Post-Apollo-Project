# R4b ordered local fixture delivery candidate

Depends on exact independently scoped-reviewed R4a #2588. This is a Runtime
owner candidate for review, not an installed sender or permission. UI2 accepted
the proposed six-field local presentation unit in #7152819926 subject to DOC3F
placement acceptance. No UI source or actual ForestW hookup is included.

Owner supplies independently resolved original FixtureDeliveryBinding
(OperationRef, exact B6 attachment, exact R4a Tree pair and separate local
correlation). Host issues fresh independent 32-hex requestId and viewKey
using PresentationCorrelation.fresh; generation matches attachment view
generation. The token shape is a candidate decision for UI2/DOC3F review.
No M4 pagination request, private identifier or original effect identity
may be reused. Resolver returns an independently current binding only
while isolated public provenance is established, not a UI flag.

LocalFixtureDelivery owns one existing R4a projection and synchronous ordered
owner-thread callback. No public packet input or queue. Resolve before
projection and immediately before callback. Exact unit fields are requestId,
viewKey, generation, sequence, kind, statusPacket. STATUS is exactly the
seven-field false-authority R4 packet, WITHDRAW has null. Sequence starts at
1; NO_UPDATE emits no callback or sequence. Initial IDLE is not dispatched;
first normal status REQUEST_PENDING. Terminal status cannot be promoted:
late internal events invalidate, finish/STOP ACK after terminal do not
emit, explicit current withdrawal can close. No implicit history refresh.

If currentness is lost or changes, invalidate locally without sending to
the new view. Explicit withdrawal can send only to the still-current exact
old view. Callback exception or re-entry invalidates without retry. The
owner MUST separately close/clear only the returned instance correlation
on INVALIDATED, even if the callback previously painted. This result
is local, not a delivery receipt. UI2 checks independently observed view
and exact sequence; stale other-view packets/withdrawals ignored, malformed
current-view/gap/duplicate closes that lifetime; uncorrelatable input cannot
mutate a new view. Detach clears immediately without relying on a callback.
No async callback or retained queue permitted by this candidate. Future
cross-thread/transport adapter must separately fence and invalidate queued
work, not reuse this as a protected sender.

No authenticated currentness, continuous atomic custody, private status,
C5 release, terminal receipt, resource admission or model execution claimed.
Tests use actual R4a/R3/B3 fixture with a recording callback, not real UI2.
DOC3F and UI2 acceptance of placement/invalidation/consumer required before
any actual integration. Independent Nurse review and operator merge separate.
