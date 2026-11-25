# R7d-a // Lifecycle writer-boundary integration proposal

DOC2F Runtime. Main 1495675707a55c8aabc14c7dd09ea8d41ef8d67e.
Nurse #2808 comment 7171053609 authorizes preparation of actual writer
coverage and next integration contract, NOT actual lifecycle mutation.
R7c-b fixture integrated blob ef44829b, cc072a1c raw 139417239006
11+12 tests PASS. Mind/Heart scoped acceptance; Security implementation
review pending. No production schema, provider or protected authority.

## Concrete writer gaps and target boundaries

Existing B1 d1533f15 _write BEGIN IMMEDIATE serializes SQLite writers,
not process/network effects. B1 create_session INSERT creates an OPEN
session without task binding; append_turn (both roles) and set_state
read _owned including title and then write; they do not know a task
slot or lifecycle revision. A direct assistant append must not bypass
the B3 exact terminal writer. Standalone set_state PAUSED is not Winter.

B3 c5dbbc29 _reserve performs M2 body read or legacy body read before
the RESERVED INSERT within _write. To prevent new work, lifecycle check
must precede either read as well as reserve, not merely the INSERT.
B3 _commit checks current OPEN/revision and RESERVED lineage; _abort
updates RESERVED; _commit_fenced invokes real _commit then separately
terminal receipt. Neither distinguishes lifecycle intent. B3 exchange
yields RESERVED then checks context/STOP and enters lazy B2 transport.
A DB reservation is NOT a durable provider admission or send fence.
B2 db572336 HTTPConnection.request is first possible prompt-bearing
effect. A check before generator creation alone cannot prevent a send
after freeze. Protected actual send fence and independent settlement
remain separately owned, not supplied by R7c.

R5 7dba584a start_next appends before R3 exchange, reopen_journal
reopens a disposable conversation journal; B4a 5948497e generate calls
B3 directly. These entry points must not create alternate bypass paths.
B1 read history/list, R5 REOPEN and M2 snapshots are not claims,
retirement or permission. UI/history/cache attachment invalidation is
separate from durable conversation revision.

## Scope and transition rule proposed for review

Keep existing Runtime-owned lifecycle mapping and B1/B3 transaction
domain; no second task registry, daemon, protected writer or schema
migration. A future real lifecycle-aware host must be an explicitly
selected mode with independently held exact owner/Tree/Clone/task/
execution context/generation/slot/session/lifecycle revision; no
caller-chosen bypass flag, no fallback to legacy if mapping missing.
Legacy fixed-public B1/B3 fixture tests must remain compatible, not
presented as global enforcement. Unknown or mismatched mapping HOLD.

- New claim/create, direct append (both roles), resume/set_state and
  reserve require exact active lifecycle identity and current revision
  inside their actual write transaction, before any body/title read
  or mutation. Distinguish task active-slot claim from session creation.
  Unmapped legacy session must not obtain a lifecycle-aware claim.
- Pending retirement wins against new conflicting work, including
  reserved-but-not-admitted sends. Any already-admitted original attempt
  must remain eligible to settle only its exact original operation,
  attempt, binding/settings, user/reply lineage and original effect;
  current B1 OPEN/revision checks remain. No new attempt, rekey or
  fallback. Do not pause B1 early or abort on mere EOF.
- DB-local fence does not serialize network send/revoke. Independently
  protected source-use before body and final serialized recipient/
  payload effect fence at actual B2 send remain Security-owned. No
  Boolean flag, callback alone, SQL lock across network, or modeled
  R7c result substitutes for that boundary. Ambiguous admission/send
  retains original pending identity, no retry or cleanup-based release.
- Final retirement only with separately current terminal, quiescence,
  Heart accounting and Security settlement; preserve original receipt
  and continuity atomically in approved store. R7c fixture does not
  implement this actual authority. On loss, read exact original outcome,
  no automatic replay. History/cache/view old scope retired explicitly
  by owners; new Spring review/claim/admission is separate.

## First proposed R7d-b scope (await exact owner/Nurse approval)

Test-only actual-writer boundary coverage on the existing disposable
R7c B1/B3 fixture, not installed guards. Map actual direct writer paths
and explicitly exercise negative bypass evidence before introducing a
guard. Include B1 append user and assistant, state change/resume,
create/activation mismatch; B3 legacy and M2 reserve, exact original
terminal vs conflicting attempt and reserved-before-send seam with
fake provider only. Distinguish actual currently bypassable legacy
calls from desired guarded behavior; do not make a test pass by calling
a wrapper instead of the direct path. No claim an already-admitted
attempt exists in the existing R7c committed fixture; a separate
owner-approved synthetic pending-reserved scenario would be needed
to test original terminal settlement. Preserve all existing R7c tests.
If a later guarded actual writer fixture is agreed, define exact
admission record and transaction check before code, not a SQL trigger
that conflates RESERVED with admission. No B1/B3 source change or
production global fence in R7d-b proposal.

## Distributed seasonal identity (operator clarification)

UI2 #2814 merged and #7171079179 operator-confirmed direction: show
runtime seasonal status at each normal Tree, Colony/chat, Clone/worker
and Assignment/task location, not a separate global dormant destination.
Frozen original doctrine 15e4e11a lines64–139: Spring Cleaning FIRST,
Summer Growing, Fall Shedding, Winter Dormant; independent task and
component state. Separate Forest-LANGUAGE b70d23ee lines13158–13186
development-focus seasons have different meanings; do not conflate.

B6 TaskContext b7fdcfc5 carries principal_key, tree_key, optional
clone_key, task_id, execution_context_id, generation, origin. It
does not prove deployed Clone/worker, Colony ownership, a parent
graph or season. B1 session_id is conversation identity, not Colony
lifecycle truth. Tree/Clone/Colony/Assignment require independently
resolved exact entity identity and authoritative per-entity current
season; no inheritance or aggregation. Real producers absent; UNKNOWN.
R7c ACTIVE/PENDING/WINTER fixture is transaction state, not universal
season enum: no automatic ACTIVE→SUMMER or PENDING→FALL mapping,
fixture WINTER is not a live indicator. No season from B1 PAUSED,
cache, model residency, visibility or timestamp. Task slot release
is not H2 or RAM release. Actual dormant catalog publication needs
separate lifecycle and disclosure approval. Preserve contextual R1/R2.
No QML, producer, new seasonal schema or entity mapping implemented.

## Required review

Mind: exact B1 continuity and pre-body boundary, cache/history lifecycle
invalidation, actual writer coverage. Security: distinct original
admission/final-send/terminal/receipt fence, no positive protected
producer or global authority; Heart: exact old attempt/resource
custody, no release or new admission inference. UI1/UI2: per-entity
normal-location indicators and no legacy inference. Nurse2F:
exact R7d-b coverage scope and separate later guard integration review.
No executable changes, host actions, inference or production authority.
