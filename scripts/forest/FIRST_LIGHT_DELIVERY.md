# First Light FL5 // owner-worker delivery seam

Nurse #2161 7217350418, Spirit #3037 7217426821, UI2 #3037 7217404872.
Development-only fixed-public disposable trial; no native recipient,
execution authorization or installed UI connection. FL4 may integrate
independently; this uses the unchanged FL3 host method contract.

The existing host is created and consumed by one owner worker in
FirstLightDelivery. No iterator, raw frame or raw original ID is handed
to a view. Worker methods submit(view, prompt), advance(), owner_outcome()
and close() reject foreign-thread access and reentry. Observe view
changes independently with observe_view(view or None); an opaque
incarnation object is local correlation only, not an identity or grant.
One original view is pinned when submitted; any change withdraws it
irreversibly for that trial, including A-B-A. No replacement attachment.
Owner must observe every transition; take(view) checks at dequeue and
consumes one latest immutable replacement snapshot. A receiver must
still discard after view change before render; local take is not ACK.
No user callback under lock. Queue bounded to one snapshot, full text
bounded to B1 MAX_BODY UTF-8 bytes, separate increasing sequence may
skip intermediate updates. No raw errors, provider diagnostics or IDs.
No claim of authenticated or atomic cross-process egress.

Status: PREPARED, LOCAL_RESERVED, GENERATING, STOP_REQUESTED,
LOCAL_COMMITTED, UNKNOWN_HOLD. Native admission always false.
No explicit safe-refusal receipt yet: setup/dispatch uncertainty stays
UNKNOWN_HOLD, never auto-retry or clear draft from absence of reservation.
Local commit displayed only after R3 terminal, worker exhaustion and
original journal local outcome plus exact accumulated text. On unknown
the disposable terminal snapshot discards provisional text; no personal
retention/destruction policy. request_stop(view) resolves original local
operation and attempt internally; STOP_LATCHED is request observation
only, not provider terminal. Withdrawal clears queued output but does
not stop the original worker. Owner can still inspect local outcome.
The original host run_internal() remains an internal worker-only API;
the delivery wrapper does not export it. Direct misuse of that generator
outside the wrapper is not prevented by this slice.

UI1/UI2: use this actual local producer in bounded integration tests;
existing composer/feed, one original response row, independent current
menu/view/Tree/Loader observation, no raw IDs and no native SEND unlock.
Coalesced sequence requires monotonic advance, not contiguous delivery.
Do not turn local reservation into native admission or local commit into
provider quiescence. No native wire or actual source/recipient selected.

Heart/Spirit: actual source, POST fence, capacity, independent recipient
and durable original effect/terminal custody remain external requirements.
No qualified provider, actual model invocation, permission, retry,
scheduler, new store or installed host. Existing B3 workflow exercises
this implementation with actual B2 to an ephemeral fake HTTP peer.
