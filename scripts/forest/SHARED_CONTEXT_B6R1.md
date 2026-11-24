# Forest Core B6-R1 // Shared Tree, Bark and task reference contract

PATIENT: The-Post-Apollo-Project  
ROOM: Forest Core / Heart shared infrastructure  
ROLE: Forest backend DOC, external Hospital-compatible  
STATE: source-only semantic reference; production HOLD.

## IMPLEMENTATION

Operator approved the revised B6 architecture in the conversation following
[the B6-R0 proposal](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7129266366).
[Nurse 2 reconciliation](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7129223905)
and [B5 review closure](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7128564896)
remain the basis. This PR adds a pure Python semantic reference, not an
installed API, scheduler, wire or native authority implementation.

Original provenance: The-Post-Apollo-Forest-Project archived Language
0.13.35 edited candidate (blob 5fcd899aff88db3fd8090b2e7c6e0645235b1816),
Tree/Clone/Colony (0d15621def2c6b4d6d0b2a1f81a91868bbccb16a), Core Design
Doctrine (15e4e11a5cd58f2803ddf7258578c6aec59a9512), portable runtime
(2d3dfb2e88d694b612dd0553feddf616f9017d46). See R0 for exact links.

- TaskContext: principal, canonical Tree, optional Clone, task, execution
  context, generation and origin. Neither model nor Bark defines identity.
- BarkAttachment: independent presentation instance, requester/release/seat
  references, recipient, requested Tree hint and view generation.
- BarkListRequest: exactly requestId/treeKey/generation/action fields, action
  LIST_SESSIONS only. This accepts an in-memory dict, NOT native wire bytes.
- ListOperationReference: one original fixture binding. Compare with current
  fixture context and attachment, refuse mismatch or detach. Matching values
  return REFERENCE_MATCH_AUTHORITY_HOLD; no successful admission.
- detach(): creates a detached presentation value without mutating task or
  other surfaces. Not a real revoke, lease release, cancellation or proof
  a background job is running.

The reference explicitly separates UI-selected Tree label from canonical
Tree identity resolved by future custody; no alias registry or trusted
mapping is implemented here. No operation ID issuance, replay ledger,
native currentness evidence, actual subscription or task storage.
A future host must produce bindings independently; in-process values
are forgeable and never sufficient for authority. The public projection
uses static codes, no owner/Tree/task identifiers or private rows.

## HOW TO USE / VERIFY

python3 -B -m unittest discover -s tests/forest -p 'test_shared_context_b6r1.py' -v

21 focused semantic checks plus existing B1/B3/B4a/P1 regressions.
No DB opener, model adapter, subprocess, socket, dispatch callback,
network, new service or native host integration. Other code untouched.

## WATCH OUT FOR

This contract deliberately grants nothing, even with matching references.
No current title consent or approved masked-title wire. An unauthorized
request cannot cause storage/model IO because none is present. This does
not establish live deny-before-open ordering or actual revoke fencing.
Closing Bark is modeled only; task scheduling, cancellation, durable
clone coordination, presence lease and lifecycle are later work. Preserve
development and runtime Seasons as separate dimensions.

## NEXT / DECISIONS

Review exact head independently. Forest Core + ForestW + DOC1/2/3 align
actual request/recipient, owner/Tree, task context and C5 list/title
permissions before protected LIST_SESSIONS integration. AUTO recovery is
separate pure implementation lane; existing UI preview is not authority.
No duplicate core per widget, new production account, private DB, native
inference or workstation installation. Production HOLD.
