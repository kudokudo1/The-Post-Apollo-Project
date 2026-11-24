# DOC 3 // Forest B6 C5 protected permission consumption contract (RFC)

PATIENT: The-Post-Apollo-Project · ROOM: Forest C5 protected operations and disclosure · STAFF: DOC 3, reporting to Forest Nurse 2 · CONNECTION: external Hospital-compatible, registration unverified · PRODUCTION HOLD.

## IMPLEMENTATION

Operator authorized DOC 3 succession and continuation in the existing lane. This is a consumer-side integration proposal, not a new wire format, new authorization backend, credential enrollment or production approval. No runtime change. The independent issuer and native source dependencies remain unresolved; another local test signer would not close them.

### Existing sources and provenance

- [C5 authority boundary](../services/connections/forest/ForestC5AuthorityBoundary.py) and [#2385](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2385): separate always-refusing list/title entrypoints; existing COMMIT_GENERATE semantics unchanged.
- [#2392](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2392): test-only signed public marker, one-use spend and local revoke ordering. [#2395](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2395): diagnostic privacy. Neither is independent authority.
- [C3e custodian RFC](./connections-c3e-forest-purpose-custodian-producer-contract-rfc.md) and [#2397](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2397): independent Forest-purpose custody proposed; installed test host public HOLD consumed, not enrolled.
- [#2415](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2415): C4b measured real installed test source and distinct UID recipient process; same-checkout pin and unsigned disposable RPM are not enrolled authority.
- [B6-R0](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7129266366), [R1 shared context](../scripts/forest/shared_context_b6r1.py), [R2 registry](../scripts/forest/capability_registry_b6r2.py): R1/R2 merged, source-only and forgeable, no access. Original archive provenance is linked in R0; Spirit deterministic policy, Heart governed shared data, Trunk execution, Bark presentation, Colony separate live contexts, Mycelium permission-aware cross-Tree continuity.
- [DOC 4 #2383](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2383): separate Hospital C5 original COMMIT uncertainty boundary; no transferable consent.

### Join of existing owners (semantic facts, not field names or wire)

| Fact | Producer / custodian | Required C5 consumer check |
| --- | --- | --- |
| Forest audience, approved root and issuer roles, history head, revocation floor | DOC 1 / independent administrator | independently current; no Identity/test roots or caller-provided trust pins |
| Original installed host release/process/boot/seat and actual recipient channel lifetime | DOC 2 with Forest Core | challenge-bound evidence, current at admission and egress; no PID/UID/hash alone |
| Canonical principal and owner domain, Tree, optional Clone, task, execution context and generation | Forest Core resolves using independently verified authority | exact scope of original operation; base Tree is distinct from every Clone |
| Original operation ID, exact request digest, challenge, expiry, current policy and revocation generation | independent custodian with C5 policy | one original operation and recipient; independently durable fence; no replay across purpose |
| Bark attachment, recipient, request correlation, view generation | Core host from verified source, not the UI | separate attachment and context generations; alias/hint is not canonical identity |
| Capability/operation and target data scope | DOC 3 policy; Core supplies operation semantics | LIST and title release are separately granted; R2 selection is metadata, not a grant |
| Actual protected storage opener, snapshot, serializer and outbound submission | Forest Core | no access before required grants; no substituted DB, mixed owners, or arbitrary callbacks |
| Current protected consent and one-use spend/settlement | DOC 3 consumer with DOC 1 custodian | verify independent currentness and bind exact scope, consume before irreversible submission; uncertain result stays HOLD |

These are required relationships, not new independently authoritative Python types. R1 TaskContext has principal_key/tree_key/clone_key/task_id/execution_context_id/generation/origin; BarkAttachment adds requester/release/seat/recipient/attachment references and view_generation. Both are caller-constructible. R2 SelectionPlan.context is an R1 value; its selected/sticky/dormant/unresolved capabilities are planning metadata. Do not copy those values into a trusted principal, permit, live lease or policy registry. The first metadata operation does not need a Workshop or model load. No duplicate registry, scheduler, DB, daemon or authorization service.

### First vertical slice (proposed ordering)

1. Parse bounded Bark correlation only. Resolve one canonical Tree/owner and independently authenticated source, context and recipient. Reject detached Bark, stale view/context generation, wrong Clone/Task or unsupported operation. No private lookup from a supplied owner or treeKey.
2. Independently check enrolled issuer, exact challenge/operation digest, current history/policy/revocation, expiry and scope. A valid signature alone is not currentness. A failed, stale or unavailable dependency returns fixed HOLD, no fallback.
3. Require LIST_SESSIONS before opening/querying private storage. Separate title grant before selecting, reading or serializing titles. Default for absent title grant: zero title bytes; until operator and Core/W accept an explicit opaque-only response contract, return public HOLD rather than invent a masked schema. Never derive LIST from READ_SESSION or title consent from LIST.
4. Core owns protected storage selection and consistent bounded snapshot: canonical owner and Tree predicate before LIMIT, no mixed-owner rows, no title read in opaque-only path. IDs/counts/timestamps are private metadata too, not a public error payload. Do not run model/tool.
5. Bind result to original operation and exact recipient; at actual host-owned serialization/send gate recheck current scope, expiry and revocation. Serialize authorization/spend with egress against revoke; independent durable one-use fence must be consumed before submission. A local mutex alone is not durable custody. No grant transfer on reattach or Clone creation. If disconnect, partial submission, lost ACK or unverifiable spend: UNKNOWN/HOLD and no auto-retry; original terminal lookup only through approved custodian. Never claim that a failed send means no private byte reached recipient.
6. Revoke fences future authorized submissions, not erasure of already queued/transmitted bytes. ACK requires actual fence and in-flight reconciliation; no ACK inferred from UI detach. Bark detachment is separate from cancelling an independently authorized background task.

No private values, rejected raw packets, exception objects, trace locals, request digests or identity fields in generic public denial output. Specific approved audit identifiers/retention remain owner policy. All current C5 methods remain deny-only.

### Cross-purpose invariants

- Forest LIST/title/read/generate/provisional/commit/send/voice/tools remain distinct operations. C5 does not implement Mycelium, Cedar key custody, Colony scheduler or Workshop activation.
- DOC 4 Hospital H4 human-consent refusal and H11 original PX receipt/recovery stay independent. Shared lessons: spend before uncertain effect; no auto-retry; original terminal evidence only. No shared grant, root, or receipt schema assumed.
- Identity Sign-In and TimeW restore remain separately authorized. No escalation through a Forest capability, Bark, Clone, model choice or sticky Workshop selection.

## HOW TO USE

Owner response in this PR or [Forest #2161](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161) / [Connections #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119): ACCEPT / REVISE / HOLD for your own interface, with concrete source path, trust boundary and tests. This RFC is not an install instruction.

## VERIFY

Review the one-document diff and current referenced source. No new runtime test result claimed. Future native disposable acceptance (after owner-approved interface and enrollment/test administration selection):

- Valid independent source and LIST grant with no title grant: no title selection or serialization; approved opaque-only policy or public HOLD.
- Valid LIST and separate title grant for exact scope: bounded synthetic records only in approved disposable protected host; zero model/tool invocations.
- Missing/wrong root, cross-purpose grant, stale head/revocation, signed denial, caller-selected source: no private DB open or disclosure.
- Same Tree with changed Clone, Task, context/view generation, recipient FD, seat, release, boot or request digest: no disclosure.
- Workshop core/sticky membership and R1 reference equality without grant: no disclosure.
- Changed DB/owner, mixed rows, title metadata in errors: refuse; check query and actual kernel egress instrumentation.
- Send/revoke races, detachment and source exit: no new submissions after verified fence; already sent bytes not retractable.
- Concurrent spend, crash before/after spend, lost ACK, restored snapshot: independently durable replay refusal and original terminal recovery or UNKNOWN/HOLD. No retry.

## WATCH OUT FOR

The existing installed candidate is disposable and sends only public HOLD. No owner-approved original protected host/DB/serializer, independently enrolled issuer, live seat/recipient trust, or title policy is established. Do not write authority-bearing runtime code until these concrete dependencies are accepted. This is not a replacement for Forest Nurse 2 review or Connections Nurse 2 succession.

## CHECKLIST

- [x] Reconcile merged R1/R2 and existing C5/C3e/C4b/DOC4 source contracts.
- [x] Preserve separate permission, source, custody, storage and presentation owners.
- [ ] DOC 1: accept/revise exact consumer scope and currentness/one-use interface; operator selects independent administration/enrollment.
- [ ] DOC 2: accept/revise original installed-source and recipient lifetime evidence; distinguish disposable observation from enrolled producer.
- [ ] Forest Core: identify approved host/DB opener/actual serializer, context resolver, storage and send gate. ForestW/Core/operator decide opaque-only versus HOLD/title schema.
- [ ] DOC 4: confirm common uncertainty invariants, not shared consent.
- [ ] Forest Nurse 2: independent review of C5 contract; Connections review remains separate.
- [ ] Implement and verify authentic consumption in bounded disposable integration after owner decisions; operator acceptance separate.

## NEXT

Obtain owner responses; preserve current DENY ONLY. No further synthetic authority wrapper. If an upstream interface is not ready, report blocker and continue only independently justified DOC 3 work; do not take another owner's implementation.

## DECISIONS

Operator-approved development direction: shared Forest architecture and DOC 3 continuation. Proposed consumer join and title policy remain pending owner review; production HOLD. No runtime change, key, deployment, merge or workstation action.


## First-Tree DISCLOSURE interface addendum (DOC 3F proposal)

Operator-approved responsibility split: [first-Tree decision](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7139439017) and [UI addendum](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7139466477). This section proposes exact semantic fields for owner agreement, not a new signed wire or runtime implementation. It extends the existing C5 contract and does not supersede independently reviewed denial behavior.

### Input and ownership

| Group | Proposed fields (reuse existing names at their owner boundary) | Producer |
| --- | --- | --- |
| Original context | principal_key, tree_key, clone_key (null means base Tree), task_id, execution_context_id, generation, origin | DOC4F resolves existing B6 TaskContext |
| Original operation | request_id, session_id, user_turn_id, attempt_id, expected_revision, operation, original_request_digest | DOC2F / DOC4F original attempt; no UI-created authority |
| Recipient | bark_id, requester_id, release_id, seat_id, recipient_id, view_generation, attachment state | Host + Connections DOC2, existing B6 BarkAttachment references alone are not evidence |
| Output unit | event_kind, sequence, exact serialized byte length and digest, projection/snapshot identity where applicable | DOC2F actual serializer; DOC4F history projection |
| Permission evidence | original purpose-specific permit identity, issuer/current history, expiry, consent/revocation generation, bound recipient and scope, durable spend evidence | Connections DOC1/2 and C5; never supplied as a trusted UI Boolean |

Each group is bound to the same original operation. No duplicate context registry or task ID allocator. Exact field types/limits and transport serialization must be agreed with producers; existing V1 signatures are not silently extended. Runtime-private identifiers and digests are not public UI fields.

### Behavior and final-send seam

- DOC2F keeps B3 RESERVED/STARTED/DELTA/COMMITTED internal. B3 DELTA precedes the final commit check. Neither model output, local COMMITTED, capability selection nor a valid presentation shape grants disclosure.
- Separate purpose permissions: LIST_SESSIONS, DISCLOSE_SESSION_TITLES, READ_SESSION, GENERATE, DISCLOSE_PROVISIONAL, COMMIT_GENERATE and SEND where applicable. Final committed reply access must be covered by its own accepted read/release policy; do not assume COMMIT grants display.
- Proposed host-facing disposition: HOLD (zero private bytes), UNKNOWN_HOLD (uncertain original effect; no retry), or future protected release only through the actual owner-controlled final send. No currently enabled positive release result. A positive Boolean returned to an unrestricted caller would not be a final-send fence.
- At protected admission verify scope before storage/model access. At actual send, independently verify current source, recipient/attachment, scope, lease, cumulative serialized UTF-8 byte budget and chunk sequence. Serialize send admission against revoke; independently durable one-use stream/operation spend before first irreversible submission. Subsequent chunks require current scoped lease/fence and monotonic sequence, not a new replayable grant. No automatic retry after uncertain send; original receipt lookup only. Send completion is not recipient display or protected terminal proof.
- STOP requests cancellation; detach invalidates recipient delivery; revoke withdraws permission. They are distinct, and cancellation/close/EOF is not a revoke ACK. Already submitted bytes cannot be recalled. Unknown outcomes remain unknown.
- Public-only disposable development is a separate explicit host-controlled scope using known synthetic/public input and isolated journal, no private history/tools/credentials and no caller-selected public flag. No fabricated issuer or positive protected permit; real local model execution needs its separate approval. UI2.1 can use public fixtures before protected integration.

### Presentation agreement

Existing LIST consumer returns exactly session_id,title,revision,updated_at_ms for OPEN rows, whereas chat-list policy consumes seven raw B1 fields. DOC4F/UI2 should agree a separate validated four-field presentation projection with request/Tree/view correlation in the enclosing response, without padding missing raw fields or asserting authentication. The title-bearing projection remains protected in production: canonical owner+Tree/Clone before LIMIT, distinct TITLE grant before title selection, bind canonical query/page/snapshot/projection and recipient to original operation (DOC1 correction #7138250815). Until an opaque-only policy is approved, missing TITLE permission yields public HOLD. UI may clear withdrawn/stale presentation; this is not retroactive erasure or revocation settlement.

### Acceptance gates

Owner agreement requested: DOC2F on exact event envelope, serializer and actual send location; DOC4F on resolved context/session/revision and query snapshot/projection; UI2 on presentation correlation, fixed status and STOP/detach semantics; Connections DOC1/2 on independent evidence and original spend; Nurse 2F independent integrated review. Test disposable public-only first Tree, wrong Tree/Clone/task/recipient, stale view/context, revoked/expired lease, missing title permission, DELTA before commit, cancellation, disconnect, duplicate/late chunk, unknown send and no retry. No protected production acceptance until real enrolled authority and native final-send verification. NAS/second-PC deferred. No other owner files modified.
