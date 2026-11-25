# Runtime original lifecycle recovery // R7a proposal

PATIENT: The-Post-Apollo-Project · Forest Integration · DOC2F Runtime.
Development ACTIVE; native model, protected data and production HOLD.
Source-only owner coordination; not a frozen contract or permission to act.

## Evidence and ownership

Original read-only source: kudokudo1/The-Post-Apollo-Forest-Project
at 28895aafdddb07cf402f1e75574eea1ee79a516d, under
raw-import/2026-09-22-transfer/The-Forest/bristlecone.
Assignment #2161 comment 7160677299; succession 7161256592.
Target main 52fb321a246632366d49902040d5b1298f63309f.
R6b #2696 ec9ca309 remains separate and unmodified. Frozen R6a R1
is CI-only and cannot transport lifecycle operations.

| Original mechanism (source blob) | Current evidence (source blob) | Recover / do not infer |
| --- | --- | --- |
| task_session.py a2458c4e: end_task 6227+, lock, durable Winter record before clearing active slot | B1 session_journal_v0.py d1533f15 set_state 231+ checks owner/revision/time; R5 7dba584a close/reopen | Recover durable same-task retirement with no loss or double activation. PAUSED/ARCHIVED and close do not prove Winter or model release. |
| list_winter_tasks 4724+, load_winter_task 6130+ | B1 sessions/turns and M4 public history | Discover scoped metadata separately from content/activation. M4 OPEN fixture is not a Winter registry. |
| begin_spring_cleaning 4976+: empty active slot, durable worksheet, write active then cleanup dormant record | R5b reopen keeps same local journal; UI2 #2690 proposed synthetic review | Separate actual dormant selection, task claim and worksheet from review display. No auto activation, deletion or adoption of historical runtime IDs. |
| plan_spring_restoration 5788+, record_spring_restoration_decision 5231+, apply_spring_restoration 2712+, complete_spring_cleaning 3844+ | B1 revision + R3 events, no equivalent plan revision in reviewed seams | Read-only plan, explicit intent, authorized apply, independently verified completion; independent plan revision and currentness. |
| session_identity.py 64e97968 and session_store.py fff28521: execution context + binding, adapter and provider session ID distinct | I2 model_binding_i2.py e8a9a5d1; R3 runtime_events_r3.py 291dbaa4 OperationRef; B3 turn_bridge_b3.py c5dbbc29 | Preserve exact task/context/binding/attempt distinction; fresh provider session on uncertain old lineage; no old credentials or live session assumed. |
| model_residency.py a19a754c: compatible binding can share weights, not execution state | Heart H2 heart_resource_custody_h2.py 55100576 fixture-only custody | Separate execution quiescence from retained shared weights and actual release. Never unload another task's weights or credit unobserved memory. |
| conversation_continuity.py 39d2a20b; turn_composition.py 12c472b8: completed exchanges and bounded reference composition | B3 atomic attempt/context and Mind M2/M4, M7 proposals #2683/#2691 | Reuse committed continuity and exact revision, Mind owns selection/assembly. No inherited authority or private context via restored bindings. |
| task_session.py guarded binding/handoff 8284+, 8406+, 8660+, 9254+, 10565+ | R2/R3 one-shot STOP/commit arbitration; B4d recovery_inspect_b4d.py e4f4a537 | No automatic retry or optimistic rollback. B4d local RESERVED/ABORTED/COMMITTED is not C5 settlement or provider quiescence. |

Historical file duplication favored recoverability after interruption.
Do not copy the YAML active-slot/Winter-file implementation, best-effort
provider teardown or old resource assumptions. Prefer an atomic durable
transition in existing owned storage if ownership/schema review establishes
it is appropriate; no second journal or daemon. A duplicate or contradictory
recovery record is HOLD, not permission to choose the newest timestamp.

## Proposed lifecycle invariants (for owner agreement)

