# M7d-a // Metadata-first exact-version retrieval (owner proposal)

Patient: The-Post-Apollo-Project; Forest Integration; DOC4F Mind.
Development ACTIVE; protected reads, writes, provider use and production HOLD.
Recovery #2161 comment 7160677299; S2 #2705; DOC3F successor #7162620619.
Base 55aa55d8. Independent M7c #2730 remains a draft at 017f00eb.

## Source and gap

Original frozen tree 28895aafdddb07cf402f1e75574eea1ee79a516d,
raw-import/2026-09-22-transfer/The-Forest/bristlecone:
- learning/turn_retrieval.py 78503738 lines 205–284, 612–697:
  exact selected IDs, domain, captured generation; even empty selection
  checks current policy. Recover exact selection, not historical permission.
- learning/foundation.py fb79b392 lines 1400–1470: latest eligible
  revision at or below requested domain generation. Append retains immutable
  revisions but historical local file/active state is not authenticated authority.
- learning/snapshot_provider.py df607872 lines 654–784: domain/id/generation
  lookup and bounded coordination of loads; cached hits precede current
  generation lookup. Do not transplant this as protected access.
- learning/context_matcher.py b95be680 lines 257–350: metadata trigger index
  before record load. Automatic matching is a later separately reviewed step.

Current main M7a SelectedHotRecord contains domain generation but no exact
record revision, original source, approval, Clone/Task eligibility or
recipient. M7b TaskStickyContext is bounded volatile derived data.
B1 session_journal_v0.py d1533f15 stores committed conversation, not approved
learning; no equivalent protected knowledge store identified in current tree.
Connections C5 authority boundary and writer-custody preflight remain
deny-only/reference-only. S2 is an accepted owner proposal, not a grant.

## Proposed semantics, not wire/schema or callable permission API

1. Independent owner resolves current TaskContext (principal, Tree, Clone,
   task, context, execution generation), input and both domain clocks, policy
   and revocation currentness. Owner identifies intended purpose and exact
   model/provider/recipient boundary. No body read or disclosure here.
2. Separately authorize metadata enumeration where required; do not assume
   read permission grants listing. Candidate metadata is bounded and private
   unless explicitly public. Resolve exact selected domain/id/revision from
   owner-pinned source identity and snapshot; choose visible revision at or
   below independently held domain generation. Reject duplicates, ambiguity,
   future generations, wrong domain, unknown provenance, unauthorized scope,
   superseded/revoked use and missing revision. No fallback to latest.
3. Independently verify current read/use approval for exact record version,
   original source identity, content commitment, sensitivity, source and
   destination scopes, purpose, recipient, policy epoch/revocation state
   before reading any body. Approval must bind immutable version and
   content commitment; historical approval, active status or cache hit
   never establishes current authority. Metadata verification itself cannot
   silently load private bodies or derive a public summary.
4. Protected custodian must bind authorization and exact-version read to
   actual immutable source transaction/snapshot; prevent substitution and
   define revocation/read ordering. Separate owner recheck after read and
   before cache admission/assembly; changed/unknown authority discards
   derived results and blocks further use. No assertion that recheck alone
   closes a concurrent revocation race or erases already read bytes.
5. Keep exact record-version provenance distinct from domain snapshot
   generation. Project into M7a selected records only after all checks.
   Bound at most 32 selected records, 4096 UTF-8 bytes each, 16384 assembled
   bytes including framing; no truncation or partial assembly. M7b cache
   admission and future reuse must preserve binding to current eligibility,
   not merely record ID and domain generation. M7c shedding drops only
   derived state. No shared cross-task mutable route or inherited rights.
6. Empty selection still requires independent current policy/context check.
   Any missing selected record refuses complete composition. No automatic
   candidate expansion, prompt injection defence claim, token-fit claim
   or model submission. Runtime/Heart own dispatch and capacity respectively.

## Durable absorption and receipt boundary

