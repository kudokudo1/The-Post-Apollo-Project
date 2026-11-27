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

UI1/2 retain one unified Tree-first conversation/member surface per R7h,
with optional presentation-only filters, existing 184/148/hidden compact
rail and accepted neutral Tree glyph. Member
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

## R7f // Durable source and custody feasibility (design only)

Nurse #2161 comment 7179545956 approves this bounded comparison, not
a source selection. Inventory 7179482880 and owner dispositions:
UI1 7179486984, UI2 7179493060, Heart 7179502122, Mind 7179503811,
Spirit 7179508274. Main at intake db49916c; R7e is integrated.
Neither candidate below has an actual qualified issuer or complete
membership source. No schema, private data, API or executable change.

### Existing evidence and limits

| Actual source at intake | What exists | Why it cannot issue R7e |
| --- | --- | --- |
| B6r1 b7fdcfc5, TaskContext | Frozen principal/Tree/optional Clone/task/execution/generation/origin reference | No durable creator, enumeration, independent revision or authority. |
| B1 d1533f15, sessions and turns | SQLite conversation and revision; _write uses BEGIN IMMEDIATE, rejects nesting | No member/Assignment lifecycle mapping, independent custody or complete roster. |
| B3 c5dbbc29, reserve/commit | Exact attempt and user/reply lineage, atomic conversation commit | Reservation is not provider admission, member creation or authoritative currentness. |
| R7c ef44829b, fixed-public transaction fixture | One Cherry slot; ACTIVE/PENDING/WINTER and exact recovery | Literal fixture, not general membership or protected lifecycle issuer. |
| I6 dcae58df, process diagnostic | Bounded selected PID/cgroup correlation | Not complete process membership or canonical Colony lineage. |
| Historical original task/session storage | Original active/dormant continuity semantics | Missing/skipped YAML and binding slots cannot prove completeness or current custody. |

Connections' existing storage-independent authority boundary
(9b541eaa) deliberately refuses protected operations; its separate
Forest-purpose custodian RFC (e32e0a8f) leaves actual enrollment,
original installed producer, DB opener, recipient channel and independent
rollback/currentness custody unresolved. Neither Identity keys nor
local fixtures can be reused as a Forest-purpose issuer. Spirit owns
the protected seam and F1–F6 coordination; Runtime does not supply it.

### Candidate/evidence matrix (no selection)

| Requirement | A: one owner-approved durable lifecycle/member/Assignment transaction domain | B: separate durable source with independently reviewed reconciliation/fencing |
| --- | --- | --- |
| Actual owner, issuer and issuance path | Candidate Runtime-owned lifecycle writer co-designed with Mind for continuity; independently authorized installed writer/opener and issuer not identified. Existing B1/B3 transaction seam is evidence to investigate, not the selected database. | Runtime retains membership semantics; actual independent persistence owner/issuer/transport not identified. Requires named authorized source and original writer custody, not a second guessed registry. |
| Original creation, replacement and retirement | An agreed writer must atomically bind original member address, lifetime and exact Assignment to its lifecycle/continuity mapping; freeze, terminal settlement and retirement must preserve original identity and separate conversation revision. No such general writer exists. | Each source must establish exact original identity and operation lineage. Durable reconciliation must serialize conflicting transitions and settle original outcome before publishing; neither source can declare completion from the other's optimistic response. No such protocol exists. |
| Snapshot and completeness | A consistent read in the approved domain must bind complete membership and Assignment relations to one immutable revision and exact lifetime; all writers must advance it atomically. Separate independent custody must prove currentness and rollback resistance. No current roster revision exists. | Obtain independently pinned revisions from each required source under a proven common fence or equivalent consistency contract. Inconsistent, pending, missing or independently unverified source is unavailable; no join of unrelated latest rows. No common fence or recovery proof exists. |
| Restart, replacement, lost ACK and rollback | Persist original transition/outcome and lifecycle generation; prove current independent floor on restart before exposing data. An older valid database image, equal-value alias or reused process cannot reestablish a retired lifetime. | Durable original operation identity and independently current source heads must survive interruption, rollback or replacement; recovery reads exact outcome, does not replay a write or pick newest by timestamp. Pending split outcomes stay held. |
| B1/B3 writer compatibility | One actual transaction boundary must enforce lifecycle mapping before title/body access or new work without nested _write; preserve B3 original admitted settlement and atomic reply/session/attempt update. | Same B1/B3 invariants apply; an external check before SQL is insufficient. A separately reviewed durable fence must prevent conflicting writers from progressing between source check and mutation. No cross-store atomicity assumption. |
| Disclosure and independent currentness | Shared SQL does not authenticate requester/recipient or serialize external delivery and revocation. Independent prequery and final effect fence remain required. | Same requirements plus independent cross-source currentness at delivery; loss of any required evidence refuses output. |
| Feasibility disposition | Preferred investigation because R7c/R7d already require one coherent lifecycle/continuity boundary; actual storage and protected custody remain unproven. | Alternative only if separation is justified by actual owner/custody constraints and durable fencing/recovery is demonstrable. No existing qualified candidate established. |

