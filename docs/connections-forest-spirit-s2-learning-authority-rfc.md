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
