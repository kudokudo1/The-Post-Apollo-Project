# Trash++ // V2s Durable Signed Service-Release Floor (Fixture Only)

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible developer; no verified live Hospital registration  
ASSIGNMENT // Authority-signed release sequence, sticky grant revocation, precommit stale-release refusal  
SCOPE // GitHub-only stacked draft, files under scripts/trash and tests/trash. No Weather/research/MACHINE/Connections edits, host deployment, credentials, PR merge, Restore, retention or Burn rights.

## IMPLEMENTATION

- New `archive_v2_service_release_history.py` verifies an authority-signed **V2s release record** against an independently supplied *EXTERNALLY_PINNED_TEST_ROOT*. Fixed canonical schema binds existing demo/Weather owner, copy-only audience, signing-root ID, V2r service-grant digest, contiguous release sequence, exact predecessor release digest, issue/validity times and revocation state. Ed25519 and strict unsigned-field rejection are inherited from the established verifier dependency. No self-published root.
- A separate **TEST-ONLY** 0700 private SQLite history stores per-owner highest accepted sequence, release checksum, grant checksum, root fingerprint, issuance floor and revoked state. All sequence/head, retired-grant and revocation updates share one `BEGIN IMMEDIATE` transaction with FULL synchronous and rollback journal. Skipped/older sequence, wrong predecessor, changed root and issuance rollback refuse. Replaced grant digests and explicitly revoked grant digests are permanently retired within this synthetic ledger.
- A broker-supplied release record is checked against the currently enrolled authority-owned *test ledger* at initial V2o request preflight **and again inside the V2p final pidfd / V2q files / V2r grant precommit guard**. If the high-water sequence/revocation changes before the final check, the V2m synthetic nonce and payload record both roll back.
- The canonical V2n request binding and V2m synthetic copy row now include an additive `service_release_sha256`; read-only recovery returns only metadata, with no payload or new capabilities. Older fixture records remain explicitly `serviceReleaseSha256=""`, never misrepresented as release-pinned.
- The new release history is **not** the real ArchiveStore or a host trust anchor. The release fixture ledger is separate from the test snapshot DB. Every response remains captureAllowed=false, productionAllowed=false, archiveCopyAuthorized=false, sourceProcessVerified=false, restoreAllowed=false and burnAllowed=false. No live daemon, socket activation, service unit, private signer or source files are created.

## HOW TO USE

No new Quickshell buttons or local installation. Synthetic tests enroll a release signed by an in-memory ephemeral root, read its high-water mark, submit signed fixture data through the existing temporary Unix socket broker, and verify a deny-only synthetic receipt containing the release digest. Current Trash++ SAVE SNAPSHOT/CONFIRM COPY, capacity bar, VERIFY CHAIN and Camera/Burn are unaffected.

## VERIFY

Tests cover independent pinned root and signature checks; correct release binding persisted with test receipt; durable reopen; contiguous sequence and predecessor enforcement; wrong root/owner/scope/type/expiry; sticky grant revocation; permanent retirement on rotation; loss of release enrollment; missing paired history/grant/record; invalid root/file symlinks; precommit revocation after initial preflight with rollback of both nonce and test copy; and legacy fixture receipts with empty release field. Existing Trash Python and JavaScript regressions and Meta Apollo Grammar workflows remain required.

## WATCH OUT FOR

- **The policy root and history file are CI test fixtures, not an independently controlled Weather/research authority.** The same user owning the directory can replace/roll back the SQLite database. Without off-host or protected monotonic anchoring, the test floor cannot stop a privileged/owner attacker. It is not an authenticated production revocation service.
- The synthetic release DB and synthetic copy DB are separate: a release can change between the last read-only high-water check and the copy COMMIT. No two-database/kernel/filesystem atomicity is claimed. Production admission needs a separately reviewed atomic or recoverable policy snapshot and trusted time.
- A release signature proves test-root approval of a grant digest, not that systemd launched a unit, that the peer script and all imported files are immutable, or that a source owner holds a genuine approved private key. The V2p pidfd and V2q unit/script checks are still not complete source attestation.
- No real Weather, research, MACHINE, Identity/Connections or other protected authority contract has been approved through this work. We neither install host services nor enable source access, copying from protected sources, Restore or Burn.
- **Stacked PR ordering remains V2p #1897 → V2q #1901 → V2r #1905 → V2s.** They are not independent merges. Retarget only after reconciling current main and reviewing the exact diff. Operator retains final merge/activation authority.
- V2s is about fixture authorization lifecycle, not real ArchiveStore quota/receipt and data protection. The existing Archive capacity control and unsigned V2i/V2j status remain unchanged.

## CHECKLIST

- [x] Rechecked Syntagma AGENTS/Hospital protocols, latest main and V2p/q/r ownership
- [x] Strict signed release envelope and independent test root
- [x] Durable per-owner release sequence/lineage and sticky grant retirements
- [x] Current release read-only check at initial admission and synthetic precommit
- [x] Bind release digest to atomic test copy/nonce + legacy compatibility
- [x] Add restart, forgery, revocation, rollback and broker integration tests
- [ ] GitHub CI green / any corrections
- [ ] Independent security and source-owner/MACHINE/Connections handoff
- [ ] Operator merge/deployment/production decisions

## NEXT // V2t Implementation

**Service-manager origin attestation and protected authority anchor.** Implement a source-owner-reviewed service identity contract with a dedicated Linux UID, externally pinned unit/cgroup/argv and full interpreter/script/package measurements, policy-origin verification with trusted time, and protected high-water release anchoring. Separately design real ArchiveStore nonce/snapshot/receipt/quotas integration. No live keys or source-owner service files without explicit approved cross-room handoff; Restore and Burn remain separate.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2s-grant-release-floor-20261111  
BASE // feat/trashpp-v2r-signed-service-grant-20261111, PR #1905  
STATE // GitHub-only synthetic implementation, not live Hospital registered  
ROLLBACK // Revert V2s release verifier/ledger, optional broker gate, tests and additive synthetic receipt hash field. Do not touch actual Archive SQLite, existing snapshots, Quickshell, source data or production trust histories.