### Writer and projection separation

R7d identifies actual B1 create/append/state and B3 reserve bypasses.
B1 _owned can read a title; B3 _reserve reads M2 or legacy bodies before
the RESERVED insert. Any eventual lifecycle-aware mode must independently
resolve original mapping before those reads and check the actual writer
transaction before mutation. R5 start_next/reopen and B4a generate may
not bypass it. The original B3 admitted attempt alone may settle its
exact operation and lineage; never treat RESERVED as admission. Do not
pause, delete or rekey B1 to indicate Winter, and do not attach a new
generation to an old grant. Preserve B3's existing reply, revision and
attempt atomic unit. SQL serialization is not a provider send fence:
B2's actual request effect and independent terminal receipt remain
separate protected boundaries. Do not hold a SQL transaction across
network IO as a substitute for that proof.

For either candidate, the R7e owner projection must:

1. Resolve the original principal, Tree, member (when required),
   requester/recipient, purpose and view incarnation independently;
   authorize enumeration before querying even metadata.
2. Obtain a complete, immutable, independently current scoped source
   snapshot with original lifetimes and revision; no conversation
   body/title/history access, B3 reserve, cache admission or mutation.
3. Apply independent row, alias, lineage, role, season, completeness,
   count and action disclosure before assembly/serialization. No raw
   identities, hidden counts, ordinal gaps or unapproved reason signal.
4. At delivery, require independently current source, recipient/view and
   policy under a separately approved effect/revocation fence. If revoke
   wins, withhold; if an effect wins, revoke cannot be acknowledged as
   complete until its permitted original outcome is independently
   accounted for. A callback, local comparison or valid old signature
   cannot prove this ordering. Unknown remains HOLD.
5. Distinguish authorized complete-empty from partial, refused, missing
   and unavailable; expose distinctions only when authorized. Withdraw
   only the exact original view on stale/lost evidence; old callbacks
   cannot clear or repopulate replacements. Restart never resurrects a
   prior alias or selection. No automatic action, history or restoration.

### Evidence required before a candidate can be selected

- Named owner and independently enrolled Forest-purpose source/issuer,
  original installed writer/opener and recipient channel; no same-UID,
  fixture, Identity-purpose credential or local SQL as authority.
- Actual creation/association/replacement/retirement writer coverage,
  including concurrent claim and pending retirement, exact admitted
  attempt settlement, and independent proof of scope completeness.
- Original snapshot revision/lifetime and protected currentness across
  restart, rollback and ABA (old equal-value record reappearing);
  interrupted transaction/lost ACK exact outcome and no replay.
- For B, explicit multi-source serialization, durable recovery, split
  outcome refusal and proof a stale source cannot authorize a writer
  or delivery. Otherwise retain HOLD rather than assert atomicity.
- Independently reviewed deny-before-query and final effect ordering;
  revoked, wrong scope, hidden metadata, partial snapshot, lost source
  and replacement-view negative acceptance cases per R7e.
- Heart resource/attempt/H2 custody remains independent; no physical
  resource credit from a roster. Mind history, cache and retrieval
  remain separately authorized. UI1/2 retain the unified Tree-first
  surface per R7h, with neutral unavailable roster/chat coverage until
  independently qualified sources are approved.

### Decision requested

No existing store meets the full contract on inspected evidence.
Request owner and Nurse exact design review of this comparison. A is
a candidate for further architecture selection, not an approval to use
B1 or to add a table. B requires a demonstrated need and separately
approved fence/custody design. If no candidate meets the requirements,
seek a new bounded architecture decision with the actual owner and
Connections before proposing a writer, schema, migration or UI producer.
Native execution, protected operations and production remain HOLD.


## R7h // Persistent member identity, chat binding and execution succession

