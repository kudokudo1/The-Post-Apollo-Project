# Trash++ // V2r Authority-Signed Source Service Grant (Fixture Only)

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
PROVIDER // OPEN AI // CHATGPT
STAFF ROLE // External DOC-compatible development; not verified live Hospital registered
ASSIGNMENT // Bind separately signed service policy approval to V2q pinned files and V2l enrolled capture key
SCOPE // GitHub stacked draft PR, own scripts/trash + tests/trash only. No Weather/research/MACHINE/Connections source writes, local host changes, production keys, signer enrollment, merge, Restore or Burn permission.

## IMPLEMENTATION

- New `scripts/trash/archive_v2_service_grant.py`: requires a strict canonical V2r **authority-signed service grant** with fixed copy-only audience/purpose, TEST_FIXTURE_ONLY origin, allowlisted source owner, root key ID, capture signer key ID, V2q service-file policy SHA-256, source-owner manifest SHA-256, matching generation, issued/valid time (maximum 24h) and explicit revocation status.
- A broker-supplied **EXTERNALLY_PINNED_TEST_ROOT** Ed25519 public key verifies the grant. It is not supplied by the untrusted capture request, nor chosen by the service-file policy. Unknown grant fields, bad signatures, wrong owner/key or generations, changed files/policy, wrong trust root, revoked/expired grant, and unsupported origin all refuse.
- The approved grant binds the V2l owner-key enrollment record to the V2q file/socket measurements. V2p continues to hold a Linux pidfd for the original Unix-socket peer. All linked checks are repeated at the final V2m **test-only SQLite commit guard**, after nonce + synthetic copy insertion and before COMMIT.
- Extended V2n's canonical broker request digest and V2m's **test fixture only** SQLite copy row with `service_grant_sha256`, written atomically with source claim hash, service witness, peer witness, nonce and synthetic payload. Read-only recovery reports the signed-grant digest without exposing any payload. Older V2q fixture rows remain explicitly `serviceGrantSha256=""`, not backfilled.
- The new grant is not part of the user's real V2a Archive database or V2i provenance receipts. It does not modify Quickshell, live SAVE SNAPSHOT, storage capacity bar, VERIFY CHAIN, Camera, GIO or Burn.
- The reply explicitly preserves `sourceProcessVerified=false`, `archiveCopyAuthorized=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`. A valid test root signature is not actual source authorization.

## HOW TO USE

No new UI button or desktop installation. GitHub CI generates ephemeral root/owner Ed25519 private keys in-memory, constructs a signed service grant covering its private temporary unit/script/socket fixture, opens a real Unix socket and calls the existing V2o handler. A success returns a deny-only synthetic receipt and stores only digest/linkage evidence. Production capture is still unavailable through this route.

## VERIFY

Adversarial tests exercise signed fixture grant matching, independent root signature, wrong capture key/file policy/source manifest/generation, expired/revoked grants, invalid fields, unsupported grant alone without pinned files, precommit revocation rollback and explicit unsiged legacy V2q records. Full Trash Python, JS Camera/snapshot/capacity/chain/Burn, Meta Apollo Grammar CI remain required, plus independent crypto/security review.

## WATCH OUT FOR

- **The authority root is an ephemeral test fixture, not an authorized independent production authority.** No actual Weather/research owner has approved or enrolled a signing key. A same-UID attacker with authority over test policy/keys can manufacture an internally valid demo claim.
- A signed grant binds an expected unit/script/socket policy and capture key, but it does **not** prove systemd launched that unit, that a specific script is the one executing in the peer's process, that imports and assets are immutable, or that the process holds the private signing key. Kernel SO_PEERCRED and pidfd are useful evidence, but not complete source service attestation.
- No durable externally anchored grant-version/revocation floor is provisioned. Revocation is enforced only for the currently supplied signed fixture and V2l's test enrollment generation. A production broker would require authority-owned release and revocation history with rollback refusal independent of the request.
- The final recheck is before the SQLite COMMIT; there is no atomic filesystem/kernel/SQLite operation guaranteeing a process continues to exist or files remain unchanged after COMMIT.
- The V2m/V2q synthetic transaction is **not** the real ArchiveStore; actual quota, SQLite schema, source-owner authorization, signed V2i receipts and crash-safe production admission remain blocked.
- This is **stacked behind open PR #1901 (V2q), itself stacked behind open PR #1897 (V2p)**. Do not merge/retarget without reconciling the latest main, parent heads and permission to merge.
- Weather/research/MACHINE/Connections retain their own ownership. The program may not create live services, UIDs, keys, or new owner scopes based on passing tests.

## CHECKLIST

- [x] Reconcile V2p/V2q pending and current Syntagma AGENTS/Hospital ownership
- [x] Strict authority-signed service grant and independently pinned fixture root
- [x] Bind V2q file/socket identity + V2l signer enrollment/generation
- [x] Persist service grant hash atomically with test nonce/copy and retain legacy empty evidence
- [x] Add adversarial scope/signature/expiry/revocation and commit-rollback tests
- [ ] GitHub CI final green and corrections
- [ ] Independent security review and source-owner/MACHINE signed handoff
- [ ] Operator approval for merge, host deployment and any live permission grant

## NEXT // V2s Implementation

**Authority-owned grant release/revocation floor and authenticated service-manager evidence.** After explicit Weather/research + MACHINE and Connections owner coordination, bind owner-controlled signing keys and service IDs to an independent trust/enrollment service with durable epoch/sequence revocation, verify dedicated Linux UID and systemd cgroup/unit, and integrate a separately reviewed *real* ArchiveStore nonce+receipt+quota transaction. Preserve deny-only for all synthetic code until those gates and owner permissions exist. No automatic Restore/retention/Burn.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2r-signed-service-grant-20261111
BASE // feat/trashpp-v2q-fixture-service-files-20261111 (PR #1901)
STATUS // GitHub-only draft; no verified live Hospital registration, no host/system/user data mutation
ROLLBACK // Revert V2r grant codec, optional broker grant gate, tests and additive **test-only** SQLite grant hash. All real Archive snapshots, source-owned writers, UI storage display and V2p/V2q semantics remain unchanged.
