# CPU++ M1c.3b // Durable intent storage (DOC 4, proposed interface)

Source-only slice of #2433 / #2434. No live service, QML import, command execution,
monitor, notifications or privilege grant. The existing MemoryOperation singleton,
helper, snapshot and shared workflow remain owned by their respective lanes.

Interface: Queue(path), enqueue(target_gib, source, now, expires_at),
replace(expected_id, ...), cancel(expected_id, now), expire(expected_id, now),
pending(), lookup(request_id). Keyword-only arguments except expected_id/path.
Timestamps are integer Unix seconds. No default expiry or automatic expiration.
The integration caller chooses the unprivileged private storage location and
collects a fresh boot ID and managed base/extension device/inode/size_kib
observations; absence is null. These observations are untrusted historical intent,
not a safety or identity proof. No arbitrary paths or credentials in request data.
Target is managed NVMe capacity, in whole GiB (0–64 step 4), not total swap.
Zero is recorded intent only; unsupported execution must remain blocked.
The database uses SQLite transactions, FULL synchronous mode, one pending row,
explicit ID-checked replacement/cancellation/expiry and terminal row retention.
Corrupt/unknown schema is not reset; retain the file for inspection. No retention
policy chosen. Storage initialization requires a private regular user-owned file
and existing parent directory. This is not a protected security boundary.

Only QUEUED/CANCELLED/REPLACED/EXPIRED exist in this slice. Readiness,
blocker evidence, recheck timestamps, recovery states, execution receipts and
durable notification events are subsequent milestones. Reopen does not replay,
check conditions or authorize anything. The caller must explicitly reconcile
boot and expiry before any later readiness evaluation. Future schema migration
must preserve existing intent and history; version 1 is not a frozen ABI.

DOC 1 owns safety/preflight and mutation. DOC 2 owns UI and explicit user actions.
DOC 3 owns diagnostics. Connections owns any protected reusable grant (#2412).
DOC 4 owns queue state and future monitoring/notification adapter. Nurse 2
reviews. No production integration or local-machine changes authorized here.

## M1c.3b.3 // advisory readiness and storage review follow-up

Nurse 2 review of #2439: private parent (same UID, mode 0700 or stricter,
no symlink path components), single-link DB, identity rechecks on transaction,
initial directory fsync, full history audit on reopen and explicit audit_history().
These reduce accidental replacement and history corruption, not same-UID attacks,
ancestor replacement races, hostile SQLite files, or full native power-loss risks.
Existing unsafe paths are refused, not repaired. Production path selection remains
an integration decision; recommend a dedicated private directory beneath the
operator's XDG state directory, not a shared database. Native crash tests pending.

memory_queue_advisory.evaluate is a pure version-1 display projection using DOC 1's
reduction-preflight v1 response, caller-bound boot/source IDs and an explicit
sample age limit. A previous sample from the same observer is needed; this is
only two observations, not a calibrated stability interval. Discard it on restart.
Unknown, expired, stale, mismatched and busy observations refuse readiness.
The request remains QUEUED; READY_ADVISORY always has can_execute=false. No
persisted readiness or replay, no operation invocation, no monitor or QML adapter.
Caller must provide actual independent observations and an operation-state witness;
no protected file identity collection or root lock witness is implemented here.
Only bounded reduction advisory is supported. Expansion and other operations are
not inferred from a missing reduction result. The storage schema stays v1.
