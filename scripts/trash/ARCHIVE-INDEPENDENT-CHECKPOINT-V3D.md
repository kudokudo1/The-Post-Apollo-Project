# 🏥💜 Trash++ V3d // Independently Signed Checkpoint Verifier

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · Protected Archive Source Authorization
STAFF ROLE // External Hospital-compatible DOC; live Hospital connection not verified
ASSIGNMENT // Define and test the separate-trust-root verification boundary after V3c mainline recovery
PERMISSIONS // Repository scripts/tests/workflow/docs only. No live writes, OS provisioning, enrollment, service or production authority.

## IMPLEMENTATION

V3c (#1990 mainline recovery) demonstrated that a kernel-isolated Linux UID can keep a broker from opening a private SQLite witness file, but root or the privileged owner can restore an older internally consistent database. Neither a signature nor a separate on-host UID prevents rollback of both the alleged current and previous high-water records.

V3d introduces offline cryptographic checkpoint verification in scripts/trash/archive_v3d_external_checkpoint_review.py:

- Verify a signed Archive-side V3b witness under its separately supplied test public key.
- Verify BOTH the prior pinned checkpoint and the presented checkpoint with a third ephemeral test Ed25519 key, distinct from the Archive witness and V2w floor signers.
- Domain-separate canonical checkpoint signatures, use fixed bounded strict schemas and exact owner/grant binding.
- Compare signed checkpoint counters and predecessor digests; bind each forward V3b witness to the exact prior checkpoint's pinned witness SHA. Detect older signed replay, same-counter fork, missing history, broken signed witness predecessor, mismatched witness digest/counter, release rollback, release content fork, revocation reversal and floor disagreement.
- Return immutable INDEPENDENT_AUTHORITY_HOLD with all capture, production, restore, burn, delete-original, retry, rollback and safe actions denied regardless of signature validity.
- Expose no CLI, database, network client, key storage, host permissions, service, actual snapshot reader or writer.

The unit tests use three independently generated ephemeral private signing keys in process memory. No real signer, host UID, process or remote log is configured. Existing V3a/V3b/V3c behavior remains untouched.

## HOW TO USE

GitHub CI only:

    python3 -B -m unittest discover -s tests/trash -p 'test_archive_v3d_external_checkpoint_review.py' -v

Do not wire into any live Trash control. This contract explicitly cannot authorize real Archive capture or deletion.

## VERIFY

- Successful separately signed prior/current candidate checkpoints, including a forward linked sequence, still deny all operations.
- A newer pinned reference exposes a rollback of an older valid signed checkpoint.
- Same checkpoint sequence with different signed digest, invalid predecessor, gaps, witness mismatch, wrong signer, key reuse, wrong owner/grant, revoked-to-live, release downgrade and malformed/spoofed claims refuse or hold.
- NEGATIVE PROOF: replacing both caller-provided previous and current checkpoints with an older valid signed pair may still pass cryptographic verification. Offline inputs alone do not authenticate their own retention, the reference pin, real independent administration, trusted time or remote durability.
- Full Trash Python/JS and grammar suites must pass on exact head. Security implementation needs independent source-owner review.

## WATCH OUT FOR

### What an actual independent authority needs

A different permission on the SAME host is insufficient against host-root compromise. A legitimate production design requires source-owner-operated, physically or administratively independent trust and durable records that the local Archive host cannot rewrite or erase. This is an ownership/authorization dependency, not a Python flag.

A future separately approved service should:

1. Provision the authority's signing key outside Archive host/root control, with explicit accountable owner and key rotation/revocation policy.
2. Maintain append-only / rollback-resistant release history or a separately pinned latest high-water in an independent trust domain. Make loss of that record fail closed, and distinguish a stolen signer from lost history.
3. Bind receipts to fixed owner, grant, release epoch/sequence/digest, current V3b witness hash, prior checkpoint hash, revocation and a trusted issuance clock. Refuse conflicting same-version writes.
4. Define authenticated retrieval / anti-replay and retention policy; the client must not accept arbitrary caller-supplied prior checkpoints or pins as trusted.
5. Provide independent restore/recovery witness and incident response; block activation after signer, clock, replica or history disagreement.
6. Integrate C3e attested process identity, C5 independent one-use human consent, source-owner revisions, writer-quiescence, backup custody and cutover acceptance through their owning teams.

V3d does not establish any of these operational prerequisites. Its metadata names and successful signatures are only offline test evidence.

### Threat model

| Attacker / failure | V3d can show | What remains unproven |
| --- | --- | --- |
| Forged signed checkpoint | Ed25519 verification refuses | Independent key provisioning |
| Same-sequence fork against pinned reference | Semantic hold | Reference is really pinned independently |
| Replay of older signed receipt | Holds when compared with a newer trusted reference | Local attacker cannot replace both inputs |
| Archive root restores old SQLite DB | External signed floor could reveal drift | External service, storage and retrieval not built |
| Root steals source/authority signing key | No safe outcome | Off-host custody, key revocation and incident handling |
| Host loses external authority connection | No live client or decision | Network fail-closed policy and independent recovery |
| Owner requests real Burn | Unconditionally denied | Explicit source-owner permission and independent C5 consent |

## CHECKLIST

- [x] Mainline V3c #1990 and separate UI/Media owners inspected
- [x] Scoped offline two-signer verification; no shared source or backend mutation
- [x] Negative regression matrix for signed replay/rollback/forks and paired input substitution
- [ ] Exact-head dedicated V3d + Trash + grammar workflows, raw-log verification
- [ ] Independent Nurse 2 security and source-owner protocol review
- [ ] Operator approval of remote authority owner, hosting, custody and trust-root bootstrap
- [ ] Production implementation / staged recovery / C3e+C5 integration in separately authorized assignment

## NEXT

With V3d checked, the next implementation, not a synthetic authority claim, is to coordinate a source-owner-owned independent checkpoint writer/storage service plus authenticated client retrieval, bootstrap trust and loss-of-service refusal. Those are outside this bounded offline review and require operator-approved authority/hosting and ownership boundaries.

## DECISIONS

Draft-only repository work. No production activation, main merge, local machine writes, real Trash/Burn, source-key enrollment, independent network endpoint or live Hospital registration. Revert only the four new V3d files to undo. Nothing in V3a/V3b/V3c or the Camera UI must be changed.