These are conceptual states, not a new wire or database schema.

1. Explicit retirement intent binds independently resolved principal, Tree,
   Task/execution context and current task revision. Freeze new dispatch
   before resolving the current attempt. A stale intent cannot retire a
   replacement task. Preserve committed conversation and its revision.
2. Resolve existing B3 attempt locally via B4d. RESERVED, ambiguous receipt,
   lost worker or contradictory identity remains UNKNOWN_HOLD. STOP request
   or client EOF is not terminal proof; do not auto-abort after commit entry.
3. Verify exact provider/runner terminal outcome and no remaining active work
   using independently attributable evidence. Reconcile H2 custody with
   Heart; an idle shared residency can remain resident only under approved
   accounting. Never interpret retained weights as active task or free RAM.
   Protected authority/settlement requires Security's separate evidence.
4. Only after required terminal, quiescence and custody checks, durably
   retire same task without erasing committed continuity; then acknowledge.
   On ambiguous write outcome, inspect exact persisted identity/revision and
   hold rather than retry. Atomic storage and native evidence are not yet
   implemented or approved. A new activation cannot pass an unresolved
   conflicting retirement.
5. Discover dormant metadata under current authority, no content read or
   resource activation. Selection and review are read-only. Independent
   task identity, view lifetime and plan revision must match; UI2 aliases
   are presentation only. No R6 action or dependency on B1 revision alone.
6. Actual Spring entry requires explicit intent, verified dormant identity,
   exclusive claim and durable worksheet. Plan changes invalidate earlier
   decisions. Retain references as advisory, revalidate Mind context and
   Security permissions, then record choices without executing them.
7. Apply requires exact current plan/decision, Heart admission and Runtime
   enforcement, with new operation identity. No previous provider session,
   reasoning intensity, capability or grant restored from historical state.
   Unknown apply holds; no auto retry. Summer/completion requires separate
   verified applied state, not a successful click or local history read.

## First bounded implementation gate

Propose R7b as an isolated disposable retirement eligibility/transition
witness using existing B1/B3/B4d evidence, after the exact owner contract is
agreed. No provider, no new storage engine, no production or seasonal claim.
Do not edit shared B1/B3 until Mind/Security custody and writer ownership
agree. H2 is a fixture reference, not independently verified release.
Use explicit fixture provenance and all authority/action flags false.

Negative matrix for review: active/RESERVED attempt; STOP-only; local
COMMITTED but provider still running; local ABORTED but unknown settlement;
wrong task/Tree/binding/attempt; stale revision; unknown quiescence;
shared weight residency vs task work; duplicate retirement; interruption
before/after durable commit; conflicting active/dormant evidence; stale
restoration plan/decision; revoked context/authority; failed Heart admission.
Verify no loss of original rows, no duplicate activation or automatic retry,
and no inferred authority. Native provider/host changes need separate approval.

## Owner decisions requested

- Mind: exact task-to-continuity reference, snapshot and plan invalidation;
  whether existing journal can support the lifecycle record without a new
  store, transaction ownership and explicit retrieval boundary.
- Heart: distinguish exact attempt quiescence, release accounting and
  retained compatible residency under H9; no availability credit from STOP.
- Security: current authority and exact terminal/settlement evidence,
  protected writer custody, revocation and unknown outcome handling.
- UI2: prior exact five-row synthetic review ACCEPT unchanged; real plan
  metadata is not yet approved. UI1: no mount or R6 wire change.
- Nurse2F: independent scope review of R7a and approval of bounded R7b
  candidate before executable lifecycle work. Operator acceptance separate.

R6b remains at its independently reviewable head. No code, database,
native runner, existing provider, shared UI, production or host change here.


## R7e proposed Colony/member/Assignment projection contract (design only)

