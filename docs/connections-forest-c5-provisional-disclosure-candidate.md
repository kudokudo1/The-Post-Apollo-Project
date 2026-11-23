# 🏥💜 DOC 3 // Forest C5 separate provisional-disclosure candidate, v0 (NO PERMISSION)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Forest C5 · separate streaming disclosure authority  
**STAFF ROLE:** DOC 3, Connections C5 security development; reports to Forest Nurse 2  
**PROVIDER / CONNECTION:** OPEN AI // CHATGPT · external Hospital-compatible, no live registration verified  
**STATE:** PROPOSED / CI-ONLY / UNINSTALLED / DENY-ONLY  
**PRODUCTION:** Forest / Sign-In HOLD

## IMPLEMENTATION // What bytes and process boundaries matter

The existing Forest B3 generator can yield \`DELTA(provisional=True)\` to its direct caller *before* its final B4b/C5 pre-COMMIT check. If consent is denied after that yield, B3/B4f can leave the original reply locally ABORTED without recalling bytes already seen. DOC 3 merged PR #2285 confirmed this with disposable B3/B4f tests, 90/90 PASS and retrospective Nurse 2 scoped PASS.

A **COMMIT_GENERATE** operation permits a future trusted host to persist one reply only when protected C5 admission and terminal settlement are actually established. It is *not* permission to show provisional tokens. This candidate makes the disclosure operation a distinct narrow family:

- **Proposed action / phase:** \`DISCLOSE_PROVISIONAL\`; its own candidate audience \`postapollo.forest.provisional-disclosure.candidate-v0\`, never the COMMIT v1 audience or an Identity/Hospital/TimeW signing namespace.
- **Exact signed parent context:** SHA-256 of the existing unchanged V1 COMMIT intent wire, plus exact principal, Tree, sessionId, original userTurn, attempt, model, expected revision and consent epoch. Hash equality compares caller-supplied bytes; it does NOT prove the parent was authentically signed or issued.
- **Separate disclosure operation identifiers:** \`disclosureRequest\`, \`disclosureCandidateId\`, \`disclosureNonce\`; none can reuse each other or COMMIT \`request\`, \`grant\` or \`challenge\`. These are only candidate-correlation strings, NOT tokens or approved permits.
- **Intended output recipient:** \`recipientInstance\`, \`recipientReleaseSha256\`, \`recipientSeatEpoch\`; all are untrusted suggestions until independently bound to a live process/seat by DOC 1/DOC 2 and C5.
- **Candidate scope limits:** \`maxBytes\` (structurally capped at 16000, matching the reviewed B1 body cap); positive \`disclosureEpoch\`; issued/expires times bounded within the original V1 COMMIT lease. Bounds apply ONLY to static candidate syntax, not cumulative stream accounting, protected clock, one-use or revoke ordering.
- No consent signature, issuer PIN, native writer key, global antirollback head or live actual revoke state is provided or accepted by this module.

\`ForestC5ProvisionalDisclosurePreflight.inspect_untrusted_disclosure_candidate()\` verifies strict canonical JSON, exact known fields, original V1 scope, independent operation IDs, recipient and clock/size limits. It returns **only** an untrusted candidate digest and all protected authorizations FALSE. It cannot create a permit.

\`block_provisional_delta()\` accepts one internal synthetic B3 DELTA event and always returns \`emitEvent=None\`, \`emittedBytes=0\`, \`safeActions=[]\`, every authority bit FALSE. It never returns or logs the text. It is an illustrative fail-closed **downstream sink** boundary, not a buffering engine, live policy callback, revocation watcher or UI component. If the original Forest B3 generator has already yielded a DELTA to its direct caller, this function cannot erase the caller's in-memory copy.

This addition does **NOT** change the Forest B3 writer, B4f/B4g outbox, Ollama transport, ForestW UI, C3e/C4b identity sources, legacy COMMIT V1 wire, or current native sign-in. No daemon, service, database or credential store is created. It is not silently made canonical.

## HOW TO USE // Disposable CI/reference only

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_provisional_disclosure_preflight.py' -v

Expected focus: 26 adversarial cases plus inherited C5 V1/Forest B4f/B4c/B4g regression tests. The tests use synthetic text and a disposable B1/B3/B4f SQLite file for one actual B3 generator-to-test-sink demonstration. No provider call or protected stored data.

A real ForestW option should **not** be exposed yet. Do not tell the user that a C5 disclosure permit exists. No current UI is authorized to enable protected token streaming.

## VERIFY // Safety properties

1. A COMMIT v1 wire cannot masquerade as a disclosure candidate; the same \`grant\` or request ID cannot be reused.
2. Cross-principal, Tree, session, original attempt, user turn, model, revision or consent-epoch substitutions are refused. A hash of a *different* original intent fails even with otherwise matching fields.
3. Duplicate JSON keys, noncanonical serialization, unexpected permit/consent/response fields, Boolean counters, invalid recipient, improper lease, future/expired candidate or oversized bounds are refused.
4. A fully matching candidate never grants streaming. A syntactically valid B3 \`DELTA\` is dropped and not included in the return value.
5. The original B3 generator can still yield bytes internally. In a disposable demonstration, the C5 reference suppresses an external sink even when the later final COMMIT check denies; local Forest B3/B4f abort remains unchanged. This is NOT an approved host integration.

## WATCH OUT FOR // Real native implementation is a separate owner-approved workstream

**No real provisional-disclosure authority exists here.** Before any live release, Forest Nurse 2 and Forest Core/ForestW must agree with the operator on a product policy, and Connections Nurse 2 / DOC 1/2/3 must define the actual custodian.

Suggested requirements for the **future installed host**, not implemented:

- Require separate, authenticated, human-approved \`DISCLOSE_PROVISIONAL\` *and* independent \`COMMIT_GENERATE\` where relevant. Neither grants the other; different roles/audiences, independent replay and revocation fences.
- Authenticate recipient process/seat/release and original B3 session/attempt. No inherited anonymous socketpair SO_PEERCRED or caller-supplied pin shortcut.
- Perform the protected disclosure admission **before the first external byte**. Serialize each outbound chunk with the issuer's revoked/lease state, accounting for in-flight output. Revocation ACK cannot truthfully assert no subsequent bytes unless the host/recipient output path is fenced and all pending sends accounted for. Previously emitted text cannot be recalled.
- Bind one bounded stream to a one-use disclosure permit and independently enforce cumulative bytes (UTF-8 encoding), target identity, deadline and revocation epoch. Local \`maxBytes\` syntax and caller clock cannot enforce these.
- Avoid one remote roundtrip per token. A future host can use a short-lived *independently authenticated local lease plus serialized revocation invalidation* on the existing Forest process, if approved and proven. Never substitute a stale in-process cached truth for a durable revocation acknowledgement.
- Explicitly select the policy for late/revoked/missing terminal COMMIT receipts, UI display of already streamed text, cancellation, logging/persistence of provisional text, and replay after crash. Even successful disclosure cannot authorize a durable DB reply.
- The separate [native terminal evidence V2 RFC](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7099402181) is still unaccepted. Do not silently modify V1 \`storageTxnId\` semantics or treat local B4g marker as independent trust.
- Reuse Forest's existing resource-governor/performance data; do not create a constantly running second AI service just for permission checks.

## CHECKLIST / NEXT

- [x] C5 exact-session V1, Forest B3/stream, B4f/B4g and historical negative streaming tests inspected.
- [x] Separate source-only deny-only candidate and drop-only test gate, no Forest owner writes.
- [x] Strict original session/attempt/intent binding and recipient/lease constraints.
- [ ] New exact-head CI, raw logs, Nurse 2 pre-merge review.
- [ ] Operator + Forest Core/ForestW streaming policy agreement.
- [ ] Independently enrolled native C5 disclosure issuer/recipient/writer and revocation ordering.
- [ ] Original writer terminal V2 evidence contract and native trials.
- [ ] Explicit final production acceptance.

## DECISIONS

This candidate is NOT permission issuance. Neither streaming nor COMMIT is enabled, V1 stays unchanged, and Forest production remains HOLD. Owner decision and Nurse 2 independent review precede any merger or live connection.
