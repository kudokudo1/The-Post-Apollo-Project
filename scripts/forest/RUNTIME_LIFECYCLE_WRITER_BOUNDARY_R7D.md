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

## Admitted-original settlement feasibility (design only)

Nurse #2161 7189013536 authorizes this supplement only; Runtime intake
7187656566/7188900285, Heart 7188905278, Mind 7188906015 and Spirit
7188911920. Main d351c035 at intake. R7d-b #2832 and R7d-c #2849
already cover existing direct-writer and separate R5/B4a negative paths.
They are not guards. R7f #2876 technical review closed 7189005120,
with historical review-order exception retained; neither source A nor B
selected. This design does not depend on selecting either.

### Exact original reference and currentness

R7b 566a7116 _scope requires RetirementRef.session_revision equal to
operation.context_ref.expected_revision+1. R7c ef44829b _continuity
requires original COMMITTED and latest user/assistant lineage; its
test setup consumes the exchange before retirement. Neither can
represent an admitted still-running attempt. Preserve both unchanged.

A future separate fixed-public witness would require independently
supplied, immutable, test-only original admission evidence, NOT a
Boolean, RESERVED row, fake STARTED/DELTA or caller grant. Bind:

- Exact original principal/Tree/member execution context and lifetime,
  TaskContext including task, generation and origin, original lifecycle
  revision and active claim, exact OperationRef and H11 AttemptRef,
  original session/user turn, attempt and binding/TransportSettings
  including model/runtime identity and configuration commitment.
- Original modeled admission/effect identity and ordering reference,
  original H2 accounting reference, and distinct retirement intent
  identity/revision. Admission must precede the freeze to qualify for
  original-only settlement; unknown ordering cannot qualify.
- Pre-commit conversation revision r and conditional post-commit r+1
  (only on a successful original reply commit). Local ABORTED does not
  advance r; a lost receipt does not imply either revision. Neither
  revision is the lifecycle revision or a currentness credential.

Independently compare current exact original evidence at each boundary;
a replacement lifetime, reused alias, changed binding, stale policy or
equal-value rolled-back state cannot inherit the old admission. The
fixture reference is not an issuer, native admission, send permission,
resource grant or protected receipt. Actual issuer and rollback/fence
custody remain missing under R7f and Connections F1–F6.

### Desired future ordering (not implemented)

| Retirement timing / state | New work | Exact original operation |
| --- | --- | --- |
| Freeze before reserve | Refuse before title/body access, append or reserve | No admission or settlement inferred. |
| RESERVED before freeze, no proved admission | Refuse before further read/send/mutation | No new send; local reservation alone cannot establish no external effect, terminal or clearance. Resolve original evidence only. |
| Independently modeled original admission before freeze | Refuse conflicting work | Only independently eligible original settlement; no additional send, new attempt, history retrieval or disclosure grant. |
| Admission or effect unknown, conflicting, stale or replaced | Refuse | Retain original HOLD and recover exact evidence; no replay or replacement custody. |

New-work eligibility must be distinct from original-only settlement.
Actual B3 exchange c5dbbc29 yields RESERVED before fake stream and
checks current context/STOP again before commit (483–568). Invalidating
every context or automatically issuing STOP at freeze can abort the
original too. Do not bypass those checks: the future original settlement
path must establish its own exact independently current eligibility,
including any applicable revocation, not revive expired consent.
Retirement does not itself authorize or revoke a provider effect.

The eventual lifecycle-aware writer must resolve exact independently
authorized scope and check the actual transaction before B1 title/body
access, claim/create, both append roles, state/resume and B3 reserve;
R5/B4a must not bypass it. No wrapper-only protection or legacy fallback.
For settlement, verify the original admission and pending intent, OPEN
session at r, exact original latest user/RESERVED attempt, binding and
effect under the actual writer boundary before any unauthorized access
or mutation. Preserve the existing B3 _commit (282–368) atomic assistant
INSERT, session revision r+1, attempt COMMITTED and optional synthetic
outbox when enabled. No nested _write, second reply writer or added
ledger. The existing pre_commit callback is after metadata access and
is not this lifecycle guard. The independent source-use, actual send,
commit permission, recipient disclosure and revocation/effect fences
remain separate; no SQL lock across network IO as a substitute.

