# CPU++ R2a // Notify-only runtime owner and transport proposal

DOC 4-owned reference. Operator-approved development direction and Nurse 2
integration review permit scoped development, not production activation.
Review with DOC 2 before freezing an actual wire format.

## Owner

One cooperating Linux owner opens the existing private Queue database, takes
a nonblocking exclusive flock on its existing inode, and only then constructs
Runtime. No extra daemon, socket, polling timer or privileged helper. A second
cooperating owner refuses; closing or process exit releases the lock (unless
a forked child retains the open description; never fork while held). Check
same PID, file identity, permissions and link count before and after calls.
SQLite's normal transaction locks are separate. All future cooperating
runtime writers must use the same owner; direct Queue callers, same-UID
adversaries, renamed/recreated paths and external root tools are not fenced.
File replacement invalidates the old owner; do not infer security authority.

## Proposed in-process envelope

STATUS: version=1, owner_id UUID per construction, strictly increasing sequence,
next_action_sequence, kind=STATUS, can_execute=false, projection=exact R1 tick
object. DOC 2 may pass only projection to its existing strict presentation
parser. ACTION: same envelope metadata, action_id UUID, action_sequence,
disposition REPORTED/REFUSED/UNKNOWN, code, result or null, invalidate=true.
REPORTED is a local runtime return, not a verified memory adjustment.
DETAIL: developer-only history response. The actual wire/JSON encoding,
including safe representation of Linux 64-bit inode/device values, must be
agreed separately. Do not expose raw request or history as JS numeric identity.

Client action message: exact fields version, owner_id, action_id,
action_sequence, kind, expected_request_id, target_gib, expires_at.
QUEUE requires null expected ID; REPLACE/CANCEL/EXPIRE/RECHECK require exact
pending request UUID. Target and expiry are explicit for QUEUE/REPLACE,
otherwise null. No arbitrary commands/paths, no execution action. An action
sequence is consumed before dispatch; no replay in the same epoch. This is
a single logical client sequence, not per-tab independent sequences. Old
owner messages fail after restart; no automatic re-dispatch across epochs.
Lost/unknown response requires read-only reconciliation of intent/history.
An action error is not evidence of noncommit. Malformed requests refuse.

## UI and scheduling contract

Host owns scheduler in runtime monotonic domain. Schedule only non-null
next_check_monotonic_ms and explicitly wake after local intent change.
Owner must stop publishing when disconnected, clear stale projection on
action dispatch, accept only increasing sequence from the active owner,
and invalidate on owner loss/change or reply timeout. Read fresh STATUS
after action (even unknown/refused). Do not compare monitor monotonic
deadline against QML wall clock. For now READY remains historical REPORTED
/ RECHECK REQUIRED; do not enable APPLY. Host must bound transport lifetime
and observation freshness before native deployment. No candidate replay,
completion promotion or asynchronous Hub packet transport in this slice.

## Dependencies

DOC 1 protected directory identity/recovery observation and DOC 3 timestamped
telemetry reuse remain missing. No inferred source/IDLE from public capacity.
DOC 2 must review envelope and consumer lifecycle. #2560 remains independent;
no change to its files. Stage-failure recovery, native runtime wiring, actual
Hub offer and tests remain. #2412 protected execution/automation HOLD.
