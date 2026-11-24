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