Read/use and retention are separate effects. No conversation-to-lesson
promotion, active flag, inferred preference, trigger match or model verdict
automatically commits knowledge. Independently authorized absorption binds
exact candidate content commitment/version, provenance, destination, scope,
retention/use policy and original effect identity. Owner-controlled writer
must establish immutable revision and domain-clock advancement atomically
with actual durable effect evidence; old history must not be overwritten.
Separate protected writer enrollment, original peer/release, independent
custody floor, transaction evidence and serialized revocation/settlement
are required, not caller-selected signatures or local fsync alone.
Unknown outcome fences original effect, no retry/refund/inferred rollback.
External release requires separate exact current egress authorization and
actual serialized recipient/input commitment. No schema or writer selected.

## First bounded implementation proposal (M7d-b)

Only after owner and Nurse scope agreement: fixed public synthetic metadata
and immutable revisions in an isolated test fixture, exact selection and
version resolution, bounded all-or-nothing projection, no real source,
private body, positive grant, persistent store, signer or R6 integration.
Negative matrix: future/stale snapshot, wrong domain/task/Clone/Tree,
duplicate/ambiguous/missing version, superseded/revoked candidate,
wrong commitment, metadata without read authority, stale currentness,
empty selection, unselected records, size cap and no partial cache admission.
Fixture can test call ordering using fixed public bodies; cannot prove
independent custodian, atomic authority, real durable storage or protected
retrieval. No new parallel cache/controller, automatic trigger matcher,
production API or durable learning write in this slice.

## Exact owner requests

DOC3F: ACCEPT/REVISE metadata/read/use/absorption/egress separation and
revocation ordering, exact version/source/commitment/recipient requirements.
Connections DOC1/DOC2 via #2119: identify independently authenticated
source/custodian, current policy and revocation evidence, protected writer
enrollment and durable receipt/settlement interfaces; no positive path until
agreed. DOC2F: independently held task/attempt and actual provider/recipient
handoff, effect settlement; no model dispatch in M7d. DOC1F: byte budget is
not admission or tokenizer capacity. Nurse2F: independent M7d-a scope
review, then explicit M7d-b disposable scope decision. Preserve R6 critical
path, M7c review and operator final acceptance.

## M7d-b disposable implementation

Nurse2F #7169077778 authorizes this narrow witness; Security #7165714136
conditionally accepted. Implemented entirely in tests/forest/test_mind_version_resolution_m7d.py
with a fixed public literal catalog and bodies, immutable selections and
separate fixture metadata/read-use observations. All selected versions
validated before any body read; compare source, exact current scope and
version/commitment, reject ambiguity, superseded/future or revoked records.
Visible history resolves at the independently held snapshot, never a
fallback to latest. Recheck fixture currentness before/after reads and
assembly, project to the existing M7a assembler, keep exact revision
references separate from domain snapshot generation.

Decision: no sticky-cache admission even on success. Existing M7b records
cannot retain exact revision/source/current-use commitments, so inserting
them would lose provenance. No protected producer or general reader is
implemented; the witness contains only known public strings and no I/O
other than Python test discovery. No actual permission, atomic custody,
storage, learned record, automatic matching, provider dispatch, or R6
change. Twelve focused tests in existing Mind CI; independent exact-head
review required. Production HOLD.


## M7i-a // Original Warm trigger routing (design candidate only)

Owner DOC4F Mind; Hospital #2161 proposal 7196959037, Heart 7198778561,
Runtime 7198782473, Spirit 7198806331, Nurse one-document authorization
7199717187. Supersedes only the deferral of automatic matching above as a
design investigation; M7d-b remains a fixed-public exact-selection witness,
not an automatic matcher. No executable behavior changes in this milestone.

Historical reference: kudokudo1/The-Post-Apollo-Forest-Project frozen tree
28895aafdddb07cf402f1e75574eea1ee79a516d, under
raw-import/2026-09-22-transfer/The-Forest/bristlecone/learning/:
context_matcher.py b95be68099035948803a8c119ec53ae2779d1e21 and
indexes.py da7b65afe3f77948d4d656b75dbd3ca7cda613ec.
The original matcher receives canonical Task signals, deduplicates in
first-occurrence order, looks up exact tags, sorts deduplicated IDs/types,
and chooses none/check/must-check. The original index derives mandatory
routing solely from explicit hard user constraints. Recover these semantics,
not the arbitrary iterable materialization, trimming of noncanonical input,
global cache/index, whole-domain enumeration, exposed record/untagged counts,
non-atomic separate generation read, or diagnostic error text.

