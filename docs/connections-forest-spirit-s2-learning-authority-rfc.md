# Forest Spirit S2 // Learning and absorption authority (RFC)

PATIENT: The-Post-Apollo-Project · ROOM: Forest Integration / C5 · OWNER: DOC 3F · STATE: PROPOSED, source-only; protected production HOLD.

## IMPLEMENTATION // Recovery evidence and gap

Recovery #7160677299; S1 #2684 (pending independent acceptance); R6a R1 frozen public CI-only #7160417171. Target main 52fb321a246632366d49902040d5b1298f63309f.

Original evidence pinned to 28895aafdddb07cf402f1e75574eea1ee79a516d:
- [Bristlecone AGENTS](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/The-Forest/bristlecone/AGENTS.md): only user-approved lessons enter approved learning, no self-approval or permission changes.
- [Learning foundation](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/The-Forest/bristlecone/learning/foundation.py#L740-L850) blob fb79b392: record creation sets status active; source refs, protection and recorded-by fields are caller inputs, not proof of approval.
- [Append](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/The-Forest/bristlecone/learning/foundation.py#L1638-L1766): local lock, immutable revision, separate user/operational generations, JSONL append/fsync. Mechanism retains history, but does not itself verify approval, independent policy currentness or rollback-resistant custody. Do not copy its store.
- [Operational compatibility facade](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/The-Forest/bristlecone/learning/operational.py): aliases the single foundation store rather than creating a second source of truth.
- [Language candidate Sap and Tar Sap](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/Trees/FOREST-LANGUAGE-Edited-Candidate-0.13.35-Edit-Chain-002.md#L12695-L12765): temporary use distinct from lasting absorption; purpose, scope, sensitivity and user authorization. Archived concept not a live classifier.

Current Mind #2683 M7a and #2691 M7b use SelectedHotRecord, HotRouteStamp and task-local derived caches. Active status, selected ID, generation, Tree and cache reuse are fixture references, not approval evidence; record eligibility across Clone/Task is unresolved for protected use. Current [C5 boundary](../services/connections/forest/ForestC5AuthorityBoundary.py) and [B6 C5 RFC](./connections-forest-c5-b6-protected-permission-consumption-rfc.md) prohibit caller-supplied authority and require exact independent scope/egress custody. S1 distinguishes delegation, tool release and deliberate pruning. S2 proposes a missing semantic separation without new flags, wire, issuer, storage or controller.

## Proposed operation semantics (not signed action names)

| Intent | Required authority before actual effect |
| --- | --- |
| Observe or propose a learning candidate | Existing source access permission for exact purpose; candidate is not trusted knowledge. No automatic approval or promotion. |
| Temporarily use selected knowledge | Independently current read/use scope for exact record revision, canonical principal/Tree/Clone/Task and model/provider/recipient. Scope before body read or context assembly. No durable absorption inferred. |
| Commit lasting learning / absorb | Separate explicit operator-approved policy or exact approval of record content/version, destination and permitted future use/retention. Source permission is insufficient; no self-approved active flag. |
| Reuse retained learning | Independently revalidate current provenance, source restrictions, destination, purpose and sensitivity before retrieval/use; historical approval is not present permission. |
| Supersede, prune or downgrade | Separate mutation/classification policy, original protected classes, dependencies and recoverability; no consent inferred from cache eviction, confidence or season. |
| Release to external tool/model/Tree | Separate current disclosure/delegation authority and actual serialized input/recipient commitment; temporary use or approved retention alone never implies release. |

A public fixture is owner-created fixed synthetic data, not arbitrary data labeled Water, public or approved. Unknown classification/provenance/currentness refuses before private reads, assembly, persistence or release. Tar Sap remains local-only and purpose-bound per historical doctrine; current implementation has no approved classifier, keys or policy source, so no positive path. Never disclose private text/IDs, raw exceptions, policy details or protected counts in generic refusal. JSON reference framing is not prompt-injection isolation.

## Required owner join (no new schemas yet)

Mind owns durable record version, source/dependency lineage, retrieval filters, actual protected storage/commit and receipts; Runtime owns current task/execution context and actual provider submission; DOC3F owns use/absorption/egress semantics; Connections DOC1/DOC2 own independently current custody, source/recipient verification and revocation. Heart owns resource admission, not data grants. Resolve authority independently of record, model, UI or cache. Bind stable original effect unit to exact approved content/target/version/purpose/recipient and independently current policy/revocation generation; approval for one effect cannot silently authorize another. Durable promotion and outbound disclosure require separately scoped effect accounting and actual outcome; unknown/partial effects fence original operation, never auto replay, infer rollback or refund. Revocation stops future authorized use, invalidates affected derived selection; not proof of erasure of already disclosed bytes. Policy clocks in M7b must be independently supplied by actual owner/custodian, not arbitrary monotonic integers.

No protected source body read before approval check. Avoid reconstructing sensitive body to generate public refusal. Historical append/active status and local fsync are not independent authority. User-authorized standing policy may be considered later with exact bounds; this proposal does not require a prompt for each ordinary public read, nor grant automatic learning.

## HOW TO USE / VERIFY

Request DOC4F exact source/read/approval/destination/effect interface, DOC2F actual model and tool submission boundary, DOC1/DOC2 independent policy/currentness/custody requirements, Nurse2F and Connections Nurse2 scoped review. This is a document-only proposal; no runtime behavior verified.

Future integration regression matrix using the actual owned seams: candidate cannot become approved via active/confidence; valid read/use cannot promote; approved retention cannot export; revoked/expired approval and stale policy clock refuse cache reuse; base Tree/Clone/Task/destination mismatch refuses before body read; unknown provenance and protected class refuse without raw output; superseding revision invalidates exact old approval; unknown append acknowledgement preserves original effect fence; fixed public fixture still works without protected grants. Use real owner implementation and independent evidence, not another synthetic signer or parallel store. S1 and S2 no change to frozen R6 protocol or disposable trial.

## DECISIONS

Proposed semantic recovery only. No positive authority, durable-learning implementation, new wire/flags, original repository writes, model execution, deployment or protected activation. Operator and owners must agree current policy before implementation; independent custodian/actual writer and release remain blockers.


## S3 // Owner reconciliation and exact effect ordering (proposal, 2026-11-25)

S2 #2745 is merged at 4706775c (6/6 workflows; 144/144 dedicated tests).
Its five refusal methods are not a protected integration. Mind M7d-a #2735,
DOC3F scope acceptance #7165714136, Runtime #7162779126 in Forest #2161,
and Connections DOC1 #7162375593 / DOC2 #7162425518 in #2119 agree on
semantic separation but require independent custody before protected freeze.
This addendum addresses their ordering requirements; no producer is selected
or enrolled by this document.

| Boundary | Independently established facts | Actual owner / effect |
| --- | --- | --- |
| Metadata enumeration | source identity, permitted metadata class, current purpose and destination scope | Mind metadata query, before any private lookup |
| Candidate or exact-version use | immutable version and protected commitment, provenance, classification, principal/Tree/Clone/Task, purpose, recipient, current policy/revocation head | Mind authorized snapshot/body read; bind authorization and immutable source read in custodian-defined ordering |
| Temporary assembly and reuse | original read evidence and independently current eligibility, same exact destination and source restrictions | Mind cache/assembly; recheck before admission and every reuse; no fallback to latest |
| Durable absorption/mutation | separate approval, exact content/version and destination/retention scope, original effect identity, independent durable spend/fence | Mind actual writer transaction, immutable revision and domain-clock advancement; original writer receipt |
| Outbound release | separate current disclosure grant, actual enrolled recipient/channel lifetime, exact serialized unit and original effect | Runtime actual submission; durable spend/fence before possible send, serialized against revoke |

Current source seams at a2554b3d: scripts/forest/turn_bridge_b3.py
`_reserve` (line 145) reads/assembles context before the streamer is called;
`exchange` checks current context/STOP before reserve and again before the
streamer, but these checks do not establish independent source authority.
scripts/forest/ollama_chat_transport.py constructs JSON at line 135 and
calls `connection.request("POST", "/api/chat", ...)` at line 191.
The actual serialized payload and independently established recipient must
be bound at the latter owner's send boundary, not inferred from a model name,
endpoint string, or creation of a generator. No protected input may be loaded
merely to construct a commitment: compute it inside already authorized source
custody. B3 `_commit_fenced` (line 242) is a distinct synthetic SQLite
commit seam, not proof of a learning writer transaction or of provider
delivery. Existing provisional-output C5 disclosure and terminal-receipt
contracts remain separate; do not reinterpret their action/receipt schema.

Required ordering: authorize source access before body read; authorize
temporary use before assembly; authorize actual serialized outbound effect
before first possible send; separately authorize any durable learning
effect before its actual transaction. Historical approval validity and
independently current policy head must be verified separately. Revoke
prevents new effects and invalidates derived eligibility; post-read or
post-send recheck cannot undo bytes already read or sent. Unknown spend ACK,
partial send, lost append ACK, interrupted execution, or unavailable original
terminal evidence keeps the original affected scope fenced across restart
and key rotation. No new effect ID, expiry, rollback assertion, retry or
refund bypass. Recover only through independently authorized original-effect
lookup; a provider return or local COMMITTED does not settle independent C5.

Before executable protected integration, DOC1 identifies actual independent
policy/current-head, revocation, durable fence and historical custody sources;
DOC2 identifies actual enrolled source/writer/recipient and channel lifetime
evidence; Mind identifies actual immutable snapshot and writer/receipt
transaction; Runtime identifies actual serialized submission/terminal
boundary. DOC3F owns operation policy/consumption semantics, not those
producers. Nurse2F and Connections Nurse2 review their respective scopes;
operator approval is separate. No new schema, signer, store, daemon,
private read, protected grant, or native activation. Existing public
fixtures and R6 wire remain unchanged.

## S4 // Unified Tree continuity and stewardship authority (design only)

Operator unified Forest direction #2161 7202168479 and development
autonomy 7204485179; Nurse bounded reconciliation 7204663398.
Spirit proposal 7204342935, Runtime 7204354166, Heart 7204360784,
UI1 7204351741 and UI2 7204365035. This append-only proposal preserves
S2/S3 and the R7g custody findings. Connections owner review of the
completed interface is required before shared adoption, not before
draft preparation. No positive policy, default, issuer, schema or
execution is selected.

Historical input: frozen Forest repository 28895aaf, language candidate
0.13.35 Edit Chain 002, blob 5fcd899aff88db3fd8090b2e7c6e0645235b1816,
Maple profiles, Syrup/Leaf stewardship, Cedar protections and Canopy
material modes. These recover separate view/use/reference/copy/move/
edit/download/absorption intents, explicit Loose/Sturdy boundaries,
Never Reabsorb, minimum-copy derivation, reversible undo and explicit
early-destruction permission. Historical automatic feeding and discarded
Syrup reabsorption were off by default; this is not a new product
configuration or authority to enable either.

### One Tree, multiple authorized presences

A Tree's durable identity, knowledge, toolbox and Workshop relationship
can be shared by its base presence and named Clones. Separate stable
member and conversation identities from mutable display name, logical
home, assignment, binding revision, Task, input, recipient and actual
execution incarnation. Shared ownership is not shared active prompts,
unrestricted transcript access, a physical resource reservation or
permission to execute every capability. Do not derive identity or grant
from a label, default Clone number, widget, local process or model name.

Standing user-approved policy may authorize recurring ordinary work
without another prompt for each covered action. Proposed policy field
groups: independently authenticated principal/Tree and delegated
member/role scope; exact allowed source classes and operations; purpose,
destination/recipient and capability limits; retention/protection
restrictions; time, workload and effect budgets; explicit exclusions,
revision and independently current revocation. No silent escalation or
Tar Sap expansion. The actual source must check eligibility before
enumeration/read, and the actual effect boundary must verify current
authority and original operation identity before submission or mutation.
A standing policy can be changed or withdrawn; unknown currentness
does not become implicit permission. Cross-Tree Mycelium and external
routing remain separately scoped. No repeated operator confirmation
is necessary for already approved reversible work within its bounds.

| Intent | Independent boundary (proposed, not signed actions) |
| --- | --- |
| List or inspect member/chat associations | Authenticate recipient and purpose before source enumeration; separately permit each field, relation and completeness claim. Hidden name, number gaps, count, title, home, role, task and season must not leak. |
| Rename / change display label | Exact stable member and current metadata revision, authorized mutation and durable receipt. No recreation, history relabel or permission expansion; default number comes from owner, not UI enumeration. |
| Reassign conversation / change binding | Exact old and proposed new member/chat, current binding revision, independently permitted new recipient and data scope, original pending effects retained. No implied cardinality, draft/history/cache or grant transfer; no automatic send or replay. |
| Renew execution | Keep original committed conversation and authorship; requalify new Task/lifetime, input, model/recipient, resource and policy. Original uncertain effect stays fenced under its original identity. |
| Automatic same-Tree coordination | Current scoped standing policy, exact eligible version/source, task/recipient and action, separate actual capability and resource admission; no broadcast of protected work. |
| Cross-Tree or external release | Separate current destination and disclosure/delegation permission; bind actual serialized unit and original effect before first possible send, per S3. |

A local filter or selection is navigation, not a query grant or a
composer retarget. Source-side field authorization and relevant coverage
must precede assembly; independently current source, recipient and exact
view must hold at delivery. An authorized subset does not prove absence
of hidden members or complete-empty. Unknown is neutral unavailable,
not a guessed count or hidden reason. Withdrawal removes only affected
presentation/eligibility, not durable data or original pending custody.

### Leaf stewardship and retention boundaries

Keep retention priority (Loose/normal/Sturdy), active use or storage
location, and independently established protection/permission separate.
A Leaf is a meaningful knowledge object, not a token, byte, native
context entry or measured physical resource. Original history, immutable
approved knowledge versions, derived summary/decision material, task
working set and provider context remain distinct.

| Intent | Required scoped effect and outcome |
| --- | --- |
| Inspect / temporarily use | Exact permitted metadata then independent version/body/use/recipient scope; no durable retention or sharing inferred. |
| Preserve / change Leaf state | Current authorized metadata mutation; respect user-marked Sturdy and Loose limits. No silent demotion or permission change. |
| Remove from active context | Invalidate only the authorized derived working set; no journal deletion, durable erasure or physical resource-release claim. |
| Refine / derive Syrup or summary | Independently authorized source, version, purpose, derived destination and retention. Minimum necessary copy; preserve Sturdy original and protection; whole-copy needs exact scope. Preserve permitted provenance, decisions, rejected alternatives and uncertainty; no rewrite of original authorship. |
| Shed / retain inactive material | Exact retention/grace/recovery policy and source transition; explain reversible changes and offer authorized undo while actual recovery remains possible. No invented grace duration or implied destruction. |
| Recover / reabsorb | Independently current eligible source, provenance, destination and consent. Never Reabsorb remains binding; Trusted Shed historical exception is not a current grant or unrestricted Cedar bypass. |
| Absorb / promote lasting learning | Separate explicit approval or exact standing absorption policy, original writer/version and durable outcome. A preview, temporary use, active flag or derived summary does not approve promotion. |
| Transmit or feed another Tree | Separate recipient/destination and exact release scope, including actual bytes and use limits. Retention and source permission alone do not authorize feeding. |
| Irreversibly destroy | Explicit separately approved scope and effect, actual source owner and dependency/replica/recovery coverage, independently verified outcome. No automatic destruction from ordinary pruning, confidence, cache eviction or season. |

For destruction, distinguish requested, pending, confirmed within
verified scope, and unknown/partial outcome. Before actual mutation,
resolve the authorized original records/versions and affected copies,
derivatives, indexes, caches, logs, replicas and recovery material with
their owning custodians. Do not read protected content merely to discover
or disclose scope; require authorized metadata and independent source
coverage. Identify excluded copies and externally delivered bytes only
as permitted. Do not promise their recall or unverified backup erasure.
Resolve conflicts with retained provenance, recovery requirements and
other owners before effect; preserve only authorized non-content receipts
that cannot recover or expose forbidden content. No covert retained
summaries, fragments, fingerprints or recurrence checks contrary to
destruction scope. A confirmed irreversible destruction is not undoable.
Unknown effect retains original operation custody, not success, rollback
or permission to retry. No actual deletion algorithm is selected here.

Maple/Cedar automation may apply already approved reversible actions
with bounded workload, policy/currentness and user-readable permitted
reason, source/version and undo when available. Explicit new irreversible
scope, external effects and permission expansion remain separate. Actual
summarization/refinement may itself require a model and resource claim;
no budget bypass or guaranteed speed improvement. Reduced Leaf count,
dropped references or deleted files are not proof of freed RAM/VRAM;
independent Heart H11/H2 terminal, quiescence and accounting remain
required. Resource cleanup likewise does not prove content destruction.

### Negative cases and review boundary

| Case | Required result |
| --- | --- |
| Shared Tree, foreign Task or revoked recipient | No private enumeration/use or effect despite common ownership. |
| Allowed visible subset, hidden members or unknown completeness | No inferred total/empty, numbering gaps or revealing status. |
| Rename/rebind with stale revision, foreign recipient or unresolved original send | No silent transfer, relabel or replay; original custody retained. |
| Replacement execution or filter change | No inherited old grant, automatic composer target or resource credit. |
| Sturdy derivation, Loose restriction, Never Reabsorb | Preserve authorized original/protection; refuse conflicting reuse or revival. |
| Allowed reversible automation, denied promotion or transfer | Ordinary covered action only; no expanded authority or repeated prompt for the already covered action. |
| Derived working set shed, allocator/provider still resident | No inferred durable erasure, physical credit or original settlement. |
| Destruction requested, unknown derivative/backup or lost receipt | No complete-erasure claim, covert retention, new effect ID or automatic retry. |
| Confirmed scoped destruction, later recurrence request | No recovery or forbidden reuse; only permitted surviving provenance/receipt. |
| Local SQL success, matching fixture signatures, revoke after send | No independently authenticated external terminal or recall of delivered bytes. |

Runtime owns identity, binding and actual writer/submission ordering;
Mind owns version/dependency and storage/derivative outcome; Heart owns
resource measurement; Spirit owns permission and destruction semantics;
UI owners present qualified outcomes. Connections DOC1/DOC2 retain
independent custody/currentness and enrolled source/recipient; actual
F1–F6 remain unresolved and NAS/second-PC setup deferred by #2119
7132962989. R7g A/B unselected. This design selects no authority,
default, registry, storage, signed action, API, transport or deletion
implementation. No new executable source, test, protected read, grant,
credential, external effect, host operation or production activation.
Review this exact completed proposal with affected owners and Nurse;
operator integration remains separate.

## S5 // Multi-author room audience and delegated work (design only)

Operator group conversation clarification #2161 7215166665/7215453268,
UI2 S5 #2999, Nurse 7215502409 and Runtime source analysis 7215535828.
This proposal refines S4: one durable room may contain independently
authorized authors across Trees and Clones. A versioned association
does not designate the sole speaker. Serialize conflicting actual
effects and durable message appends separately, not the right to speak.
S4 source and stewardship protections remain. No A/B transaction
choice, real roster, issuer, new grant, default policy or execution.

### Concrete existing source gap

Main 916ebb03: B1 session_journal_v0.py d1533f15 has one owner/Tree
per session, ordered user/assistant roles and owner-filtered body
reads, not authenticated member authorship or per-message audience.
B3 turn_bridge_b3.py c5dbbc29 reserves one attempt per user turn and
one live attempt per session; original revision/latest-user checks
also prevent simply admitting two group replies. M2 1085bc56 refuses
Clone scope; retain refusal. C5 ForestC5AuthorityBoundary.py 55949fd1
refuses every protected operation; LIST, title, READ, provisional
disclosure, committed release, tool input/execution and delegation
are already separate. None establishes membership, a message audience,
attachment access or a durable room grant. Do not reinterpret signed
V0/V1 session references, weaken existing checks or create a parallel
authority to make group chat work.

### Separate independent boundaries

| Boundary | Required scope (logical fields, not a wire schema) |
| --- | --- |
| Room membership / join / leave | Actual room, authenticated member and Tree, current membership incarnation and policy revision. Join grants no retrospective history by itself. |
| Visible room projection | Authorized recipient/view and field groups before source enumeration; relevant completeness separately qualified. No hidden names, participant counts, unread counts, message ordinals/gaps or attachment existence leaked. |
| Message / attachment delivery | Exact original message/author, version/content commitment, independently permitted audience, actual recipient/channel and current scope. Attachment metadata, preview, body, download and external release independently scoped; a link is not access. |
| Address / response routing | Actual authenticated speaker, deliberate addressed member(s), trigger message, current room and individual mode, eligible audience and bounded causal root. A quoted or proposed address does not create a response job. |
| Model context / submission | Each member's independently eligible room-message subset and private Task context, exact input and provider recipient; actual serialized send fenced per S3. Shared room never grants private Leaf or cross-Tree history access. |
| Delegated assignment | Original operator authorization, permitted delegation chain, approved revision, exact receiving role/member/Task/workspace/target/actions and current scope; separate original assignment and effect identity. |
| Tool / state mutation | Actual resource/effect owner, independently current grant and claim, conflict ordering, exact operation and actual terminal outcome. A spoken reply or approved design is not execution or a receipt. |

Room mode is a ceiling on participation, not an access or resource
grant. Per-member mode and optional suggestion preference narrow it.
For the S5 example, collaborative Maple may offer relevant bounded
dialogue, observing Cedar receives only independently permitted
messages and stays silent absent deliberate permitted mode change,
directed DOC 1 may volunteer bounded proposals where room policy
permits, directed DOC 2 does not volunteer. These are example labels,
not authenticated identities or configured policy. No automatic
fan-out. A directed participant can address another only within
user-approved communication bounds; that does not delegate a tool.
A mention, quote, suggestion, address, assignment, design acceptance,
implementation authorization, execution and user acceptance remain
distinct. A text token or model intent guess cannot establish an
authorization. Ambiguous effect intent is non-executing.

### Covered handoff and independent original effect

An already approved bounded standing grant can cover multiple
delegated work steps without repeated operator prompts. Before
admission the receiver must independently establish the authentic
original grant, exact approved revision and intended scope, delegation
eligibility and any limits on subdelegation, current sender and
receiver roles/assignment, recipient and actual target/action,
remaining effect/resource budget and current revocation. A relay
message, summary of approval, room role, mode or checked UI control
is not that evidence. Attenuate at every delegation; no widening
scope, forwarding credentials, transferring old execution authority
or self-authorizing a new effect.

The actual source must authorize before metadata or body access.
A response job independently binds original trigger, recipient,
allowed input snapshot, policy revisions and causal root. Recheck
before context assembly and actual provider submission; separately
qualify outgoing answer/artifact audience and original message append.
An intervening append cannot silently refresh old context or change
recipient. A delivery envelope for several recipients must be
qualified for each; do not leak who was excluded, and do not treat
authorization for one recipient as authorization for the group.
Revoke or leave invalidates affected pending admissions, derived
eligibility and delivery, not unrelated authorized work. Distinguish
local durable append, external delivery and actual tool effect.
A committed room message does not prove all recipients received it
or any described change occurred. Unknown original effect remains
fenced across restart; no replay, alternate recipient, implicit
rollback or new operation to bypass original custody. Already delivered
bytes cannot be recalled by revocation. STOP does not prove terminal
or release resources. Heart independently accounts for each workload.

### Negative acceptance cases

| Case | Required result |
| --- | --- |
| Member joins a room with older restricted messages | No automatic historical read, ordinal/count leak or private Leaf access. |
| Observer or directed non-volunteer is merely mentioned | No response job, model invocation or tool effect. |
| Authorized member addresses another | Only independently permitted response; no inherited tool grant. |
| Quoted/negated command or proposal to assign | No assignment or dispatch. |
| User accepts design, but implementation grant absent | Proposal/design state only; no write. |
| Exact approved delegated scope remains current | Covered work can proceed without redundant consent; actual separate effect fence required. |
| Sender claims approval, stale revision or widened delegation | No grant, source read or effect from that assertion. |
| Two eligible speakers respond to one trigger | Distinct original jobs and ordered append, not a shared effect claim or one-speaker restriction. |
| Attachment or message visible to only part of room | Per-recipient disclosure; no global metadata/body or excluded-audience leak. |
| Leave/revoke during response or recipient replacement | Withdraw affected new delivery/admission; original pending effect retained, no retarget or retry. |
| Repeated relay/reconnect or unknown tool receipt | Reconcile original job/effect; no duplicate response/tool call or inferred success. |
| Cross-Tree room with private member memory | No automatic Mycelium transfer, shared memory absorption or universal context broadcast. |

Runtime owns actual multi-author append, job and effect ordering; Mind
owns exact input/approval revision and Leaf lineage; Heart owns bounded
turn/resource claims; UI owns deliberate addressing and honest
presentation. Spirit owns purpose, audience and delegation semantics;
Connections owns actual independent issuer/custodian/currentness and
recipient evidence. Existing F1–F6 and hardware deferral #2119 remain.
This completed design proposal does not change C5, choose a signer,
policy source, registry, database, wire format, queue or budget,
or authorize protected data, model/tool execution or host operations.
Native/protected/production HOLD.