Design only. Operator unified Forest vision #2161 7202168479,
development direction 7204485179 and Nurse reconciliation 7204663398.
Runtime 7202378795/7204270135/7204354166; Heart 7204297064,
Mind 7204287316, Spirit 7204264385, UI1 7204259049, UI2 7204310531.
Supersedes only the two former default/exclusive CHATS presentation
assumptions in R7e/f. All existing R7a-g lifecycle, source permission,
original custody and uncertainty rules remain. See
[R7g source custody](RUNTIME_LIFECYCLE_WRITER_BOUNDARY_R7D.md).
A/B transaction domain and actual independent opener/custodian remain
unselected. No schema, registry, issuer, producer or executable change.

### Original recovery and separate identities

Frozen original 28895aaf: Colony architecture checkpoint 0d15621d
distinguishes shared durable Tree identity, knowledge and capabilities
from each presence's active Task, conversation, Workshop/Ready rack
and runtime state. Original colony/identity.py 849a4378 and
runtime/session_identity.py 64e97968 distinguish semantic execution
context and context+model binding from adapter/provider session IDs.
runtime/conversation_continuity.py 39d2a20b preserves completed public
exchanges by execution context and Task, not hidden reasoning, tool
replay, in-flight turns or provider KV. Recover the distinctions, not
a caller-selected root or implicit transfer of history.

Current B1 d1533f15 stores session_id, owner_key, tree_key, title,
state and revision and ordered turns. It has no authoritative member
binding. B6 TaskContext b7fdcfc5 has optional clone_key and exact
task/context/generation/origin but is a reference, not a registry.
R5/R6b disposable reopen and history evidence is not persistent
member succession or production restart evidence. R7e historical
Tree + execution_context_id address remains a lineage reference;
the actual owner must establish stable member identity independently
of each replaceable execution incarnation. Do not mint a second ID
merely for presentation or reinterpret B6 fields as issuer evidence.

| Concept | Required separation (not a storage or wire schema) |
| --- | --- |
| Tree / Colony | Canonical owner and Tree identity; base and Clone presences share durable Tree ownership, no duplicate independent intelligence identity. |
| Member / Clone | Stable independently resolved member identity and lineage. Role, Assignment, logical home and current execution are distinct. A dormant member can exist with no live process or chat. |
| Display name / number | Mutable user name takes precedence over owner-issued stable sequential default Clone number when no name exists. Neither is an identity, permission, membership count or process. |
| Chat | Durable conversation identity, original authorship/turn lineage, independent revision and authorized history; no inferred member from B1 Tree or OPEN state. |
| Binding | Candidate versioned member/chat relation with independently current old/new scope; no selected one-to-one or many-to-many persistence/cardinality. |
| Assignment / home | Exact assigned work and logical tool/widget/environment reference, independently current TaskContext and origin. Home does not imply host/PID, active state or access. |
| Execution / effect | Exact original Task/context/generation, execution incarnation, operation/attempt, frozen model binding/settings and H11/H2 claim; distinct provider session/process and actual external effect. |
| View / recipient | Authorized source revision, recipient, view lifetime, purpose and action. Selecting a row is not a grant or change to the composer target. |

The base Tree name is the primary public heading in the disconnected
UI design; real names, aliases, default numbers, binding, role, home,
task, season, count and completeness require independently authorized
per-field disclosure before enumeration. No client-derived numbering
or hidden gaps/counts. Name uniqueness, numbering namespace, allocation
and reuse are open owner/operator decisions; names need not define
identity. A user-assigned name does not change original authorship,
member identity, chat binding, permissions or execution incarnation.

### Versioned association and original writer order

The unified view can present a permitted member with related chats,
a member without a chat or a standalone chat with no qualified
association. No assumed cardinality or automatic membership creation.
Multiple relations do not imply multiple current send recipients:
each actual submission independently binds one exact authorized
original operation, chat revision, Task/member and recipient. Separate
authorized tasks may run concurrently; conflicting writes to the
same conversation require original writer ordering, not last-writer-
wins. Do not change existing B1 revision/attempt semantics here.

1. Independently resolve and authorize the exact original owner,
   Tree/member/chat, source and intended metadata mutation or
   reassignment before reading protected data. A rename, home change,
   Assignment change, explicit bind/unbind/rebind, view selection
   and send are distinct intents.
2. For rename or association mutation, pin current original metadata
   and relation revision, exact old and proposed new scope, recipient
   and original outstanding effect references. Compare and serialize
   at the actual authorized durable writer; stale/conflicting/unknown
   observations refuse. Actual transaction domain is not selected.
