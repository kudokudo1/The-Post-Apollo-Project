# 🏥💜 DOC 3 // Provisional Forest DELTA disclosure before C5 COMMIT

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Forest C5 · Streaming and revocation boundary  
**STAFF ROLE:** DOC 3 · Connections security implementation, reporting through Forest Nurse 2  
**CONNECTION:** External Hospital-compatible; live registration not verified  
**SOURCE:** Additive Connections-owned disposable CI only  
**PRODUCTION:** Forest / Sign-In / TimeW HOLD

## IMPLEMENTATION // Fundamental event order

The existing Forest owner B3 generator yields an uncommitted assistant output chunk with \`event=DELTA\` and \`provisional=True\` to its caller **during** model streaming. Its final \`pre_commit\` authorization callback runs **after the model has finished** and only before B3 inserts the durable reply. When \`pre_commit\` returns false, no assistant reply is saved and B4f's opt-in outbox records the original attempt as locally ABORTED atomically. This is a useful write barrier, but it does **not** retract text already delivered through the generator.

The Forest owner already covered part of this ordering in its B4c test \`test_revoke_after_delta_before_final_policy_check_refuses_reply\`. This additional DOC 3-owned test combines the **current B4f local outbox** with that existing streaming behavior to demonstrate the disclosure-vs-commit boundary using disposable SQLite and fake output.

### What the new test demonstrates

- A \`DELTA\` string is observed before final COMMIT authorization. A subsequent denial, revocation flag or generator cancellation leaves local attempt ABORTED and B4f outbox LOCAL_ABORTED; previously yielded bytes remain in the caller's memory.
- A stream that emitted a \`DELTA\` but then ended incomplete or with mismatched COMPLETE text also leaves a local ABORT, **after** provisional text has been exposed.
- If the original SQLite COMMIT succeeds, B4f records LOCAL_COMMITTED in the same transaction, but a synthetic held-permit terminal callback that fails or raises yields UNKNOWN_HOLD with no client COMMITTED event. Earlier DELTA text has already escaped.
- Even a fully successful local synthetic path exposes DELTA **before** B3 commits, confirming that \`provisional=True\` describes a source-state flag, not a confidentiality guarantee.
- A denied/aborted reservation cannot be silently rerun on the same user turn. That protects duplicate execution but cannot undo text already seen.
- No private prompt or assistant text is returned by the B4f local terminal inspector; the leak is the intentional **streaming event** interface, not outbox metadata.

The tests use *only* artificial text. No real model execution, personal chats, installed identities, signing keys, socket, local machine configuration or production change.

## HOW TO USE // Test-only

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_provisional_delta_disclosure.py' -v

The test uses a temporary B1/B3/B4f SQLite database, fake injected model streamer, existing Forest \`exchange()\` and \`pre_commit\` hook, and a fake B4c terminal permit object. Its assertions are **negative security evidence**; do not interpret the test as providing or recommending a production workaround.

## VERIFY

- 12 new real B3/B4f synthetic streaming-versus-final-authorization tests.
- Inherited 24 B4f outbox, 15 B4c held-permit, 21 B4e lineage and 18 B4d recovery tests.
- 90 expected focused cases, source compilation and no new production module/actuation.
- GitHub exact-head CI/raw logs and Forest Nurse 2 **pre-merge** source review required.

## WATCH OUT FOR // Genuine operator/Forest product decision

A client can display or persist a streamed DELTA before the final security check. A terminal COMMIT receipt, revocation acknowledgment or local ABORT record cannot retroactively hide those bytes.

Two future **proposals**, not decisions:

**A. Protected buffer until final authorization (safer default for C5-protected chat):** The trusted Forest host buffers model output, holds a single-operation protected permit through COMMIT and independently authenticated terminal settlement, then discloses the completed answer. This removes incremental live-stream responsiveness and requires memory/size bounds and careful handling of post-commit ACK loss. Never disclose after a merely local COMMIT while C5 still UNKNOWN_HOLD.

**B. Explicit separate provisional disclosure consent:** Require a separately scoped, revocable, user-visible approval for revealing provisional tokens. It must distinguish \`may disclose provisional text\` from \`may save/commit response\`, enforce origin/seat, sender/recipient and revocation ordering, and explain that already seen bytes cannot be recalled. This requires a new operator-accepted product/security policy and cannot be inferred from a generic GENERATE grant.

**Recommendation (PROPOSED, not operative):** For protected Forest C5 conversations, default to **no provisional DELTA release** until the independently authenticated terminal and disclosure policy are complete. Forest Core and ForestW owners should weigh UX/streaming behavior; Forest Nurse 2 routes any cross-Connections security implications to Connections Nurse 2. This is not permission to change Forest code.

Separate blocker: DOC 3 [native terminal evidence RFC](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7099402181) remains awaiting Forest ownership response; C3e/C4b protected enrolled original writer and independently custodied journal still do not exist here.

## CHECKLIST / NEXT

- [x] Existing Forest B3 stream, B4f outbox and B4c revocation test behavior inspected.
- [x] Additive Connections-only negative streaming tests created; Forest owner code untouched.
- [ ] Dedicated exact-head CI and raw log verification.
- [ ] Forest Nurse 2 independent pre-merge review.
- [ ] Forest Core/ForestW + operator decision on buffering vs separately consented provisional disclosure.
- [ ] Native protected writer C5 issuer/receipt integration and genuine revocation serialized before deployment.
- [ ] Final operator acceptance.

## DECISIONS

No policy selected. No Forest ownership transfer, native installer, key, personal data, UI, service, DB migration, or production authorization. Existing B4f and C5 V1 semantics remain untouched. **PRODUCTION HOLD.**
