# Trash++ // V2o Single-Request Protected Broker Protocol (Fixture Only)

PATIENT // The-Post-Apollo-Project  
ROOM // Trash++ Universal Resource Lifecycle  
STAFF ROLE // External DOC-compatible development; not verified live Hospital registered  
ASSIGNMENT // On-wire source signer/broker contract, bounded peer-verified request, deny-only synthetic end-to-end handoff  
PERMISSIONS // GitHub-owned scripts/trash, tests/trash and draft PR/docs. No Weather/research/MACHINE owner writes, local host changes, service deployment, signing keys, Merge, Restore or Burn authority.

## IMPLEMENTATION

- Adds `scripts/trash/archive_v2_fixture_socket.py`, a **single-request** protocol handler operating on an already-connected Linux AF_UNIX SOCK_STREAM socket. There is **no bind/listen daemon, socket file path selection, key management, source reader, CLI entry point, Quickshell control or ArchiveStore import**.
- The on-wire contract is a four-byte network-order frame length followed by up to 256 KiB of **canonical ASCII JSON**. Exact allowed keys: fixed v2o schema, owner, resource, source revision/timestamp, canonical Base64 payload up to 128 KiB, V2l authority-signed enrollment manifest and V2k owner-signed source claim. Rejects extra/duplicate fields, noncanonical encodings, malformed Base64, invalid types, truncated frames, oversized declarations and timeout, without writing a snapshot.
- The server's owner expectation, public-key trust root and peer-process policy must come from separately supplied **test fixtures**, not the untrusted wire packet. V2n obtains kernel SO_PEERCRED, process start ticks, executable SHA-256 and boot identity, then binds that peer witness to the exact claim/manifest/payload SHA-256 and nonce. V2m persists nonce + synthetic copy + evidence digests in one SQLite transaction.
- Exactly one request is handled per accepted connection. On success the handler sends a framed, bounded, **deny-only** reply with the synthetic test receipt ID and evidence hashes. Errors are fixed machine-readable codes, not source bytes, private paths, credentials or raw tracebacks. A lost success reply is reconciled through V2m read-only nonce receipt recovery, never by resubmitting an authorized real capture.
- Tests create an ephemeral Unix listener in a private temporary directory and an actual separate Python client process. The client receives a pre-signed test request; **no private signing key is sent to the client or stored outside test memory**. Kernel credentials of that child process, not user JSON, are checked in the broker.
- Live ArchiveStore/source permissions and V2i unsigned provenance are unchanged. Every result retains `captureAllowed=false`, `archiveCopyAuthorized=false`, `sourceProcessVerified=false`, `productionAllowed=false`, `restoreAllowed=false`, `burnAllowed=false`.

## HOW TO USE

There is no new desktop button. CI exercises the protocol with generated ephemeral Ed25519 fixture keys, a temporary socket and a private test ledger. Current Trash++ > ARCHIVE > SAVE SNAPSHOT / CONFIRM COPY / VERIFY CHAIN and the capacity bar remain unchanged. This tests the *wire boundary only*, not an approved Weather/research source service.

## VERIFY

Python synthetic tests cover a real second-process Unix socket peer; bounded frame round trip; signed claim + pinned authority + peer binding committed in the test ledger; replay denial on a second connection; truncated/oversized frames; duplicate/unknown/noncanonical JSON fields; boolean timestamp confusion; malformed Base64; mismatched signed payload; wrong UID and unprovisioned peer policy; wrong authority root and signer; no service listener or real ArchiveStore integration. The full Trash Python and JavaScript Camera/snapshot/capacity/chain/Burn suites and Meta Apollo Grammar checks remain mandatory.

## WATCH OUT FOR

- **The temporary Unix socket is a CI fixture, not a protected service.** It runs under the same test user; a Python interpreter hash does not prove which Python script is connected. Linux SO_PEERCRED measures UID/GID/PID at connection time, but is not source-owner authorization, script identity, human consent or proof the source cannot change after checking.
- The externally provided test trust root is not enrolled in a protected system service, and no source owner holds an approved private key. The signed claim does not grant a live Archive copy. A fixed deny-only outcome is mandatory even with valid signatures.
- Frame size is intentionally 128 KiB payload maximum for tests and not designed for streaming real multi-megabyte snapshots. Real service would require review of full metadata/payload transport, connection lifetime, resource budgets, process-exit invalidation and a trusted clock.
- A single accepted connection is handled once; the caller must close it. The module intentionally has no production socket listener or public CLI. Invalid requests must not mutate actual ArchiveStore or other sources.
- MACHINE/TimeW's metadata broker, Weather's event source, Finance/demo research source and Connections/Identity key trust are separate owners. Do not provision their services/keys or infer approval from test success. Coordination and independent security review remain required.
- The V2m test ledger transaction is **not** the real ArchiveStore database transaction. Actual production quotas, V2i signed receipt extension, key custody, revocation floors and durable on-disk capture will need a separately reviewed broker plan before activation.

## CHECKLIST

- [x] Reconciled V2n merged `main`, Syntagma Hospital protocol and neighboring active PR ownership
- [x] One-request strict canonical Unix-socket wire protocol
- [x] Signature/peer source evidence bound to V2m atomic synthetic receipt
- [x] Bounded deny-only success/error response, no user data or signer keys
- [x] Cross-process peer and adversarial wire/authority/replay tests
- [ ] Full GitHub CI and corrections
- [ ] Independent security and owner-interface review
- [ ] Operator-approved merge/deployment and future production authority

## NEXT // V2p Implementation

**Protected service lifecycle and owner-authority handoff.** With explicit Weather/research + MACHINE coordination, define dedicated service UIDs and socket ownership, source-held signing keys, independently pinned signer enrollment, complete unit/script/executable provenance, process-exit revocation (pidfd where available), trusted-clock policy and real ArchiveStore nonce/receipt/quota transaction. Start with isolated demo owner only after approval. Preserve V2k/V2l deny-only gates until real key custody and service identity are independently verified. Restore, retention and Burn remain separate assignments.

## DECISIONS / RECOVERY

BRANCH // feat/trashpp-v2o-fixture-socket-contract-20261111  
STATE // GitHub-only draft fixture, no live Hospital registration  
ROLLBACK // Revert V2o one-file protocol, tests, docs. No real Archive SQLite schema/data, Quickshell runtime, systemd unit, production credential or source-owner file has been changed. V2n peer binding and V2m crash harness remain as previous.
