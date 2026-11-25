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


## Revision 1 proposal // exact mapping and transaction owner intake

Post-merge main b57277b1, R7b #2778 and R7c-a #2785 merged.
Nurse #7169709860 design ACCEPT / R7c-b HOLD; Mind #7169647526
REVISE; Security #7169646591 design ACCEPT. This resolves the questions
for review, NOT authorization to create a schema, implement or execute.

### Named ownership and minimal candidate record

Runtime proposes ownership of one canonical task lifecycle mapping
inside the existing B1/B3 SQLite transaction domain, with Mind owning
the existing session/turn lineage and transaction compatibility.
This is a proposed extension to the owner-controlled journal, not a
separate DB, task service, event log or second active-slot authority.
No existing canonical durable mapping was found in the inspected Forest
B1/B3/R3/R5 sources. B1 remains the only conversation truth. Actual
production store/custodian is not established; first candidate is a
disposable journal only. Security owns effect authorization/receipt
semantics, not a Runtime-minted grant.

Proposed record semantics for the first scope (names illustrative):
- immutable task identity: principal, Tree, task, execution context,
  generation, origin, base-Tree (Clone absent); independently resolved,
  not user-provided alias. Exact B1 session identity links continuity.
  Require a unique task identity and unique session association for the
  limited one-task fixture; no assumption all future Tasks use one
  session. Never use session title or conversation revision as task ID.
- separate positive lifecycle revision and lifecycle state
  ACTIVE / RETIREMENT_PENDING / WINTER. For the first one-slot fixture
  the active claim is derived from ACTIVE or RETIREMENT_PENDING in the
  same record (pending retains claim); WINTER releases it. No second
  mutable active flag or active-slot row that can contradict this state.
  Explicit original slot scope and exclusivity constraint required.
- pinned continuity session revision and exact last B3 attempt/turn/
  operation + retained H11 binding/settings identity; independent
  currentness and effect identity checked on every transition.
- one immutable original retirement effect ID, original lifecycle
  revision and disposition retained through pending and WINTER. The
  same owner transaction records its committed outcome; lost ACK reads
  that exact outcome, no new effect or rewrite. A future Spring claim
  must preserve this receipt rather than overwrite it; not in scope.
  No raw metadata/digest publication or actual authenticated receipt
  inferred from fixture values.

No storage format, DDL, migration, production path or positive
permission frozen here. Ask Mind/Security/Heart to agree record and
transaction semantics and the exact first fixture boundary below.

### Writer inventory and proposed ordering

B1 d1533f15: create_session, append_turn, set_state, _write. B3
c5dbbc29: _reserve, _commit, _abort, _commit_fenced, exchange;
M2 1085bc56: snapshot_in_transaction. R5 7dba584a owns fixture
connection, create_session, append_turn, advance and reopen; R6 wraps
R5 and is fixed public. B4a 5948497e generate calls bridge.exchange;
B5b 1b21eb72 is a disposable FD HOLD candidate, not a lifecycle writer.
These are existing entry points, not an exhaustive proof of installed
writer exclusion. Actual create/append/reserve/resume/activation and
provider dispatch must all use the same authoritative lifecycle fence
before a real retirement can be accepted. Existing B1/B3 direct calls
have no such fence and can bypass an outer wrapper; do not claim safety
from one new retirement API. B1 PAUSED omitted per Mind.

Pending intent must serialize against new work. Existing admitted
attempt settlement remains allowed only for the exact retained attempt,
not every RESERVED row; a reservation alone is not authorized dispatch.
If send status is ambiguous, preserve pending HOLD. Do not let a
previously reserved but unadmitted request start after freeze. Terminal
writer must not be blocked merely by pending state, nor permit
replacement context. Currentness/fence check in actual write domain,
not a stale pre-read. For a writer transaction, recheck exact metadata
and B4d lineage in that transaction; do not call R7b by disabling
query_only or nesting its caller-held read transaction. A shared
metadata predicate refactor would need explicit review.

### Proposed smallest R7c-b executable scope for Nurse decision

One fixed-public base-CHERRY task and one already committed B3
attempt, no active model or provider; existing disposable B1/B3
connection and owner-selected fixture-only mapping/record. No actual
freeze of running inference, restoration, protected authority, R6 wire
or installed writer change. Use explicit owner-approved synthetic
record extension on the same database ONLY if all owners agree.
Transaction witness must prove compare-and-set against original
lifecycle revision, exact session/revision and last committed attempt,
pending effect identity, five separate fixture references and no
competing RESERVED. Freeze candidate (pending) and terminal dormant
commit are separate explicit effects; final dormant transition and
active claim release/outcome atomic, no mutation of B1/B3 rows.
Unknown stays pending and fenced within the witness.

Because current direct B1/B3 writers lack a lifecycle fence, either
agree separately scoped integration of their actual checks first or
limit this witness to the owner-exclusive disposable transaction
domain and explicitly demonstrate that the current unrestricted
direct paths remain an integration blocker. No claim that the
witness enforces actual append/reserve/resume globally. Do not
silently substitute wrapper-only checks for real enforcement.
Two candidate retirement intents must serialize against one original
lifecycle revision; fail before write/rollback and lost ACK after
commit/reopen must preserve exactly one outcome and original turns.
No automatic retry/activate. Use metadata-only checks, SQL authorizer
or equivalent audit of no body/title access during retirement, exact
unchanged conversation rows and independent read-only recovery.
All actual authority/action/release flags remain false.

Request Mind/Security/Heart ACCEPT or REVISE this exact proposed
ownership, record, writer-path limitation and scope, followed by
Nurse exact R7c-b decision. If no mapping owner or exclusive fixture
transaction custody can be agreed, HOLD. Real writer integration,
actual live freeze/settlement, protected producer and dormant
publication remain separate later scope.