B3 _commit_fenced (242–280) may commit locally and lose its independent
synthetic terminal receipt, returning UNKNOWN_HOLD; _abort (372–397)
only updates RESERVED. B4d e4f4a537 recovery distinguishes local states,
not external C5 settlement. Local COMMITTED is not proof of provider
terminal or quiescence; local ABORTED/EOF/STOP is not proof of no effect.
On receipt loss inspect exact original durable outcome read-only; do
not roll back a committed reply, insert another, advance r+1 by guess
or replay. If revocation wins, deny new protected effects/disclosure;
already admitted effects must be accounted for under independently
established original outcome/settlement rules, not old consent.
Unknown effect or revoke ordering retains original HOLD.

Final retirement requires separately current original terminal,
quiescence, Heart accounting including retained residency, and Spirit
settlement, then the separately approved durable transition. Preserve
original H2 custody until independently justified; local commit, cache
eviction or a dormant label confers no release or Winter. Restoration
is a new explicit claim with independent currentness/admission.

### Negative acceptance cases for a later separate executable decision

| Case | Required distinction / observation |
| --- | --- |
| Freeze before reserve; pending conflict at direct B1/R5/B4a/B3 entry | No new title/body access, append/reserve or send in desired guarded path. Existing negative fixtures instead demonstrate missing guards; no false PASS via wrapper. |
| Freeze after RESERVED before modeled admission; unknown admission | No progression or inferred non-effect; retain exact original pending identity. |
| Freeze after modeled admission, exact original settlement | Only original atomic reply/revision/attempt/outbox; new work still refused. No new consent or external effect. |
| Foreign task/attempt/recipient, stale revision or binding, replacement/ABA, revoke | No original-only bypass or inherited custody; no unrelated mutation or stale disclosure. Unknown remains HOLD. |
| Exact local commit then lost receipt; duplicate settlement | One original reply and revision advance only; read-only reconciliation, no second insert/retry. |
| Local abort or uncertain terminal | No fabricated r+1 or ABORTED from uncertainty; actual local abort leaves r, independent effect/terminal unresolved. |
| Missing terminal/quiescence/accounting/settlement | No final retirement, physical release, new admission or UI season inference. |

Future tests must independently inspect exact attempt/reply count,
revision and original held H2 state, distinguish actual SQL behavior
from modeled admission and desired enforcement, and preserve existing
R7b/c/d regressions. No executable witness, helper, schema, ledger,
guard, issuer, A/B selection, protected operation, provider or native
invocation is approved here. Require exact Heart/Mind/Spirit and Nurse
design review and CI before operator document integration; any code
requires separate authorization. Actual retirement/native progress
unchanged; production HOLD.


## R7g // Source custody and architecture decision intake (design only)

