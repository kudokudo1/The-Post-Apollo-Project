# Trash++ // V3a Production Cutover Readiness · Deny-Only Evidence Intake

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ · Universal Resource Lifecycle / Protected Archive
STAFF ROLE // External Hospital-compatible DOC; no verified live Hospital registration
ASSIGNMENT // Read-only readiness-gap assessment; no owner authority, production credentials or live Archive migration
SCOPE // New V3a pure module/test/workflow and this runbook; no modification to ArchiveStore, Trash UI, source agents, keys or shared U1 worker files

## IMPLEMENTATION

V3a continues the merged **V2w** independently owned read-only Ed25519 floor-file reader, **V2y** disposable ArchiveStore schema integration and **V2z** verified backup, staged schema and separate recovery rehearsal. A release file from V2w can be signed correctly without being protected from replacement by its own file owner. A V2z SQLite backup can be hash-verified without an independently protected/immutable off-host copy or an atomic witness of the concurrent source authority state. This work must **not** conflate these observations with real source-owner approval.

`archive_v3a_cutover_readiness_review.py` accepts only the exact existing V2w `require_current` result shape, V2z `verify_backup`, `rehearse_schema`, and `rehearse_recovery` result shapes and one explicitly **untrusted** cutover-observation structure. It validates all previous non-authorizing flags and the backup/staged/recovered cross-record bindings.

A caller cannot invent `approved`, `locked`, `trusted`, `productionAllowed`, external floor authority or a protected signing key in these inputs: unknown fields, malformed shapes, wrong types and positive authority flags refuse with fixed error codes. `signatureVerified=true` from V2w is recognized as a **reported test/read-only observation**, not a production signing/monotonicity proof. This reviewer performs **no signature verification itself**; it does not trust caller origin.

The review returns `PRODUCTION_CUTOVER_HOLD` with stable reason codes identifying:
- Production signer custody and source-owner permission absent.
- Independently protected monotonic release/revocation history, trusted clock and C3e/C5 owner/consent evidence absent.
- Same-UID V2z test backup without independent, immutable off-host custody.
- Writer freeze/cutover/rollback conditions not proven.
- Source revision, snapshot digest or record count changed after the backup.
- Active writers or new snapshots after the backup.
- Release epoch, sequence or content digest disagrees with the signed-floor observation; an observed off-UID floor remains insufficient for monotonicity.
- Expired or contested writer lease observation.

There is **no code path to green-light production**. Every returned review sets `productionAllowed=false`, `captureAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`, `automaticCutoverAllowed=false`, `automaticRollbackAllowed=false`, `deleteOriginalAllowed=false`, `safeActions=[]`. The original Archive, legacy records and every snapshot remain untouched by V3a.

## HOW TO USE

No desktop or live-host action. CI only:

```bash
python3 -B -m unittest discover -s tests/trash -p 'test_archive_v3a_cutover_readiness_review.py' -v
```

The tests construct an isolated *actual V2z disposable ArchiveStore*, write two **fake** owner records, seal a backup, create a staged V2y migration copy, verify an isolated recovery copy, and then hand the returned result objects to V3a. V2w source floor metadata is result-shaped synthetic input; no live source signing material or actual owner approval is supplied. The full existing Trash Python and JS workflows also run on changes under `scripts/trash` / `tests/trash`.

## VERIFY

A meaningful pass requires exact-head GitHub CI, the full Trash existing contract suite and independent NRS-2/source-owner review. Unit tests exercise valid V2w/V2z test result formats, untrusted off-UID floor, inconsistent backup/source revision, new writes, busy writers, release rollback, malformed schemas, Boolean-vs-integer confusion and forged positive authorization. This is **an evidence/requirements gap check**, not a secure authority or live migration implementation.

## WATCH OUT FOR

**Unresolved separate approval gates:**

1. **Source ownership / signing:** Weather/research and any other source owners must approve an identity, purpose, scope, signer custody, key rotation/revocation and release floors. MACHINE and Connections own their own downstream boundaries. No cross-owner authorization is implied by this PR.
2. **External monotonic authority and time:** An independently controlled service or hardware-backed monotonic witness must authenticate the signed release/revocation sequence and supply trusted clock/lease evidence. V2w file ownership alone cannot protect against restoring an earlier correctly signed floor.
3. **Backup:** Require independently protected immutable/off-device custody, an owner-authenticated backup manifest, retention policy, encryption key recovery, replay floors and verified separate restore. V2z's same-UID manifest is not that.
4. **Freeze/switchover:** A trusted, recoverable exclusive writer lease and explicit zero-writer state must precede cutover. Recheck DB revision, row counts, hashes and release floor *under that lease*. Any write after backup or lease expiry blocks automatic cutover. Publication of a new DB/version pointer and external source authority cannot be made one atomic SQLite transaction; define a stable handoff and deny on uncertainty.
5. **Rollback:** Preserve original and sealed backup, never overwrite a live database after new writes. Require an approved forward-replay/delta recovery strategy for any postcutover writes before allowing data to move backward. No unattended rollback from a self-hashed local manifest.
6. **C3e / C5 and user rights:** Live source/host/seat identity and separate one-use human consent remain independently owned. Restore and Burn are not capture permissions. No production ArchiveStore schema migration is authorized here.

The next separately authorized change must implement/verifiably integrate at least one of these real protected authorities under its own owner's approval, not silently flip a V3a boolean. Until then the technical safety action is **HOLD**.

## CHECKLIST

- [x] Read Syntagma and reconstruct merged V2w/V2x/V2y/V2z, current main and concurrent Trash U1 UI scope
- [x] Build non-executable strict V3a readiness-gap intake
- [x] Add actual V2z disposable ArchiveStore source/backup/stage/recovery tests and malicious claim refusals
- [x] Add isolated V3a workflow and source-owner handoff contract
- [ ] Exact-head GitHub CI and raw job-level verification
- [ ] Independent NRS-2 and source-owner review
- [ ] Operator acceptance and separately scoped authorizations for real signer, monotonic history, time, custody, writer freeze and real Archive migration
- [ ] Independently approved Restore and Burn

## NEXT / DECISIONS

Do not merge or activate without the operator's established authorization/review process. V3a is a **read-only test-derived readiness hold**. It does not change `ArchiveStore.save`, quotas, existing receipts, UI controls, source keys, real owner data or services. A future V3b may implement a small independently reviewed protected-witness reader, but only after its owning service/authority and permission contract are settled.

ROLLBACK // Revert only the new V3a module, test, workflow and this runbook. Existing V2z and every Archive snapshot remain untouched by V3a.
