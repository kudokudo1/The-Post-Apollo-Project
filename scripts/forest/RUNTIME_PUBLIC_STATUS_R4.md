# R4 fixed public runtime status candidate

Disposable public fixture only. Owner supplies exact existing R3 OperationRef
and B6 BarkAttachment; independently resolves both again for every operation.
This is not a public-data classifier or authentication mechanism. Do not
pass private runtime events here; even status timing can reveal activity.

One owner-thread projector per original attachment and operation. Fixed
candidate fields: schema, status, sourceAuthenticated=false,
permissionGranted=false, productionAuthority=false,
modelExecutionPermitted=false, safeActions=[]. No task/session/attempt IDs,
raw event ordinal, model, text, exception, timestamps or resource evidence.
The caller must separately correlate its public local request/view, never
serialize the internal binding. Candidate dictionary is not a wire schema.

Status labels: IDLE, REQUEST_PENDING, PREPARING, GENERATING, STOP_REQUESTED,
LOCAL_COMMIT_RECORDED, UNKNOWN_HOLD. LOCAL_COMMIT_RECORDED is not delivery,
permission, positive protected receipt or resource release. STOP ACK is
owner-observed actual R2 result only, not an action from UI or terminal ACK.
UNKNOWN_HOLD is sticky; no replay. Missing terminal frame, sequence mismatch
or invalid transition fail closed. Detach/changed recipient/view/task/operation
returns None and irreversibly withdraws this instance; host must clear display.
A fresh attachment requires a separately resolved operation, not replay of
old events. No actual sender, revoke fence, or continuous custody claim.

DOC3F must review placement and actual output release before any sender.
UI2 owns rendering, local request/view correlation and clearing stale state.
No SEND/STOP capability enabled. This candidate does not establish native
execution permission or resource safety. Tests use actual R3/B3/M2/R2 with
fake model and disposable SQLite, including loss of terminal observation.

## R4 revision: transition-only updates

observe, observe_stop_ack and finish return a fresh fixed packet only on a
status transition. Observation.NO_UPDATE is an internal non-serializable
sentinel: do not publish it or clear the view. None means withdrawal and
must clear the view. DELTA still participates in exact internal ordering,
but emits no repeated GENERATING or STOP_REQUESTED status. Repeated ACKs,
finish after terminal and repeated HOLD do not produce extra packets.
Snapshot is for explicit owner-side inspection, not a per-token send hook.
No polling or scheduling based on internal fragment count. This removes
fragment-count-dependent status emissions, not all timing side channels.
Only isolated public fixture operations are eligible.

Proposed UI2 correlation remains a separately resolved public request and
view lifetime held by the host; the status packet contains no original
operation, attempt or attachment identity. A host must invalidate pending
updates and clear on detach or changed request/view before display; no
automatic reattachment, retry or retarget. Actual adapter/send placement
requires UI2/DOC3F agreement. No wire schema is frozen here.

## R4a canonical Tree compatibility

B6 separates canonical Tree identity from the selected presentation hint.
M4 assigns independent binding to its fixture host; no trusted universal
alias registry exists. The only supported R4a disposable pair is exactly
FixtureTreeBinding("cherry", "CHERRY"), as used by M6b. Uppercase-equal
legacy R4 test data is replaced; no other Tree, Clone, case conversion,
registry, persistent migration or authentication is implied. The host
selects the original pair independently of the UI, and provides a freshly
resolved current_tree_binding together with current_operation and
current_attachment at every observation, snapshot, STOP ACK and finish.
Missing or changed evidence permanently withdraws the existing view.
Matching pair alone cannot authenticate a host or establish public scope.
The currentness sample is not an atomic final-send fence. Actual sender
and local request/attachment delivery correlation remain pending owner
agreement. The seven-field packet and tri-state update contract are unchanged.

Integration test uses a real R3/B3 disposable canonical journal, then an
explicit fresh M4 history request on the exact same attachment at the new
revision. No R4 packet becomes a history row, no implicit refresh or raw
runtime text forwarding. No protected data, native inference or UI hook.
