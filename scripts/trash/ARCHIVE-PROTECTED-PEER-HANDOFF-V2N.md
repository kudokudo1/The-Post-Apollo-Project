# Trash++ // V2n Protected Peer Handoff Contract

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle
STAFF ROLE // DOC-compatible external development; live Hospital registration unverified
ASSIGNMENT // Source-to-broker process evidence handoff, without exercising another Room's signing authority
SCOPE // Own scripts/trash and tests/trash only, GitHub draft PR/test/doc. No owner service edits, local host mutation, merge, signer enrollment, production activation, Restore or Burn.

## IMPLEMENTATION

- Adds `archive_v2_peer_evidence.py` to obtain a connected Linux AF_UNIX SOCK_STREAM socket peer's PID/UID/GID from kernel SO_PEERCRED rather than caller-supplied JSON. It reads /proc/PID/stat process start ticks before and after hashing /proc/PID/exe executable bytes, checks current Linux boot UUID, and compares UID/GID/executable digest to a strict TEST_FIXTURE_ONLY expected-peer policy. The report binds those kernel measurements to a canonical SHA-256 witness.
- Adds `archive_v2_broker_handoff.py`, a test-only handoff that combines this kernel-peer witness with V2l authority-signed fixture enrollment, V2k owner-signed source claim, exact source ID/revision/timestamp/payload checksum, and a broker-generated request binding hash. This request hash binds the peer witness, claim digest, authority manifest digest, source identity and nonce.
- Extends V2m synthetic `test_copies` rows additively with a peer witness digest and request binding digest. These are stored in **the same SQLite transaction** as the nonce, synthetic payload and claim/authority hashes. Old V2m test copies remain readable with empty peer fields, explicitly not reclassified as peer-bound.
- The existing query-only lost-reply recovery returns the persisted hashes, checks their format and verifies the synthetic payload SHA-256, without returning bytes. The signed test fixture still refuses reusing a consumed nonce.
- There is **no** real socket listener/daemon, signing service, source owner implementation, private key, production trust root, Quickshell button, live ArchiveStore writer, Restore or Burn route. The test fixture cannot grant source access. All outcomes retain captureAllowed=false, sourceProcessVerified=false, sourceAuthorityVerified=false, trustedTimeVerified=false, productionAllowed=false.

## HOW TO USE

There is no new operator button or local installation for V2n. Existing Trash++ > ARCHIVE > SAVE SNAPSHOT / CONFIRM COPY / VERIFY CHAIN and the capacity gauge are unchanged. The CI tests create only an in-process Unix-domain socket pair, ephemeral Ed25519 keys, and a private temporary SQLite test store. The peer credentials come from the runner's Linux kernel. A matching fixture policy and signed owner proof yield an **isolated test copy**, not a live authorized Archive copy.

## VERIFY

Tests cover Linux SO_PEERCRED identity and process incarnation; wrong UID/GID/executable checksum and untrusted policy refusal; non-socket and self-declared credential refusal; correct signed claim and owner binding; test copy+nonce+peer witness atomicity; exception rollback before commit; lost-response recovery and replay refusal; malformed peer hash refusal; legacy V2m rows retaining empty peer evidence; no production signer or ArchiveStore code path. Existing full Trash, Camera, copy workflow, real capacity bar, provenance chain, Burn and Meta Apollo Grammar CI remain mandatory.

## WATCH OUT FOR

- **SO_PEERCRED proves the peer's kernel PID/UID/GID at connection time, not its authorization as the Weather or research source owner.** A same-UID process can create a connection; Python scripts share an interpreter executable digest. This module intentionally returns sourceProcessVerified=false. A protected production service identity must be distinct from the ordinary desktop account, and its source-owner service/unit, executable AND scripts/assets must be approved and verified.
- A SHA-256 request binding is local metadata, not a digital signature on process identity or consent. A process that controls the test ledger can forge it. It does not authenticate source authority or act as a production trust anchor.
- The demo/research and Weather Rooms have not authorized source-owned key provisioning, source code changes or a host service. MACHINE has its separate metadata broker/request-binding lane. Do not transplant that broker into Trash++ or turn synthetic policies into real permissions without cross-room review.
- Linux /proc checks can fail for inaccessible or exited peers and must refuse. No cross-platform fallback is provided. A process may still change script content or behavior after the evidence read; kernel evidence alone is insufficient for production trust.
- The V2n fixture database is separate from real ArchiveStore. It does not satisfy production crash-safe end-to-end capture, real Archive quota/provenance, or a secure brokered data-copy boundary.
- Independent security review and operator production/deployment approval are outstanding. This PR does not authorize access to any protected owner, keys, private files or data.

## CHECKLIST

- [x] Reconciled merged V2m and current GitHub ownership/Hospital entry protocol
- [x] Linux kernel peer credential and immutable process-incarnation evidence
- [x] Test-only signed source claim + peer digest binding
- [x] Same atomic test transaction persists nonce, payload and peer/request hashes
- [x] Read-only recovery and legacy V2m compatibility
- [x] Synthetic denial, crash and replay tests
- [ ] GitHub CI and corrections
- [ ] Independent security review and explicit source owner/MACHINE coordination
- [ ] Operator-authorized merge, host installation and future production contract

## NEXT // V2o Implementation

**Owner-controlled signer protocol and protected broker process contract.** Pending separate Weather/demo ownership approval: define a registered Unix socket service with dedicated OS UID, owner-held keys, pinned public-key trust authority, signed exact payload and source revision, genuine process/unit/script attestations, trusted time, bounded one-use challenge and an immutable snapshot commit with quota/recovery enforcement. Scope by owner; leave QML as an untrusted requester. Start with a demo-owned pilot, not protected identities. New Restore/retention/Burn permissions require separate assignments. Do not claim any of this is live in V2n.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-protected-peer-handoff-v2n-20261111
STATUS // GitHub code/test draft, no verified live Hospital registration or host change
ROLLBACK // Revert this V2n module, test and additive test-ledger columns. No migration of real Archive SQLite, user snapshots, V2i provenance receipts, Quickshell or V2l/V2m test authority floor. Preserve any synthetic fixture history needed for debugging.