### Owner boundaries and authorization ordering

1. Runtime independently pins the original TaskContext and lifetime,
   including principal, Tree, Clone, task, context and execution generation,
   original input revision/commitment and policy; supplies already canonical
   signals bound to that exact input. Current TaskContext has no qualified
   signal producer. No NLP, model call, provider/Bark inference, case folding,
   whitespace repair, Unicode normalization, semantic expansion or inferred
   operational-learning trigger in Mind. Noncanonical input is refused.
2. Spirit/Connections must independently authenticate the source, original
   query scope, purpose and intended recipient, and authorize metadata
   disclosure **before enumeration or serialization**, field by field.
   This includes tags, hard strength, IDs, types, completeness and any
   derived mandatory/mode indicator. Read/use of record bodies remains
   separately authorized. Only an immutable bounded metadata-only projection
   for the exact user-context domain and independently pinned durable domain
   generation (including retirement) is eligible. Snapshot, coverage and
   generation must be bound together by the actual custodian; separate
   current-record enumeration and generation reads or max active generation
   are insufficient. No concrete producer, index, store or issuer selected.
3. Independently establish relevant coverage and mandatory applicability for
   the original query and current scope/purpose/recipient. A visible subset
   and caller's complete flag prove neither coverage nor absence of mandatory
   constraints. An authorized complete-empty projection is distinct from
   unavailable. Unknown/partial/stale/refused/unauthorized coverage or
   mandatory applicability is neutral HOLD for the whole route. Do not probe
   hidden records to resolve this condition without prior authorization.
4. Mind checks bounded metadata and performs deterministic routing only
   after independent initial authority/currentness. At final publication/use
   of the route, independently verify the same original input, lifetime,
   source/domain generation, coverage, policy/revocation and recipient are
   still current. A changed, unavailable, contradictory or unverified
   observation discards the route; no stale fallback or retry against another
   task. A recheck alone does not establish atomic revocation/effect ordering:
   the actual disclosure boundary requires independently qualified fencing.
5. Output is a task-local candidate reference selection, not a grant, read,
   record version resolution, cache admission, assembly or dispatch. M7d
   must independently resolve exact versions, source/content commitments,
   eligibility, read/use and final currentness even for an empty selection.
   Hard constraint means routing necessity only, never authority or budget
   bypass. An unresolved mandatory candidate cannot be silently skipped.
   Runtime retains lifecycle/effect authority, Heart capacity/admission,
   Spirit security, Connections custody and UI owners presentation.

### Proposed finite limits (not a wire schema or hardware measurements)

These are candidate logical ceilings for a later separately authorized
fixed-public witness. All bounds are inclusive and apply to one original
Task routing operation. A future producer must enforce them while reading
and before serializing; Mind must independently validate the already bounded
input before copying/materializing, deduplicating, indexing or matching.
Reject unbounded iterators, mutable or lazy collections and untrusted length
claims. A future decoder must bound its envelope before allocating a
collection; a post-allocation count check is not an allocation bound.

| Budget | Proposed maximum |
| --- | ---: |
| Raw canonical signal entries, including duplicates | 32 |
| UTF-8 bytes per signal/tag | 128 |
| Raw signal UTF-8 bytes, including duplicates | 4096 |
| Raw projected metadata rows, including duplicates | 128 |
| Raw row/tag associations across all rows, including duplicates | 512 |
| UTF-8 bytes per candidate record ID or type | 128 |
| UTF-8 bytes per other variable-width provenance/coverage field | 256 |
| Aggregate projection metadata UTF-8 bytes including repeated fields, provenance and framing | 65536 |
| Exact signal/tag comparisons (32 raw signals x 512 raw associations) | 16384 |
| Total distinct selected IDs across all routes | 32 |

