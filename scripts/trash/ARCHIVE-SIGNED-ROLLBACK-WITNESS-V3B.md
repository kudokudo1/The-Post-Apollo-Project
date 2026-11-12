# 🏥💜 Trash++ V3b // Signed Rollback Witness · Test-Only Read-Only Contract

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · Archive Source Authorization
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration not verified
ASSIGNMENT // Recognize rollback/equivocation in separately signed synthetic release witnesses
SCOPE // Pure read-only verifier, disposable crypto tests, standalone workflow, handoff; NO signer service, live authority, ArchiveStore, Trash UI or source-owner changes

## IMPLEMENTATION

V2w (#1926) already validates an owner-pinned Ed25519 signed release-floor file and checks local fixture release history. V3a (#1941, merged at `86edfcbf69257783b3dce012d25c27c29775dc29`) supplies a read-only deny-only production-readiness gap contract. Both explicitly fail to prove an externally anchored, independent monotonic high-water mark.

V3b adds a **pure** Ed25519-verifying *fixture-only* witness comparator. It accepts two already supplied separately signed test witness envelopes: a previously pinned anchor and a current witness. It checks a third, actual V2w floor *response shape*, expected owner/grant from an independent call parameter, and a separately pinned TEST public root (which must differ from the observed V2w floor-signing key). It has no filesystem operations or signing key storage.

The witness signature commits to a domain-separated schema, owner, grant SHA-256, release epoch and sequence, V2w floor SHA-256, signed release SHA-256, witness counter, predecessor witness hash, and revocation status. Signatures are verified over deterministic canonical JSON. **No caller-provided production root is supported**; only `EXTERNALLY_PINNED_TEST_ROOT` is accepted.

The independent comparison diagnoses:
- A valid but older witness sequence than a previously anchored later version.
- Two different signed witnesses claiming the same counter (equivocation).
- Missing, gapped or divergent predecessor hash, including newer counter with an unrelated lineage.
- Older release epoch or lower release sequence within one epoch, and a changed release digest with the same release version.
- A mismatch between the witness's release-floor epoch, sequence, file digest or release digest and the existing V2w observation.
- Revocation witnessed in either previous or current entry, including an attempted return from revoked to unrevoked.
- Same-UID fixture floor or a read-only off-UID floor observation that still lacks independent monotonic proof.

Every result, including matching cryptographically valid synthetic witnesses, reports `MANUAL_AUTHORITY_REVIEW_REQUIRED`, `externalAnchorAuthenticated=false`, `monotonicStorageVerified=false`, `trustedTimeVerified=false`, `productionAllowed=false`, `captureAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`, `automaticRetryAllowed=false`, `automaticRollbackAllowed=false`, `deleteOriginalAllowed=false`, `safeActions=[]`. A matching signature can NEVER authorize Archive activity.

## HOW TO USE

No new desktop UI, service, private key, ArchiveStore operation, or operator CLI. On CI only:

```bash
python3 -B -m unittest discover -s tests/trash -p 'test_archive_v3b_signed_rollback_witness.py' -v
```

The tests generate disposable private Ed25519 keys in *memory only*, exercise the real existing V2w signed file and V2s release-history fixture under a disposable private test directory, and then sign/replay/alter separate witness claims. No real Weather/research, MACHINE, Connections/Identity service, personal Archive, or host signer is touched.

## VERIFY

Require exact-head GitHub Actions success for new V3b tests, V2w and V3a regressions, full Trash launcher suite, and Meta Apollo Grammar. Raw job steps must actually complete. Nurse 2 independent review and source-owner/authority signoff remain separate gates; a merge is not equivalent to either.

## WATCH OUT FOR

**This is NOT the independently protected authority requested for production.** The prior anchor is passed as ordinary test data, not retrieved from a trusted off-host monotonic service or hardware protection. An attacker who can replace BOTH the current signed witness and its allegedly pinned prior checkpoint can still present an internally consistent older history. The signature proves only that the test signer signed a statement, not that the statement is current, complete, independently stored, or organizationally authorized. The tests deliberately show this limitation and keep permission denied.

A production authority would still require: independently controlled source-owner signing hardware/keys, witnessed persistent monotonic/revocation floor that the broker cannot rewrite, authenticated audience/owner/lease and trusted clock, source-owner permission, off-host backup custody, verified host/process/seat (C3e/Connections), human consent (C5), and lossless writer freeze/cutover/rollback. None of these is implemented or requested here.

The V3b code intentionally makes no changes to `archive_store_v2.py`, V2w reader, V2s durable local fixture history, V3a readiness, any existing Trash UI/U1 work, native systemd service, or machine settings. Capture, Restore and Burn remain separately scoped and disabled for this contract.

## CHECKLIST

- [x] Recheck Syntagma authority/Hospital rules, current main and V3a merge
- [x] Keep concurrent Trash U1 UI and Connections/MACHINE owners untouched
- [x] Build pure signed witness checker with explicit negative trust outputs
- [x] Test replay, fork, chain gap, epoch/sequence rollback, revocation and signing-root mismatch with actual disposable V2w floor observations
- [ ] Exact-head V3b CI and full Trash regressions, raw job proof
- [ ] Independent Nurse 2 and source-owner review
- [ ] Operator PR/merge/final acceptance
- [ ] Future separately owned monotonic authority, trusted clock and real service custody

## NEXT / DECISIONS

After exact-head CI and independent review, the next independently scoped V3c authority milestone should define and implement the **protected immutable/monotonic high-water store** under the actual source owner's approved infrastructure, with a real read-only query that cannot be rolled back by the broker. Do not treat V3b witness signature verification as production enrollment, protected storage, human consent or authorization.

No local workstation modification, live signing key, ArchiveStore migration, production grant, Restore/Burn action, PR merge or Hospital registration performed by V3b development. Reverting only the four new V3b files fully rolls back this isolated change.
