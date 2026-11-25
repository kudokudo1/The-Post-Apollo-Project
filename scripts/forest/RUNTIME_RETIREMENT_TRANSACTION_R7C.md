# Runtime R7c-a // Durable retirement transaction proposal

Development ACTIVE; actual retirement, protected writer, native and production HOLD.
DOC2F Runtime; main dcf22ace4872fab3e408051650980483dbe52e7c.
R7a #2703 merged; R7b #2778 read-only fixture, scope ACCEPT #7169077778.
R7b is NOT authority, an actual freeze, or proof of an existing dormant task.
This proposal is source-only, not approval for new schema or a writer.

## Concrete missing link

B1 session_journal_v0.py d1533f150 has owner/tree/session/revision
and OPEN/PAUSED/ARCHIVED; set_state (231+) opens its own write
transaction and increments conversation revision. It does not bind a
TaskContext or check B3 reservations, actual provider work, independent
settlement, resource custody or lifecycle intent. PAUSED is not Winter.
B3 c5dbbc29 has a per-session RESERVED uniqueness fence and committed
reply transaction; B4d e4f4a537 is local-only. Neither records a durable
task-to-session lifecycle mapping. R5b reopen and R7b eligibility cannot
supply it. Original task_session.py a2458c4e (6227+) wrote a dormant
record before clearing the active slot, preserving continuity over
optimistic cleanup; recover that invariant, not separate YAML stores.
UI2 R2 #2773 requires metadata discovery separate from task claim.

## Owner questions and proposed transaction invariant

Prefer a single existing owner-approved durable transaction domain if
the actual canonical task/session store can support it. Do not invent
a second journal or assume the current disposable B1 store is the
production custodian. Mind and Runtime must identify the actual mapping
owner, record identity, writer and read-snapshot boundary; Security
must approve authority/effect/receipt custody and recovery ordering.
A multi-store alternative needs a separately reviewed durable fence and
reconciliation protocol; do not claim atomicity across independent DBs.

Proposed semantics, not field names or a migration:
- Original principal/Tree/Clone/task/execution-context, lifecycle
  generation/revision, independently resolved exact continuity
  session and conversation revision, retained last operation/attempt/
  binding/settings and evidence identity are distinct. Conversation
  revision alone cannot establish a lifecycle change. No alias, model
  tag, timestamp, hidden UI or PAUSED inference.
- Explicit retirement intent, original effect identity and independently
  current authority must precede mutation. Freeze conflicting dispatch
  and activation in the actual durable owner domain; an in-memory flag
  or R7b positive result is not the fence. All actual dispatch/append/
  resume paths must respect that fence, including restart and concurrent
  clients. No implicit STOP or automatic cancellation.
- Resolve B3 local attempt and independently attributable provider
  terminal/quiescence, Heart resource accounting and Security settlement.
  Unknown, conflicting or still-active remains fenced; do not retire
  on socket close, local COMMITTED/ABORTED, or shared weight residency.
  Evidence must match original scope, remain current at commit and be
  independently trusted, not caller-created synthetic flags.
- Within the agreed transaction, compare original task lifecycle
  revision, exact session/revision and last attempt lineage, active-slot
  ownership, original effect/fence and currentness. Transition exactly
  that task to dormant and release its active claim atomically, retain
  committed conversation references without deleting or duplicating
  rows, and durably record the original effect outcome in the same
  owner-approved transaction/receipt boundary. No body/title read
  for eligibility or discovery. No resource unloading in this writer.
- Optional B1 PAUSED as a secondary append guard must be separately
  agreed with Mind (revision/history implications and all writer
  paths); never invoke current set_state as an independent nested
  transaction or treat its revision as a task lifecycle record.
  Do not choose state representation or create tables before owner
  agreement.
- A lost acknowledgment is not a failed commit. Read-only recovery
  inspects exact original effect/identity and durable outcome; committed
  means no second mutation, unknown remains HOLD, conflicting records
  do not auto-pick newest. No automatic retry. No real catalog exposure
  until the independent lifecycle commit and disclosure boundary are
  established. Restoration requires a new explicit claim and separate
  plan/currentness/authority/admission; never revive original grant.

## First proposed R7c-b scope (requires separate approval)

An isolated fixed-public transaction witness using one disposable
existing SQLite connection, only after Mind/Security identify and
approve the canonical synthetic mapping/record owner and exact writer
contract. Do not implement until Nurse scope ACCEPT. No actual provider,
private content, protected permission, production or actual resource
release. If owners cannot agree storage ownership, HOLD rather than
invent a parallel ledger. R7b eligibility is merely input semantics,
not an authorization token.

Acceptance requirements: wrong task/owner/session/revision and stale
attempt; competing reservation/activation; missing or changed fence/
settlement/accounting; unchanged committed body/turn rows; no body read;
two competing intents cannot double-retire or activate; interruption
before commit preserves prior state; interruption after commit but
before receipt preserves one retired identity and read-only recovery;
duplicate/conflicting effect refused without mutation; no implied
restoration, permission or physical release. Explicit review of all
actual writer paths and transaction ordering needed before any real
lifecycle action.

## Required owner decisions

Mind: identify mapping/continuity transaction owner, lifecycle versus
conversation revision and secondary B1 guard implications.
Security: original effect fence, independent settlement, protected writer
and durable receipt/recovery ownership; synthetic scope only initially.
Heart: exact terminal/quiescence/accounting handoff; no released-byte
credit or stale restoration admission.
UI2: synthetic dormant selector remains independent; no actual catalog
or plan until lifecycle and disclosure accepted. UI1 no mount or wire change.
Nurse2F: exact R7c-a design and R7c-b scope review after owner agreement.
No executable change, schema, writer, host mutation or production approval.
