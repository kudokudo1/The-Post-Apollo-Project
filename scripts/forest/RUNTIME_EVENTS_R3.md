# R3 host-correlated internal events

Disposable fixture composition only. Reuse B3/M2/R2; no independent model
execution engine, journal, scheduler, sender or positive admission path.

Owner constructs OperationRef from exact host-resolved SessionContextRef
(B6 task identity, session, user turn and expected revision) and original
operation ID. RuntimeExchange receives existing B3 bridge, host model
settings and independently resolved current context. Caller must establish
fixture provenance, resource safety and authorization separately. No
production or native invocation is approved by this interface.

run() is consumed once by the database owner thread. InternalEvent has
operation, attempt_id (None until RESERVED), monotonic ordinal starting
at 1, and read-only flat B3 payload. REQUESTED precedes actual B3 events.
COMMITTED is emitted only after B3 iterator exhaustion and cleanup.
All errors/ambiguous effects conservatively end UNKNOWN_HOLD; this is
not a claim of durable ABORTED, no effect, or resource release.
Authoritative B4 reconciliation and terminal mapping remain separate.
Abandoning the iterator closes B3; no terminal frame is promised.

STOP takes the exact owner-resolved operation and active attempt. A
pre-reservation STOP uses None. If binding races that reference it
refuses rather than guessing another attempt. A host must correlate the
active reference, not automatically resend. Closed and entry-won are not
cancellation receipts. No automatic retries or global model kill.

Frames are **internal**; text and identifiers are not a Bark projection.
Never send raw frames, their repr or exceptions to UI or a recipient.
DOC3F owns actual output release and serialized-byte ordering. UI2
presentation statuses require separate approved projection/withdrawal.
Internal ordinals are NOT outbound sequences or consent spend.

Tests run real B3/M2/R2 over disposable SQLite with injected fake
transport, not real Ollama. No native installation or protected authority.
