# Trash++ // V2t Kernel Cgroup Origin & Signed Release Checkpoint (Fixture Only)

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
PROVIDER // OPEN AI // CHATGPT
STAFF ROLE // External DOC-compatible development; no live Hospital registration verified
ASSIGNMENT // Test-only read-only Linux cgroup origin evidence and independently signed release checkpoint through synthetic capture commit
PERMISSIONS // GitHub-only branch, draft PR, scripts/trash and tests/trash. No live host files, source-owner services, new keys, independent trust-store claims, merge, real ArchiveStore writes, Restore or Burn.

## IMPLEMENTATION

- Added `archive_v2_origin_checkpoint.py`, with two separate fail-closed mechanisms:
  - **Linux cgroup v2 peer witness:** reads a connected AF_UNIX peer's PID/UID/GID from kernel SO_PEERCRED and verifies it matches the already observed V2n witness, Linux start ticks and boot identity. Reads actual `/proc/<pid>/cgroup` and requires a single cgroup-v2 entry. A separately supplied `TEST_FIXTURE_ONLY` policy pins the expected cgroup path, owner and UID/GID; mismatch, v1 or hybrid layout, malformed/unknown path, missing process or changed incarnation refuse. A canonical SHA-256 witness is returned, never the private cgroup path. This is *observation*, not systemd provenance.
  - **Distinct signed checkpoint root:** verifies a separate authority-signed TEST release checkpoint against an independent pinned Ed25519 checkpoint test root, with a distinct public key from V2s's fixture release root. Fixed schema binds allowlisted owner, exact current V2s release sequence/digest, V2r service-grant digest, copy-only purpose/audience, and bounded validity. Missing/bad signature, self-declared root, stale/expired checkpoint, wrong owner/release/key or incomplete component pair refuse.
- Existing V2o synthetic one-request broker optionally checks both, **first during preflight and again in V2p's pidfd/V2q file/V2r grant/V2s release precommit guard**. A mismatch or changed release immediately before the V2m test SQLite COMMIT rolls back both synthetic snapshot and its one-time nonce.
- Added `origin_witness_sha256` and `checkpoint_sha256` fields only to the V2m **synthetic test** copy table. Both hashes contribute to V2n's canonical test request binding and appear in query-only, payload-free recovery. Legacy test receipts keep empty V2t witness fields; no invented history.
- All fixture replies still say `systemdUnitVerified=false`, `sourceProcessVerified=false`, `archiveCopyAuthorized=false`, `captureAllowed=false`, `productionAllowed=false`, `restoreAllowed=false` and `burnAllowed=false`. No source-owner process, Linux service unit, socket daemon, signer/private key, real SQLite ArchiveStore or Quickshell UI changes.
- **GitHub ancestry finding:** V2p #1897 merged into main, but V2q #1901, V2r #1905 and V2s #1910 merged into *feature base branches* rather than main. V2t is branched from #1910's merge commit on `feat/trashpp-v2r-signed-service-grant-20261111`, which contains the V2s code. Do not mistake merged PR state for presence on main.

## HOW TO USE

No desktop action. CI uses an actual Linux test socket, kernel /proc evidence, ephemeral in-memory Ed25519 fixture source/root/checkpoint signing keys, private synthetic unit/script/socket files and 0700 test SQLite. No sensitive user paths or live source code is opened. Current Trash++ ARCHIVE SAVE SNAPSHOT / CONFIRM COPY, capacity gauge and VERIFY CHAIN remain unchanged.

## VERIFY

Adversarial tests cover: two distinct pinned signing roots; valid signed checkpoint and kernel cgroup witness stored in one synthetic nonce+copy transaction; forged root/signature, wrong owner/grant, changed current V2s release, unsupported v1/hybrid/malformed cgroup, wrong UID and cgroup policy, missing checkpoint/root or release history, file/process denial, cgroup change at final guard, release change after initial preflight and before final guard, strict schema/time checks and legacy empty evidence. Full Trash Python, JS Camera/snapshot/capacity/chain/Burn and Meta Apollo Grammar CI must pass.

## WATCH OUT FOR

- **Kernel cgroup membership does NOT authenticate a systemd unit.** A process may share a cgroup with other services or run as an unprivileged user. In CI, matching an exact test cgroup is evidence that the process belonged to that cgroup at observation time, not proof that a protected owner service launched or approved it. `systemdUnitVerified=false` is intentional. A genuine service-manager D-Bus/cgroup/UnitID and signed package measurement requires source-owner/security review.
- The second checkpoint's key is **independent only inside CI**. Neither test root is an actual protected, externally provisioned authority. Signed stale checkpoints can be replayed together with a rolled-back test ledger if a same-UID actor controls both. There is no protected monotonic external anchor or authenticated clock.
- V2s release history, V2m synthetic nonce+copy and kernel/filesystem observations do not share an atomic cross-system transaction. A release can change after the final check and before commit; successful synthetic verification does not mean live permission.
- Real ArchiveStore, actual snapshots, V2a quota limits, V2i unsigned receipt chain and display capacity are unchanged. No current source-owner credentials, Weather/research service data, MACHINE/Connections or protected files were modified.
- V2t depends on features not yet present on `main` despite their GitHub PRs being merged: #1901, #1905, #1910. Keep the integration path explicit and require authorized review/merge of the actual diff. This is no production activation or host install.

## CHECKLIST

- [x] Re-read Syntagma AGENTS/Hospital, rechecked latest main and exact PR base/head ancestry
- [x] V2t Linux cgroup v2 measurement with pinned fixture identity and fail-closed unsupported layouts
- [x] Separately pinned test checkpoint root and release current-head digest/sequence matching
- [x] Preflight/precommit checks and synthetic digest binding, without backfilling old records
- [x] Adversarial signature/cgroup/rollback/legacy security tests
- [ ] Full GitHub CI and corrections
- [ ] Review and authorized integration of V2q/r/s commits into main
- [ ] Real service-manager/source-owner/Connections trust contract, independent security and operator acceptance

## NEXT // V2u Implementation

**Reviewable upstream integration and protected service-manager attestation interface.** Reconcile the actual feature-branch commits into main via a separate draft PR, then, contingent on approved Weather/research and MACHINE/Connections ownership handoff, define a dedicated service UID, verified unit/cgroup identity through systemd's manager, exact executable+script+dependency integrity, externally anchored grant/release floor, protected time and real ArchiveStore quota/nonce/receipt commit. Continue deny-only until independently authorized. Restore and Burn remain separate.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2t-kernel-origin-checkpoint-20261111
BASE // V2s merge commit 28a6d45f39d3edf8f63e96deaa4d1790433c7c24 (currently on V2r feature branch)
STATUS // GitHub draft work; not live Hospital registered, not production-authorized
ROLLBACK // Revert V2t cgroup/checkpoint module, optional broker call, synthetic SQLite witness columns, tests and doc. Never delete actual snapshots or revoke real owner keys; no local system files were changed.
