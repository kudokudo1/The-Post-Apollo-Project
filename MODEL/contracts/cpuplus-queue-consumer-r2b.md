# DOC 2 R2b // AUTO transport consumer (source-only)

Reference: DOC 4 #2564, head 50c97fced332c6816d7eea7e93cb0e1b869562a5,
services/memory/QUEUE-R2-OWNER.md and memory_queue_owner.py. Consumer review
ACCEPT for in-process fixture development; REVISE passive STATUS semantics
before live wiring (Owner.status calls Runtime.tick, which may stage events).

CpuPlusQueueConsumer.js is a pure local state machine. The trusted host supplies
owner lifecycle, ordered replies, bounded timeout, fresh client action UUID and
the reviewed R2a projector. It cannot learn its active owner from a packet.
Only an explicit prepare then submit returns a message; status publication
invalidates prepared confirmation, and submission invalidates the displayed
status. A fresh status is required after every action reply. Pending and
unresolved actions block new submissions; timeout, owner loss, or invalid or
unmatched reply preserves uncertainty. Explicit reconciliation acknowledgment
requires a fresh status and operator review of history; it does not establish
whether the lost action committed or retry it. No raw response/receipt data is
retained, and no kernel/queue/Hub call is made. Expiry has no implicit default.

The consumer deliberately does not select a transport, store a durable client
ledger or implement a real timeout. Host must enforce one logical client and
fresh UUIDs, ordered delivery, timeout and lifecycle. A complete UI/host restart
loses local unresolved state; future integration must reconcile durable owner
history before enabling a new action. Existing owner sequence is a coordination
fence, not authentication. Do not send raw 64-bit identity integers into JS.
The fixture uses a stand-in projector because #2558 is still open; use its
actual strict projector for the combined test. Status remains historical only.
No live registration, activation, automatic dispatch or verified completion.