Nurse #2161 comment 7177803007 authorizes this documentation only.
Runtime intake 7177600928, historical audits 7177636155/7177768156;
UI1 7177627698/7177728110, UI2 7177633595, Mind 7177630040,
Heart 7177638539 and Spirit 7177633979 are the agreed design inputs.
No executable source, registry, schema, wire, permission, UI mount or live
operation follows from this document. Production and native execution HOLD.

### Canonical identities and ownership

The frozen original Forest commit 28895aafdddb07cf402f1e75574eea1ee79a516d
member checkpoint (58408002) and colony/identity.py (849a4378) define
one Tree/Colony containing individually addressable execution contexts.
Ortet/Ramet is lineage; Main or another operational responsibility is a
separate property. Neither determines season, residency or permission.
Preserve the historical canonical member address (Tree plus execution
context); distinguish durable member identity from the current execution
lifetime/generation. Do not introduce another identifier merely as an alias.

| Concept | Candidate owner-side reference (not a wire field) |
| --- | --- |
| Tree/Colony | Independently resolved principal and canonical Tree; no separate duplicate Colony identity. |
| Member | Exact canonical Tree, execution_context_id, independently resolved current lifetime/generation; lineage and role separately disclosed. |
| Assignment | Independently resolved member and exact TaskContext task_id, execution_context_id, generation, origin; separate original operation/attempt and task revision where relevant. |
| Runtime binding/session | Separate execution context + binding, adapter/runtime session and residency identities. Not a membership count. |
| Conversation | B1 session_id and tree_key; independent history/current revision. Not an Assignment or member. |
| Presentation | Independently resolved recipient, purpose, source revision and local view incarnation; Bark attachment is not identity or authority. |

Current B6r1 TaskContext (b7fdcfc5) already separates tree_key, optional
clone_key, task_id, execution_context_id, generation and origin. This is
a caller-owned reference, not a member registry; do not reinterpret
clone_key as an authoritative alias or change its contract. M2
(1085bc56) refuses Clone binding. B1 (d1533f15) has no member lineage.
Multiple Barks for the same Assignment must not multiply its identity.
An authorized background Assignment can have no Bark; detach does not
retire a task, change season or clear durable memory.

### Source recovery and hard gap

Original runtime/session_identity.py (64e97968) and session_store.py
(fff28521) describe execution-context/binding slots, including empty
runtime session stores. A dormant member may have no live binding and a
member may have several. Original task_session.py (a2458c4e), start_task
at 2656 and Winter record/list at 4627/4724, stores one active slot and
durable dormant YAML records. The list can return empty when the
directory is absent or silently skip malformed/nonmatching records.
Neither this historical list nor the runtime session store establishes
current independently authorized membership or completeness. Do not
migrate historical data, enumerate private files, reinterpret missing
storage as empty or reuse this behavior as a modern authority source.

Actual durable membership/Assignment registry, persistence and issuer
ownership, generation/revision issuance, source currentness, and
independent Connections custody remain unestablished. Candidate owner
interfaces below are semantic responsibilities, not API names or a
decision to introduce storage:

- Runtime resolves canonical parent/member/Assignment and owns an immutable
  versioned snapshot of its exact independently current source. It must
  demonstrate atomicity or equivalent consistency across membership and
  lifecycle changes, explicit unavailable/partial/refused outcomes, and
  stable lifetime/currentness across replacement. A data source and
  persistence owner must be agreed before any executable proposal.
- Spirit independently resolves requester/recipient and current permission
  for the exact parent, intent, enumeration and disclosure. Source
  completeness is a separate permission; no implicit global roster.
  Actual authorization, delivery fencing and custody remain separate.
- Mind retains history/context ownership and independent retrieval/use
  checks; a view cannot admit a cache or alter B1/H11/H2. Heart retains
  resource/attempt custody; listing, absence and season confer no resource
  credit, admission or release. UI1/2 own layout and contextual interaction,
  not source or authorization. Nurse reviews exact bounded evidence.

### Trusted projection and delivery sequence

