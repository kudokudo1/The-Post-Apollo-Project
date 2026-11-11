# Trash++ // V2w Read-Only Externally Owned Release Floor

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible GitHub development, not verified live Hospital-registered  
ASSIGNMENT // Refuse stale/revoked signed releases against a separately owned, read-only on-disk high-water checkpoint  
PERMISSIONS // GitHub scripts/trash, tests/trash and docs; draft PR and tests. No local computer modifications, source-owner services, key provisioning, merge, production Archive permission, Restore or Burn.

## IMPLEMENTATION

- Added `scripts/trash/archive_v2_external_floor_reader.py`, a standalone **read-only** reader of the exact filename `trashpp-v2w-authority-floor.json` under an operator/source-owner-supplied absolute directory. Neither the directory nor the root public key nor expected UID comes from a source request.
- Opens each directory component with Linux `O_DIRECTORY | O_NOFOLLOW`; opens the authority file with `O_NOFOLLOW` and limits reads to 4 KiB. Requires regular single-linked file, correct owner, non-group/world-writable root and file, stable fd/path inodes and metadata before/after reading. Rejects missing files, symlink substitution, hardlinks, writable modes, oversized files and same-bytes replacement after the initial reader is pinned.
- Strict canonical ASCII JSON envelope and fixed field schema. Ed25519 signature under separately supplied pinned public key binds owner, copy-only purpose/audience, root key ID, epoch, sequence, exact release SHA-256, V2r grant SHA-256, issue/valid times and revoked flag. Rejects duplicate/unknown fields, malformed signatures and bad canonical form.
- When asked to `require_current`, it reopens and validates the **same pinned file**, rejects changed inode/bytes and expired/revoked record, then compares against the V2s private fixture release ledger's current signed head. Mismatched release sequence, release digest or grant digest fail closed. Source-owner rotation requires a new explicitly pinned reader.
- **Production isolation:** with `test_fixture_only=false`, expected filesystem UID must differ from the calling process's UID and public key must be explicitly tagged `EXTERNALLY_PINNED_SOURCE_ROOT`. CI only tests same-UID private fixtures tagged `EXTERNALLY_PINNED_TEST_ROOT`. A matching signed file is **not** an independently provisioned authority or trusted monotonic store just because a caller passed an alleged root key.
- All results explicitly `externallyProtectedMonotonicAuthorityVerified=false`, `trustedClockVerified=false`, `sourceAuthorityVerified=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`. The reader cannot generate private keys, write the floor, update service state, touch ArchiveStore or grant permission. It is intentionally **not connected to V2o test broker or actual ArchiveStore** until source-owner approval.

## HOW TO USE

There is no new Trash++ desktop control or installation. Python CI builds a private disposable source test directory, writes an ephemeral signed checkpoint with an in-memory Ed25519 test key, and exercises the standalone reader. It compares the checkpoint to the existing signed V2s test release history. No real source service or key is contacted. Existing Archive SAVE SNAPSHOT, actual capacity bar, VERIFY CHAIN and Burn are unchanged.

## VERIFY

New adversarial tests cover successful deny-only matching; same-bytes new inode and signed-file replacement; missing file; wrong root signature; root/key re-use; same-UID refusal in nonfixture mode; symlink/hardlink substitution; file/root writable permissions; duplicate/noncanonical JSON; wrong owner/grant; expiry and signed revocation; signed release head advancement with stale floor; incorrect scope/schema/type/time; absence of live writer or ArchiveStore integration.

The complete Trash Python and 40 JavaScript contracts and Meta Apollo Grammar GitHub workflows must pass. Independent security and live owner-provisioning review are separate.

## WATCH OUT FOR

- **This reader is not a protected authority.** A signed document proves possession of the supplied signing key, not that the key is held by an authorized source owner. The caller must obtain the correct public key and expected filesystem UID through an independently approved source-owner enrollment process.
- A separately owned file protects against a *less-privileged broker user* editing that pathname only if the real OS grants and service boundaries are correctly deployed. It cannot prevent its file owner or root administrator from replacing the directory/database with an older *validly signed* file. The directory/file identity recheck protects one reader instance, **not** durable anti-rollback across restarts.
- The reader verifies time values against the supplied `now_ms`, but does **not** authenticate the clock. No trusted time authority, off-machine monotonic witness, append-only remote release history, organizational signer custody or protected owner-held writer has been established.
- It rejects symlink components but does not prove immutable parent directories, trusted package dependencies or systemd's loaded script. Additional threat modeling and native Fedora Silverblue/SELinux tests are needed before any real deployment.
- The V2s test release SQLite, V2t checkpoint, V2v D-Bus reader and real ArchiveStore remain **separate**, not one atomic protected transaction. This module does not change source signing or consume a real nonce or authorize copying.
- Weather/research, MACHINE/TimeW and Connections/Identity retain their separate owners. No source-owner records or host services were changed.
- All sources and statuses are from GitHub. Browser session is Hospital-compatible but not verified as a live Hospital Worker attachment or assignment.

## CHECKLIST

- [x] Rechecked current `main`, V2v merge, canonical Syntagma AGENTS/Hospital and competing PR ownership
- [x] Read-only off-UID root and pinned Ed25519 floor contract
- [x] Exact schema, inode/permission and release/grant binding checks
- [x] Synthetic denial/forgery/rollback and filesystem substitution tests
- [ ] Full CI and any corrective follow-ups
- [ ] Independent owner/source trust and OS security review
- [ ] Operator authorization for any future local installation, PR merge or source service interface

## NEXT // V2x Implementation

**Externally approved monotonic witness and atomic capture admission interface.** Following Weather/research + MACHINE/Connections owner handoff, provision an actual distinct service UID and protected signer enrollment outside the broker's control; define signed append-only release/revocation history (with off-host monotonic witness and trusted clock), then review how an actual ArchiveStore capture rechecks authoritative policy at quota + nonce + signed provenance commit. First test the lifecycle with a disposable demo owner; do not enable Restore/Burn.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2w-readonly-external-floor-20261111  
BASE // current main at branch creation `e16324465f8dd2dcb748506f43fa95546cd170d1`  
STATE // GitHub-only, deny-only, unmerged draft until operator's explicit decision  
ROLLBACK // Revert only V2w reader/tests/docs. Existing user Archive SQLite, all snapshots, V2v read-only manager, Camera/GIO and Quickshell state remain unchanged.
