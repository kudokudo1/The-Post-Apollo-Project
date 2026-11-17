# 🏥💜 Trash++ V3e // Offline Signed Retrieval Contract

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · Protected Archive Source Authorization
STAFF ROLE // External Hospital-compatible DOC, live Hospital registration not verified
ASSIGNMENT // Define and test fail-closed client-side verification of signed retrieval evidence
PERMISSIONS // GitHub scripts/tests/workflows/docs only; no local host writes, merge, key/service provisioning, external authority or Archive actions

## IMPLEMENTATION

V3d #2004 verified an offline V3b Archive witness against two separately signed candidate checkpoints. That was cryptographically meaningful but no proof that either checkpoint was independently stored or freshly retrieved. V3e adds an additional test-only retrieval signer distinct from V3d anchor, V3b witness, and V2w floor signers.

The new scripts/trash/archive_v3e_retrieval_envelope_review.py checks only caller-supplied synthetic metadata and signatures:

- Strict schema and domain-separated canonical 64-hex request nonce and requested minimum checkpoint sequence, exact source owner/grant binding.
- Ed25519-signed test responder envelope bound to the complete request SHA-256, nonce, prior checkpoint digest, presented checkpoint digest and sequence.
- Original V3d cryptographic review required for checkpoint chain, release, owner/grant, V3b witness and V2w floor evidence. Its rollback/fork/invalid history holds are preserved.
- Missing, truncated, malformed, forged or re-bound signed replies rejected; a signed reply below the caller's requested floor returns an explicit deny-only hold. Older checkpoint than the reference also remains on hold.
- Every result is RETRIEVAL_AUTHORITY_HOLD with no production, capture, Restore, Burn, retry, automatic rollback or deletion action. Caller-provided pin is NEVER authenticated external authority.
- No socket, TLS client, HTTP request, endpoint URL, persistent nonce registry, OS user, key store, signing operation, trusted clock or ArchiveStore modification exists.

The unit suite uses ephemeral Ed25519 keys and a cryptographic nonce generated in test memory. There is no real external authority, remote key provisioning or persistent high-water state.

## HOW TO USE

GitHub CI executes the dedicated suite:

    python3 -B -m unittest discover -s tests/trash -p 'test_archive_v3e_retrieval_envelope_review.py' -v

No end-user command or Post-Apollo UI change exists. Do not use these test pins for a real service or turn this verifier into a production permission decision.

## VERIFY

Positive synthetic cases demonstrate that a signed request-specific response tied to an exact V3d checkpoint is accepted for inspection only, yet still denies all actions.

Negative cases:
- No response or unrecognized status, malformed nonce or boolean sequence, unknown fields, noncanonical base64
- Response valid for a different nonce, request digest, grant or requested minimum sequence
- Different checkpoint digest, previous-reference digest, or checkpoint sequence, even when independently signed
- Forged responder signing key, reuse of V3d/V3b/V2w signer, or false production origin
- Signed stale response below a higher requested floor
- Propagated V3d rollback and forged V3b witness refusals
- Supposedly valid paired response/reference substitution and reuse of identical replies

### Crucial negative proof

A caller with control of both request and returned evidence can supply a consistent older signed history or replay an old request/response pair. Without a trusted separately controlled service, channel authentication, trustworthy caller challenge, persistent nonce replay store, verified clock and independently pinned high-water, these strings cannot prove remote freshness or custody. V3e deliberately reports all such properties FALSE even when its offline signatures are correct.

## WATCH OUT FOR

- No real networking yet. The contract rejects incorrect or missing response shapes; it does not connect to a network, validate TLS certificates, prevent DNS confusion or defend against network timeout by itself.
- No production keys or independent custody yet. Each pin is caller-supplied with a fixed test-only origin. Signature validity is not evidence of organizational ownership or compromise resistance.
- No durable anti-replay yet. A nonce comparison without a trusted generator and persistent replay window is not one-use authentication.
- No independent checkpoint writer yet. Genuine remote service must be controlled by an authority the Archive host cannot modify, and must preserve append-only or otherwise rollback-resistant high-water records.
- No transfer of source ownership. C3e/C5 credential/consent and Archive production writer/cutover permissions remain with separate owners and operator.

## CHECKLIST

- [x] Recheck Syntagma, Hospital protocol, mainline V3d #2004 and separate U8 Media ownership
- [x] Add isolated V3e offline request/response verification
- [x] Add hostile-input coverage and dedicated read-only CI
- [ ] Exact PR-head dedicated V3e and full Trash/Grammar workflows
- [ ] Independent Nurse 2 review and operator decision on mainline merge
- [ ] Approved separate trust domain, accountable authority owner and key management
- [ ] Real authenticated retrieval client+endpoint, independent writer/high-water storage, replay registry and failure handling
- [ ] C3e/C5 integration and protected cutover acceptance

## NEXT

After independently reviewing and landing this offline contract, the next implementation is the actual remote authority storage/writer and authenticated retrieval deployment, selected and owned by the operator/source authority, with independent key/clock custody and fail-closed outage/revocation/fork handling. V3e cannot infer the correct hosting trust domain.

## DECISIONS

Only four new V3e GitHub source/test/workflow/doc files. No existing Archive writer or Trash UI edits. No production authority, network access, host installation, live keys, source-owner writes, PR merge or live Hospital registration. Rollback: close the unmerged PR; remove only the four new V3e files if later reverted.
