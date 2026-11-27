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


## FL7 // test-only serialization/control seam

Nurse #2161 7218321562. Delivery now checks the original Thread object
rather than recyclable numeric identity, aligned with FL6. Existing host
and delivery methods remain unchanged. Combined B3/host/delivery CI is
required against integrated FL4/5/6.

UI1/UI2 disposable child: launch only
`python3 tests/forest/first_light_delivery_child.py` from repo checkout.
No arguments, no actual Ollama, no native launcher. It owns the real
FirstLightDelivery on the child thread and a fixed fake loopback B2
peer emitting RE + ADY. One JSON line command, one JSON line reply,
synchronous request/reply, <=512-byte input and <=64 commands per child.
Use an asynchronous parent process adapter; never block the GUI thread.
No automatic retry. The test child is not a native streaming scheduler
and cannot accept STOP during a blocked STEP; actual native control
must be independently available. Close or EOF disposes the test journal,
not evidence of native settlement.

Commands (exact keys):
- {"op":"OBSERVE","epoch":1,"visible":true}: actual independent view
  incarnation, increasing positive integer (<=2147483647), fresh epoch
  for every close/open/Tree/Loader replacement, including invisible.
- {"op":"SUBMIT","epoch":1,"prompt":"Reply with READY."}: fixed exact
  prompt only; ok means command handled, NOT native admission.
- {"op":"STEP"}: owner advances one internal frame, no raw frame returned.
- {"op":"TAKE","epoch":1}: one latest snapshot or null, plus original
  epoch; snapshot fields sequence/status/text/local_outcome/provisional/
  native_admitted (always false). No raw original IDs.
- {"op":"STOP","epoch":1}: contextual original STOP acknowledgement.
- {"op":"OUTCOME"}: owner local status/outcome only, no body.
- {"op":"CLOSE"}: owner closes test lifetime; no provider settlement.
  Refused command returns {"ok":false,"error":"COMMAND_REFUSED"}.

Parent must pin its own observed epoch at command issue, compare returned
epoch against the independently current GUI view immediately before
render, discard queued old data on withdrawal (even after TAKE), and
never reattach original on A-B-A. No callback from child establishes
currentness or grant. Keep one child/original trial, no new submit after
withdrawal or terminal; no persistent history. UI1 owns native test mount
and actual epoch observation; UI2 owns typed bounded snapshot/render
validation, same-row response and scroll, no draft clear from native false.
Existing installed SEND remains locked; no R6 relabel or new production
wire. Native admission/recipient/source/capacity/crash custody unresolved.
