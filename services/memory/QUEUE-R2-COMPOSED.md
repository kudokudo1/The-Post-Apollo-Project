# CPU++ R2 composed candidate qualification

DOC 4-owned test-only milestone; references the actual DOC 2 sources without
editing them. Exact open candidate heads: #2564 e94715dd, #2560 e2764368,
#2565 2ca4e7c6, #2558 d4ecae3b. Dedicated CI uses read-only checkouts at full
commit SHAs; overlays only the delivery module into a disposable copy of the
owner memory modules. This is not a merge, current-main qualification,
or approval of any candidate. Re-pin and rerun after any relevant head
change; eventual combined main tests must use actual merged source.

The Node driver loads actual consumer and projector in separate contexts.
It generates explicit action messages and sends them to an actual Python
Owner/Runtime in a disposable stdin/stdout test process with a private
temporary SQLite database and deterministic clock. This is a fixture
transport only, never an installed service or selected IPC design.
No procfs reads, native identities, protected operations or real Hub.
The Python fixture exercises the real Delivery attempt against a current
passive publication with a synchronous fake offer; does not transmit
reservation packets across the wire. Source identity integers exceed
JavaScript safe integer range; action replies omit them.

Acceptance cases: idle and repeated passive reads cause zero observation
or event staging work; explicit queue and deferred event; stale sequence
refusal; one-attempt delivery dedup; actual projector accepts readiness
only as historical; recheck resets sampled continuity; passive deadline
and provider loss invalidate; lost replace reply, restart, stale epoch
and manual reconciliation; cancel returns to idle. Counts are deterministic
fixture call counts, not measured native CPU, PSS, memory or wakeups.
Native protected reader, actual transport/host scheduling, notification
routing and resource acceptance remain pending. No new daemon or live
memory adjustment. Protected completion/automatic execution HOLD.
