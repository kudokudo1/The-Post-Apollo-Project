# 🏥💜 Connections ↔ Hospital // Read-only RECOVER request candidate, CI only

**PATIENT:** The-Post-Apollo-Project · **ROOM:** protected Connections/Hospital staffing issuer integration · **STAFF ROLE:** external Hospital-compatible DOC (live registration unverified).  
**CROSS-OWNER:** Hospital [PR #133](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/133), latest writer-owner [D1–D5 decision worksheet](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/blob/ef5ce8ab496418b20baadc63887bbb74a58711ec/docs/hospital-staffing-recovery-owner-decisions.md).  
**STATUS:** New CI fixture proposal; Hospital native release/writer protocol **unapproved**. Production HOLD.

## IMPLEMENTATION

A staffing COMMIT packet might be durably processed and then lose its reply. A socket timeout, missing ledger row, caller-provided \`REFUSED\` or \`COMMITTED\` blob cannot settle that outcome. Only the Hospital protected writer's authenticated durable original transaction journal could supply that evidence. The current candidate v13 ledger lacks enough independently bound history to prove it.

This isolated Connections-side addition **proposes** a new \`recover-original-commit-not-a-new-commit\` query record with exact canonical original \`PREPARE\`, \`PREPARED\` and \`COMMIT\` byte hashes, Room/action/Session, original requestNonce, writerInstance, signed grant digest/nonce, approval ID, original review hash, revision, source graph hash, scope hash, separate UUIDv4 query ID, 32-byte challenge and short test-only expiry. It reuses existing original-context validation from \`StaffingReceiptIdentityPreflight._source_context\` and compares exact proposed query bytes to reconstructed original context **plus separately supplied expected CI query ID/challenge**. Those expected values remain caller-provided fixtures, never independently trusted enrollment. The query is **not a COMMIT** and neither signs nor dispatches anything.

**No trust promotion:** \`candidate_query_ci_only\` accepts a **caller-selected fixture challenge and query UUID**, not a protected writer-issued challenge. It cannot prove freshness, one-use, signer origin or past outcome. A caller that controls all inputs can generate a matching candidate. \`inspect_candidate_query_ci_only\` gives shape consistency **only**. All protected writer, genuine challenge, replay protection, approved schema, C5 human consent, native read/write and production authority flags remain FALSE. \`run_native_staffing_recover_query\` ALWAYS refuses. It cannot parse a receipt, perform a native query or retry a grant.

This source file is intentionally under the Connections staffing issuer directory, **not** the Hospital PX protected writer branch; no source/SQL changes to #133.

## HOW TO USE

Only the new GitHub Actions CI job, with Hospital #133 source pinned to \`ef5ce8ab496418b20baadc63887bbb74a58711ec\` for disposable parser fixtures, may run the tests. No local activation or production socket client exists.

## VERIFY

- [ ] Exact-head 17 adversarial query tests PASS.
- [ ] Parent receipt and unknown-COMMIT adversarial tests PASS.
- [ ] Static no-authority check PASS and Grammar PASS.
- [ ] Exactly four new Connections-owned files.
- [ ] Independent Nurse 2 review before any trust or native release.

## WATCH OUT FOR

This candidate **does not declare** Hospital's final query protocol or receipt schema. In particular, Connections' earlier 15-field \`ci-v1\` receipt is unapproved; it is not the recovery response. Hospital PX owner D1/D2 must decide the journal/refusal fence; C3e owner D3 query semantics and D4 release/signing custody remain explicitly unapproved; D5 requires both sides to agree.

An approved read-only native RECOVER would need a separately enrolled protected writer release and kernel sender provenance (not arbitrary client-supplied expected UID), a one-use protected challenge / antirollback history, a pinned signed response identifying the exact original committed or terminal-refused record, and an independent grant issuer/root custodian. C5 actual live active-seat consent must have existed for the original staffing COMMIT. RECOVER cannot silently create it later.

**Outcome:** UNKNOWN until independently durable and authenticated COMMITTED / already-applied or terminal fenced REFUSED evidence is obtained. Contradictions remain security HOLD. No same-grant retry regardless of query matches.

## NEXT

Hospital protected writer owner and Connections issuer owner separately ACCEPT/REVISE/HOLD D1–D4, then decide D5 together with Nurse 2 review and the operator's final release acceptance. Any native code must follow a new owner-approved protocol and protected migration, not this untrusted builder.

## DECISIONS

CI-only, deny-only, draft. No installed signer, production keys, native service, protected database, SQL migration, human approval, local system change or release permission.