DOC2F Runtime; Nurse #2161 7199720824 read-only intake, findings
7199767419, Spirit 7199781482, Mind 7200211072; Nurse 7200194336
authorizes this addendum only. Main 8cfd204ed46d40f8725efe5df78bd24ad12826c8
at edit preflight. See [R7a / R7f source feasibility](RUNTIME_LIFECYCLE_RECOVERY_R7A.md)
for the existing A/B analysis (#2876); this addendum records actual
source limits and outstanding owner decisions, not a second lifecycle
contract. R7d-d #2902 and R7d-e #2934 are integrated offline evidence,
not an implemented lifecycle guard. #2934 historical premerge review
failure remains recorded in Nurse retrospective closure 7198669788.

### Observed source and custody boundary

| Observed source (blob prefix) | What exists | What does not follow |
| --- | --- | --- |
| B5b native_host_candidate_b5b.py 1b21eb72; B5c INSTALLED_HOST_B5C.md ee7ba023; B5e disposable_launcher_b5e.py f4222a29; B5f SPLIT_UID_HOST_B5F.md 967675c2 | CI-only installed /usr/libexec/post-apollo/forest-ci/forest-host, one inherited SEQPACKET endpoint and fixed public HOLD; same-UID launcher and separately controlled split-UID experiment. | No enrolled production launcher, independent process/recipient identity or storage capability. Proposed /usr/libexec/post-apollo/forest/forest-host and /var/lib/post-apollo/forest/ are unapproved, not observed live installations. |
| Historical bristlecone/runtime/task_session.py a2458c4e (67–103, 175–285); colony/identity.py 849a4378; runtime/session_store.py fff28521, session_identity.py 64e97968 | Frozen Forest repo 28895aaf, raw-import/2026-09-22-transfer/The-Forest/: TaskSessionManager chooses forest_root, state/active.yaml and state/tasks/winter; YAML temporary write, fsync, replace and separate flock. Semantic Tree/context/lineage/operational role and adapter session binding are distinct. | Historical Task persistence is not an enrolled principal-to-store opener, a current canonical member/Assignment registry, rollback protection or atomic lifecycle/conversation commit. Do not import caller-selected root or treat the YAML lock as a cross-store fence. |
| B6 shared_context_b6r1.py b7fdcfc5; I6 runtime_membership_i6.py dcae58df | Typed original TaskContext reference and bounded same-owner process observations. | Neither proves durable Colony/Assignment membership, per-entity season, authenticated source or provider lifetime. |
| B1 session_journal_v0.py d1533f15; B3 turn_bridge_b3.py c5dbbc29 | Host-injected SQLite; local BEGIN IMMEDIATE; B3 reserves after body assembly, atomically writes original reply/revision/attempt on local commit. | Owner string is a filter, not authentication; no canonical task slot/lifecycle mapping, trusted opener, prequery permission or external effect serialization. |
| R5 runtime_public_conversation_r5.py 7dba584a; R6b runtime_public_child_r6b.py 03797786; B4a host_admission_b4a.py 5948497e; B5a host_boundary_fixture_b5a.py e1fa6615 | Disposable conversation DB, child fixture, injected admission, in-memory list fixture. | Not a real private storage owner, durable Colony roster or protected reader/writer. |
| B2 ollama_chat_transport.py db572336 line 189; B4d recovery_inspect_b4d.py e4f4a537 | Actual first prompt-bearing HTTP request boundary; read-only local attempt inspection. | Local COMMITTED/ABORTED, EOF or STOP does not establish external effect, terminal, revoke or settlement. Lost receipt remains UNKNOWN_HOLD without independently authenticated original outcome. |
| Connections ForestC5AuthorityBoundary.py 55949fd1; exact-session V1 preflight ccf9cdb8; native disclosure handoff 74b30180; writer custody preflight dc85f8d1 | Deny-only C5 boundary and separate reference candidates. V0 lacks signed sessionId; V1 adds exact signed sessionId, separate requester/reviewer/writer signatures. | V1 keys, B4c binding replica, history floor/predecessor and receipt are caller supplied, not enrolled source or persisted-row proof. No V0 migration/fallback, positive permit, real recipient, authenticated settlement or revocation ACK. |
| Heart H2 heart_resource_custody_h2.py 4ec58531 | Local instance-held exact six-field AttemptRef and reference accounting. | No independent original process/terminal/quiescence proof, physical release or accelerator/residency credit. Preserve H1 digest and H15b separate evidence lineage. |

### A/B feasibility and HOLD decision

Both candidates require an independently enrolled original host and
recipient, protected principal-to-store mapping, approved lifecycle
custodian and authoritative original Task/Tree/member/Assignment
identity. Neither is selected or qualified. Runtime owns prospective
lifecycle semantics, not an independently administered storage or
permission authority.

| Decision point | A: same durable domain | B: separately owned durable domains |
| --- | --- | --- |
| Storage ownership | Explicitly approved common lifecycle/conversation domain, opener and migration/old-writer cutover; reuse actual B1/B3 transaction where feasible. | Approved opener for each domain, distinct ownership and original cross-domain identity; no implicit trust from a common UID or directory. |
| Freeze vs new work | Exact current lifecycle slot/revision and every direct writer checked in the authoritative local transaction before protected title/body read and mutation; no wrapper-only coverage. | Durable original freeze/reservation/effect fence spanning both domains, authoritative ordering and recovery; separate YAML flock or two local commits are insufficient. |
| Original settlement | Keep exact original operation and conditional r to r+1 reply atomic with local attempt; separate lifecycle revision and settlement evidence. | Durable joined original operation/outcome and recovery proof across stores; no split-write assumption, second reply or fabricated success. |
| Crash/rollback/ABA | Actual writer recovery and independently current original identity/antirollback anchor, no legacy bypass. | Both stores and coordination recovery must detect rollback, replacement and lost receipt; no automatic replay or partial release. |
| External authority (both) | Independent prequery/read/use, actual send/revoke, commit and recipient fence remain required; no SQL lock across network as substitute. | Same independent gates; cross-store local fence does not grant protected effects. |
| Present decision | HOLD: no approved common custodian/opener/mapping. | HOLD: no approved separate custodians/openers or durable cross-store fence. |

### Responsibility and ordering

- Forest Core/Heart and Connections DOC2: identify an approved installed
  original launcher/process, release, PID/start/boot, lifetime and actual
  recipient/channel; independent custody must supply the exact principal
  mapping and protected storage capability, never Bark or request fields.
- Runtime: preserve original TaskContext/lifetime, lifecycle revision,
  active claim, exact operation/attempt and B1 conversation revision.
  Cover create/append (both roles)/resume/set_state/reserve at actual
  writer boundary, including R5/B4a bypasses. New-work freeze is distinct
  from exact admitted-original settlement; never blanket STOP to erase
  eligible original evidence or revive revoked consent.
- Spirit/Connections: authorize source/query purpose and each required
  metadata field before enumeration/serialization, including Colony
  coverage, titles and Warm metadata; separate read/use/generate,
  commit, provisional/final disclosure, recipient and provider-send
  permissions. Independently current source, policy and recipient and
  serialized effect/revocation at actual boundary required. No hidden
  roster query, stale cache/history attachment, legacy fallback or
  guessed empty/season from unknown coverage.
- Connections DOC1/DOC2 and independent custodian: F1 independent admin
  and custody, F2 Forest-purpose enrollment, F3 rollback-resistant
  current history/recovery; F4 original durable one-use identity,
  F5 serialized effect/revoke and terminal receipt, F6 independent
  native/operator qualification. See [custodian RFC](../../docs/connections-c3e-forest-purpose-custodian-producer-contract-rfc.md),
  [V1 preflight](../../docs/connections-forest-c5-exact-session-v1-preflight.md)
  and [native disclosure proposal](../../docs/connections-forest-c5-native-disclosure-handoff-proposal.md).
  Actual send gate records in-flight original before submitting bytes;
  revoke blocks new sends and accounts for drain/closure before ACK.
  Unknown send or lost ACK is HOLD, not recall of delivered bytes.
  F4/F5 interface preparation requires separate scope, not authority.
- Heart: exact original H11/H2 and H1 binding, independently current
  terminal, quiescence and subsequent attributable resource/accounting
  evidence including retained residency; Spirit independent settlement.
  Only then may separately authorized durable retirement proceed.
  No physical release, retry, new admission or inferred Winter from
  local commit, cache eviction, cleanup or replacement lifetime.
  UI1/UI2 retain presentation only; no new roster/season producer.

### Outstanding owner/operator decision record

| Decision to record explicitly | Accountable owners / current disposition |
| --- | --- |
| Approved original installed host release, launcher, runtime identity, process/recipient observation and containment | Core/Heart, Connections DOC2, operator; no qualified production candidate. |
| Principal-to-store capability, actual lifecycle/Assignment custodian, storage scope and A/B transaction domain; migration, old writers, sidecars, recovery and rollback policy | Runtime, Core, storage custodian, Connections and operator; unselected. |
| Independent Forest-purpose administrative/key custody, enrollment, currentness and restore/antirollback topology | Connections DOC1/DOC2 and independent administrator/operator; F1–F3 HOLD. |
| Original operation, source-use, recipient, send/revoke and exact terminal receipt/unknown recovery ordering | Runtime and Spirit/Connections; F4/F5 interface decisions pending, no positive authority. |
| Original terminal/quiescence and resource release accounting; independent native acceptance and activation | Heart/Runtime/Spirit, Connections F6, Nurse and operator; HOLD, separate authorization required. |

Connections #2119 decision #7132962989 expressly defers NAS/second-PC
setup until current-system work is complete. Hardware availability is
operator-reported, not readiness or selected topology. #7171062483
remains unanswered at inspection. No provisioning, probing, key
creation or enrollment request. Local development remains ACTIVE
within separate authorized scope; no actual protected issuer, opener
or lifecycle custodian is established by the inspected sources.

No new file, code, guard, schema, registry, issuer, test, workflow,
storage choice, native/host operation or model admission. Exact
Heart/Mind/Spirit review, UI1/UI2 targeted compatibility if Colony/UI
wording is affected, exact-head doc CI and final Nurse source review
must precede separate operator integration. Native/protected/production
remain HOLD.