3. Preserve historical authorship, chat ID, original turns and committed
   conversation revision. A successful reassignment changes the
   prospective authorized relationship only, not prior Tasks, effects,
   histories, retained Leaves or authorization. No automatic draft,
   cache, credential, live session or grant transfer.
4. Existing admitted original operations settle only through the exact
   original R7d/g custody boundary. Unknown effect/receipt/terminal
   remains attached to the original; no inferred rollback, re-send,
   replacement claim or automatic release. A conflicting rebind or
   progression must HOLD if original custody cannot be preserved.
5. Publish only independently permitted current metadata after original
   mutation outcome is known and the view/recipient rechecked. Unknown
   write outcome is not success; reconcile exact original operation
   rather than retry as a new mutation. A stale callback cannot update
   replacement selection, draft, source or view.

### Renewal and shared continuity

The persistent chat and member can outlive execution. Detaching a
Bark, filtering, closing a view or changing a display name does not
retire the member or stop separately authorized background work.
Preserve the existing UI close/draft behavior; no durable draft
storage is claimed or introduced.

Before replacing a held execution, reconcile exact original terminal,
quiescence, later attributable resource accounting (Heart) and
independently authorized effect settlement (Spirit/Connections).
Retain original custody if any is unknown; no retry/replay, new
admission or inferred Winter. A separately eligible new Task or
execution must establish its own current context, binding/settings,
claim, policy, source/use and recipient; it cannot inherit the old
provider session, KV, lease, in-flight work or grant. Preserve exact
committed B1 history and prior authorship. Historical continuation
references and independently authorized Mind-derived context are
different; regenerate the latter for the new eligible workload and
recipient as needed, not by silently rewriting original history.
Model-form handoff and H16 temporary reasoning consumption are
separate from execution renewal and must retain original operation
identity and one-use settlement.

Same-Tree coordination can use authorized versioned durable knowledge
and shared Tree capability/Workshop ownership under scoped standing
policy. No wholesale transcript or live context broadcast, implicit
active Workshop/tool activation, role-specific data transfer, resource
credit or automatic permission from shared Tree identity. Mind owns
Leaf provenance, bounded retrieval and refinement; authorized lossy
working-context stewardship is not destruction of history. Spirit
owns distinct source/use/mutation/egress/revoke and destruction scope.
Cross-Tree Mycelium remains independently authorized. No hidden
retention or recurrence check contrary to a completed authorized
destruction scope, no claim to erase unknown external copies.

UI1/UI2 own the unified Tree-first rail, future ALL/CHATS/CLONES
visibility filters and explicit composer target; filters, row
navigation and rename do not silently retarget the composer. S4-U1
disconnected presentation remains separate and does not provide a
roster, count, binding or active execution. Unknown/partial/denied
coverage is not complete-empty; only independently authorized
current completeness may support an empty/count assertion. No
inferred membership, season or running status from OPEN/PAUSED,
hostConnected, process observations, model inventory or resource
reservation. Retain R7e pre-enumeration and final delivery fences.

### Negative acceptance matrix (future implementation criteria only)

| Case | Required outcome |
| --- | --- |
| Same member renamed / same display name on different members | Preserve immutable identity and original history; labels never transfer scope or selection. |
| No user name / hidden member or number | Only independently issued permitted default label; no client numbering, hidden ordinal/count leak or inferred empty. |
| Member without chat / standalone chat / multiple associations | No fabricated counterpart or assumed cardinality; exact authorized send target remains separate. |
| Rebind with stale revision, competing mutation, wrong Tree/member/recipient or unknown write outcome | Refuse or retain exact original pending effect; no implicit retarget, duplicate write or permission transfer. |
| Rebind with committed history or old derived context | Preserve original authorship/revision; new scope needs independent read/use and recipient; no automatic copy/cache inheritance. |
| Rebind/renewal while old effect, terminal or accounting unknown | Original remains held; no conflicting progression, replay, release or replacement claim. |
| Detached background Task or hidden rail | No Task cancellation, member retirement, resource release or new attachment inferred. |
| New incarnation after qualified original settlement | Same authorized durable member/chat and committed history; fresh exact execution, input, policy, recipient and claim independently required. |
| Same-Tree shared knowledge vs foreign Tree or role-restricted data | Only currently permitted scoped coordination; Mycelium/cross-Tree separately authorized; no automatic transcript or capability grant. |
| Stale/withdrawn projection, filter change or renamed row | Clear affected presentation only; no new read/send, automatic composer target, history mutation or durable deletion. |
| Missing source/partial roster or local session OPEN | Neutral unavailable coverage, never false count, membership, season or complete-empty. |

