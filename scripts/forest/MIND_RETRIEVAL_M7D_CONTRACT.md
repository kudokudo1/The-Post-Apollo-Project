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
