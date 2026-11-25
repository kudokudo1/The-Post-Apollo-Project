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

STATUS: owner-driven publish() only; version=1, owner_id UUID per construction, strictly increasing sequence,
next_action_sequence, kind=STATUS, can_execute=false, projection=exact R1 tick
object. DOC 2 may pass only projection to its existing strict presentation
parser. ACTION: same envelope metadata, action_id UUID, action_sequence,
disposition REPORTED/REFUSED/UNKNOWN, code, reduced result or null, invalidate=true.
REPORTED is a local runtime return, not a verified memory adjustment.
The reduced ACTION result contains version, can_execute=false, adjustment_outcome=UNVERIFIED and (for durable intent actions) request id/state/target_gib/expires_at, wake_required and notification_error. No raw device/inode, source or notification packet. DETAIL: developer-only history response. The actual wire/JSON encoding,
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

Host owns scheduler in runtime monotonic domain. publish() may observe and stage events; status() only copies the latest publication, checks owner clock/deadline/expiry, and returns None if unavailable. No tick, staging or revision increment on passive read. Opening AUTO never invokes publish(). Same revision is historical; reconnect requires host-issued fresh publication, not a UI-triggered tick. invalidate() clears the cached publication on owner/observer/transport loss. Action dispatch consumes sequence and clears publication; explicit RECHECK may sample, but a fresh owner publication is required afterward. Host must signal null/loss to client and enforce deadlines even when no UI reads occur. Schedule only non-null
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

## R2a.1 // DOC 2 response

ACCEPT semantic envelope; revised passive reads and reduced action results after DOC 2 review #2564. Native transport still unselected, raw DETAIL remains Python-only, no wire compatibility or combined consumer fixture claimed. Host-owned lifecycle, deadline invalidation and a single logical client remain requirements. DOC 1 proposed protected read-only sample mapping accepted conceptually: BUSY only witnessed contention, UNKNOWN for missing lock/fence/provider or recovery, no enqueue with missing identity. Connections transport pending.