Open decisions: actual stable identity and versioned association
custodian; relation cardinality and allowed reassignment semantics;
name/number namespace and allocation/reuse; source completeness and
per-field policy; actual A/B transaction and old-writer recovery;
original terminal/effect and admission boundaries. Operator/owners
must settle these with actual source evidence before implementing
a protected writer or roster. No new API, schema, data migration,
registry, opener, issuer, test, UI, provider or native operation
in R7h. Exact source review/CI at handoff; operator integration
separate. Native/protected/production HOLD.


## R7i // Multi-author room ordering and directed response custody (design)

Operator S5 clarification #2161 7215166665/7215453268, integrated UI2
#2999, Nurse 7215502409; Runtime 7215535828, UI1 7215538179,
Spirit 7215553666 (candidate #3001), UI2 7215555784,
Mind 7215556125, Heart 7215569936. Preserve R7h persistent member,
original history, execution succession and unknown-effect custody.
The earlier one-prospective-writer recommendation was not a decision:
a room may have multiple independently authorized authors across
Trees/Clones. Message append serialization is not sole-speaker
assignment, response admission, or ownership of external effects.
No actual A/B transaction topology or policy defaults selected.

### Existing implementation and gap

Main 916ebb03: B1 d1533f15 lines 23-45 stores one owner/Tree per
session and ordered turns with role/provider/model, no authenticated
member author or audience; lines 186-213 serialize append at exact
revision, lines 215-229 read bodies by owner/session. B3 c5dbbc29
lines 40-58 restrict one attempt per (session,user_turn) and one
RESERVED per session; lines 157-195 select latest user and bounded
history; lines 303-325 require unchanged revision and original user
still last at commit. Thus merely removing one-live index cannot
support a second reply to the same trigger. M2 1085bc56 refuses Clone
and selects one Tree's contiguous suffix at exact revision; filtering
after fetching private bodies or exposing ordinal gaps is not a
qualified room history. R3 291dbaa4 keeps OperationRef in memory, one
generator and STOP. H1 62dc22ec also refuses Clone/background.
B2 transport carries user/assistant roles, not stable author identity.
Retain all existing refusal boundaries; current local transaction
and fixture evidence do not establish real room or audience custody.

### Distinct logical records (not a schema)

| Record | Required invariant |
| --- | --- |
| Room / durable conversation | Stable room/chat identity independent of selected Tree, current participants and execution. Old B1 Tree/owner remain original provenance, not universal room ownership. |
| Membership / policy | Stable authenticated member and Tree, independently current join/leave incarnation, room ceiling and member-specific revision. Membership is not history, resource or execution access. |
| Message | Immutable original ID, author, order, causal reference and exact content/version; separately permitted audience and attachments. A label/model name is not authorship. |
| Address / intent | Deliberate qualified target(s) and original request, independent of readers. Mention, quotation, proposal, assignment and verified implementation authorization differ. |
| Response job | Original room/trigger, intended member, purpose and bounded causal root; independent job identity, current policy, input and claim. Multiple jobs may cite one trigger. |
| External effect / assignment | Exact original operator grant, approved revision, delegation, receiving owner/Task, actual target/action, claim and terminal outcome; separate from reply and delivery. |

The room's mode is a ceiling; member mode and suggestion preference
restrict it. The S5 Maple/Cedar/DOC1/DOC2 table is illustrative, not a
roster or default. No implicit response from observation, mere mention,
quote or proposal. A one-shot invitation to an observer remains an
open policy choice; no silent mode override. Proposal-only contribution
still requires permitted input and actual model/resource admission.
Cross-Tree audience is separately qualified; never broadcast private
Leaves, Task state, transcripts or tools through shared membership.

### Response admission, append and original recovery

1. Resolve original message/intent and independently authorized
   recipients before protected enumeration. Freeze exact member,
   membership and policy revisions and permitted trigger; establish
   bounded root, per-member/room/host work budgets and causal limits.
   Names or free-text @ tokens alone cannot create jobs. Replayed
   addressing or relay must resolve the same original job, not mint a
   new attempt. Each distinct eligible response has independent
   identity even when the same user message triggered it.
2. Evaluate serialized response admission per room first as a
   conservative candidate, not a selected global scheduler or sole
   speaker. A queue entry is not execution authority. Revalidate
   membership, intent, current policy, input eligibility and actual
   Heart claim before assembling/dispatching each job. Nonconflicting
   independently authorized background assignments may continue under
   separate claims. Host-wide capacity and causal/cadence ceilings are
   independent of room queue; no implicit fan-out or recursion.
3. Pin exact eligible input snapshot and provider recipient before
   actual send; keep the causal trigger distinct from the latest
   message. The snapshot and append-head revision are distinct
   concepts, not permission to ignore drift. If another message
   arrives, resolve actual currentness rules: hold invalidated input,
   never silently rebase a prepared request or replay an inference.
   Parallel computation remains a later candidate needing qualified
   snapshot semantics and independent claims, not approved here.
4. At the actual durable writer, serialize message append and compare
   exact original job, current qualified author/membership, permitted
   input and append precondition. Record immutable message, order and
   local original job settlement atomically or preserve unknown
   original custody. Duplicate completion must reconcile original
   outcome rather than insert another message. Local append, delivery
   to each recipient and external tool effect are different outcomes.
   No message or hidden ordinal/count is published without current
   independently qualified audience. Lost receipt is not success,
   rollback, external cancellation or permission to retry.
5. A task handoff uses independently verified original operator grant,
   exact approved revision, delegation eligibility, current receiving
   role/Task, workspace/action/target, scope and budget. Standing
   authorization may cover a bounded handoff without repeated consent;
   the sender's statement or a summary does not grant execution.
   Conflicting actual effects serialize at their actual target owner,
   not merely at the room ledger. Nonconflicting effects still need
   independent permission/claim and original custody. A posted result
   needs its own outcome and recipient evidence.
6. Leave, rebind, mode changes, STOP and revocation deny affected new
   admission/delivery and clear stale presentation where required;
   preserve outstanding original effects and accounting until exact
   settlement. No implicit retarget, history rewrite, grant transfer,
   cancellation of unrelated work or resource release. A newly joined
   member's earlier-message visibility requires independent policy;
   no automatic history backfill or inferred completeness.

UI1/UI2 own the actual layout, explicit room/target, draft and mode
controls, and authorized status. Keep addressees distinct from readers
and effect owner; no invented queued/speaking status or hidden counts.
Mind owns eligible recipient-specific history/Leaf/approval context;
Spirit/Connections own authority, audience, revocation and source
custody; Heart owns actual capacity, claim and terminal accounting.
Runtime owns original ordering and recovery, not an additional issuer.

### Future negative acceptance matrix

| Case | Required result |
| --- | --- |
| Two eligible authors respond to one user trigger | Distinct original jobs, each at most one committed message; durable order, not duplicate rejection solely due to common trigger. |
| Duplicate job delivery or completion after lost acknowledgement | Reconcile exact original outcome; no new provider send or second message. |
| New append after original input preparation | Requalify applicable snapshot/currentness; no implicit refresh/rebase, replay or guessed success. |
| Quoted/negated mention, proposal or observer without permitted invitation | No inferred addressed job, model admission or tool effect. |
| Duplicate display names or stale addressed member | Refuse ambiguous/stale target; never choose first match or replacement. |
| Join/leave/mode/revoke during queue or response | No affected new admission or delivery; retain original outstanding effect, no automatic release. |
| Partial recipient history or attachment eligibility | No body enumeration outside scope, hidden gap/count or implied full history; no automatic backfill. |
| Cross-Tree room | Separate authorized projections; no private Task/Leaf broadcast or inherited capability. |
| Accepted design without implementation grant, or widened relay | No tool effect; require independently qualified exact delegated scope. |
| Covered delegated assignment, same target conflict | Separate original claim; actual target custodian serializes conflicting effects. |
| Independent eligible targets | Separate capacity, permission and original effect claims; no room-wide sole-author lock. |
| Causal loop, budget exhausted, STOP or unknown terminal | Hold affected admission; no automatic response/dispatch or inferred settlement. |

Open: authentic room/member/author source and join/history policy;
room versus member preference lifetime; actual durable job allocation,
deduplication, append preconditions and ordering; causal/budget limits
and scheduler scope; original operation/target/receipt custody;
approved A/B transaction domain, opener, migration/legacy writers
and recovery. Candidate evaluation only. No new schema, queue, API,
registry, test, issuer, permission, UI, model/tool invocation or native
operation in this slice. Exact completed-source owner/Nurse review
and existing CI; operator integration separate. Production HOLD.
