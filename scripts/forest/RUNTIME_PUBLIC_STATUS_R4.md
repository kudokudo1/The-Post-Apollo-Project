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