Use a finite immutable collection with fixed allowed field groups, typed
scalar identities/flags and bounded nonnegative generation values (candidate
unsigned 64-bit range, bool not integer); reject unknown fields, unbounded
nesting, invalid UTF-8, empty identifiers/signals, conflicting metadata or
ambiguous provenance. All variable-sized fields and framing count against
the envelope, and repeated values count before deduplication. No arbitrary
callbacks or hidden secondary enumeration. Before set construction, establish
row/association counts, byte bounds and comparison upper bound using bounded
validation; while selecting, refuse on the 33rd distinct candidate, without
growing a result set past 32 or publishing a partial result. No per-route
32 allowance or truncation. Other bounded work includes validation of at
most 128 rows and 512 associations, bounded candidate accumulation and
sorting within validated limits; no unbounded work hidden in equality,
normalization or source access. Reject a projection requiring more work
than the declared budget. Exact identical metadata may be deduplicated
after validation; duplicate identity with conflicting metadata HOLD.
No claim about CPU, RAM, tokenizer capacity, physical resource credit or
native safety. Existing M7a limits of 32 selected records, 4096 UTF-8 bytes
per body and 16384 assembled bytes including framing remain independent.

### Deterministic candidate routing

For each first-occurrence canonical signal in the original input order,
compare exact tag values in the authorized projection. Retain the union of
matching candidate IDs, sorted in deterministic lexical order (and types
only when independently authorized and necessary); matched/unmatched signal
order follows original input order. A route is mandatory only when an
exact match is supported by an explicitly hard user-constraint record,
never by preference, record type alone, model verdict or inferred strength.

| Internal routing outcome | Meaning |
| --- | --- |
| none | Authorized, complete, current relevant coverage proves no exact match (including a qualified empty input/projection). |
| check | At least one exact match; independently established no mandatory match. |
| must-check | At least one exact match with independently established explicit hard user constraint; mandatory indicator itself authorized. |
| HOLD | Entire route unavailable: any missing authority, coverage, provenance, currentness, required disclosure, validity or limit. |

These outcomes describe internal routing, not a public status schema.
Only release independently authorized fields and routing information to
the exact intended recipient, including derived mode and completeness.
If safe relevant coverage or a necessary disclosure cannot be established,
return only neutral HOLD at the permitted boundary; no partial candidate
output, hidden hard-constraint existence, category/count/type/ordinal/tag/ID,
reason, diagnostic/accessibility leak or differentiated denial. No public
mode, count, reason, or UI projection is established by this proposal.

### Negative-case matrix for a future separately authorized witness

| Case | Required behavior |
| --- | --- |
| Authorized complete current empty vs unavailable projection | none only for proven no-match; unavailable HOLD |
| Exact tags, repeated signals/routes/identical metadata, mixed check and hard constraint | First-occurrence signal order, sorted unique candidate IDs, must-check only for explicit hard match |
| Case variant, whitespace, inferred synonym or raw prompt | No invented match; refuse noncanonical input |
| Unauthorized enumeration, hidden hard strength, mode or other metadata field | No enumeration/serialization before authorization; neutral HOLD when required disclosure unavailable |
| Allowed visible subset but unknown relevant/mandatory coverage | HOLD, never none or check-and-skip |
| Same visible mode with differing hidden IDs/types/counts/categories/ordinals | No hidden differentiation in output, errors, diagnostics or accessibility |
| Wrong original TaskContext, lifetime, input commitment, source, domain, purpose, policy or recipient | HOLD; no substitution |
| Stale/retired domain, input or policy changes, revocation, or unknown initial/final observation | HOLD, discard candidates; no stale route fallback |
| Conflicting duplicate ID/type/strength/provenance, malformed scalar or invalid UTF-8 | HOLD whole route |
| Raw duplicate flood, oversized field/envelope, row/association/work limit +1 | HOLD before unbounded allocation/scanning; no truncation |
| 32 union IDs across routes vs 33, including overlapping routes | 32 within selected-ID bound; 33 HOLD without partial release |
| Mandatory match but missing exact-version read/use authority, revoked version or failed downstream currentness | No body read/admission/assembly; mandatory route unresolved, no skip |
| Qualified empty selection with missing downstream currentness | HOLD; empty never bypasses M7d |

No executable matcher, parser, tests, schema, provider, credential, producer,
global index/cache, new storage, protected body access, absorption, model
call, host action or production feature is authorized here. A later witness
needs separate bounded authorization and review. Actual custody/currentness
and disclosure fencing remain unresolved. Heart, Runtime, Spirit and Nurse
must review the exact candidate document, and exact-head doc CI must succeed
before operator integration. Native/protected/production HOLD.