1. Independently authenticate requester/recipient and resolve the exact
   principal, Tree, selected member (if required), purpose/intent and view
   incarnation. Do not accept Bark or UI-supplied aliases as authoritative
   identity. Establish current enumeration permission BEFORE querying.
2. Obtain the owner-pinned immutable source snapshot, scope and revision
   under that permission. A partial, failed, refused or lost source is not
   an empty roster. Do not invent an issuer or fall back to fixtures.
3. Inside the trusted owner/Spirit boundary, derive only currently
   authorized rows and independently allowed bounded public aliases,
   lineage/role, season, completeness/count and action metadata BEFORE
   assembly or transmission. No raw source IDs, hidden counts, ordinal
   gaps, private diagnostic detail or full-roster QML filtering. Season
   unavailable/denied on an otherwise authorized row is UNKNOWN. Other
   unavailable fields are omitted; no default lineage/role/season.
4. Recheck independently current policy, recipient, source revision and
   exact view incarnation at serialization/delivery. Changed or unknown
   evidence refuses new payload and retires only the affected original
   visible projection. No stale fallback. Actual protected effect fencing
   and delivery receipts are not established by this design.
5. Stale response/withdrawal/dismissal for another view cannot alter the
   current replacement. Retire old list, selection and review before
   rendering a new scope; no automatic selection on arrival. Preserve
   unrelated chat history/draft, durable records and current memory.

Explicit authorized complete-empty describes only the permitted
projection, not global membership. If completeness is not independently
allowed, return unavailable rather than an empty/global count signal.
Partial/unavailable/refused states stay distinct inside trusted custody;
public exposure of their distinctions must itself be permitted. A
selection reference, if later approved, is scoped/opaque, not a grant.
Subsequent member selection and contextual Cleaning re-resolve exact
identity/currentness and independently authorize the action. Viewing
does not read bodies, claim a Task, enter Spring, activate or restore.

UI1/2 retain CHATS default, explicit Colony rail selection, existing
184/148/hidden compact rail and accepted neutral Tree glyph. Member
lineage/role can occupy an independently disclosed lower line only after
approved source/placement; no Ortet=Main assumption. Contextual Cleaning
needs independently pinned plan and separately approved existing workspace
(minimum 300x160), not a squeezed rail or new window. S1 syntheticOwner
and receive fixture interface cannot become the shipped lifecycle source.
No new rendering or physical hit-target acceptance claimed.

### Negative acceptance matrix for future separate implementation scope

| Case | Required outcome |
| --- | --- |
| Foreign principal/Tree/member/recipient or invalid view | Refuse before source query; no row/body/count disclosure. |
| Same alias, different member lifetime or task generation | Never transfer selection or permission; original identity must match. |
| Duplicate Bark, detached chat, background without Bark | One canonical Assignment; no retirement or exclusion inferred from attachment. |
| Missing store, partial/invalid snapshot, refused enumeration | No invented empty list, fallback or global count. |
| Authorized complete-empty; forbidden completeness | Explicit permitted empty only in first case; unavailable in second. |
| Hidden member/alias/season/action | No hidden row/count/order signal; authorized row with undisclosed season UNKNOWN. |
| Revocation after snapshot, before delivery | Refuse new payload, withdraw exact original projection; no stale metadata. |
| Old revision/new view or stale callback | No repopulation or deletion of replacement; preserve unrelated chat/draft. |
| Selected row or dormant indication | No body read, resource credit, activation or restoration; exact separate action authorization. |
| Unknown/pending lifecycle or missing terminal | No Winter/retirement inference, cache close or settlement. |

The matrix is design acceptance criteria only; no tests, producer,
registry, schema, signer, native source, new UI action or production
authority are introduced here. Request exact Heart/Mind/Spirit/UI1/UI2
compatibility and Nurse independent document review; any implementation
requires new explicitly bounded authorization and actual source evidence.
