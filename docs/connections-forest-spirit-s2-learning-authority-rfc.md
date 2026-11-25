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
