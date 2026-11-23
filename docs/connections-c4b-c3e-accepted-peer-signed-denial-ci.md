# 🏥💜 DOC 2 // C4b signed-denial with real AF_UNIX inherited-writer negative

**PATIENT:** The-Post-Apollo-Project  
**ROOM / STAFF:** Universal Connections · C4b Silverblue Gateway · DOC 2  
**SCOPE:** CI-only cross-owner regression, no new authority or protocol  
**PRODUCTION SIGN-IN:** HOLD

## IMPLEMENTATION

DOC 1's merged [#2355](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2355) shows that a real accepted pathname Linux AF_UNIX connection's SO_PEERCRED identifies the **connecting PID**, not necessarily the **later process that writes an inherited descriptor**. Its strict read-only C3e handler only replies with local diagnostics or refusals. DOC 2's merged [#2283](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2283) checks a 32-byte local test challenge using the exact existing 43-character base64url signed BEGIN/UNAVAILABLE verifier. DOC 1's [#2296](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2296) already shows that a local rollbackable challenge does not become protected state.

This **new C4b-owned regression** runs both *original* implementations in one GitHub-hosted disposable Linux test: the same C3e local challenge identifies an actual accepted AF_UNIX read-only OUTCOME query (including after one child inherits and writes the connector's socket) and appears in a correctly signed C4b BEGIN/UNAVAILABLE denial. The signed denial can be cryptographically valid even though kernel SO_PEERCRED reports a **different connecting PID** from the actual sending process. Neither the signature nor the accepted socket response authenticates that message sender or independently enrolls the real gateway.

The negative matrix includes the ordinary same-process connection, inherited-writer mismatch, local challenge consumed, protected custodian HOLD, wrong connecting PID dropped without ACK, wrong challenge, key replacement, frame tampering, duplicate UART proofs, forged peer/authentication fields, false protected terminal status, and the original production refusal.

**Files:** one additive C4b test file, dedicated GitHub workflow and this documentation. No existing DOC 1 or native C4b source is changed. The helper reuses original CI tests and disposable signers; no persistent listener, C5 grant, protected database, new remote protocol, installer or workstation operation.

## VERIFY

The dedicated workflow must show all 13 new checks PASS on exact head, then rerun all 24 original real C3e accepted-peer cases and all 18 C4b raw-challenge plus 28 original C4b controller tests. Native official Fedora Silverblue regression may run due to existing broad path triggers; it is independent of this combined source/real Linux socket test and must not be claimed until complete.

The test really forks Linux processes, connects a root-owned pathname socket, inherits the connected descriptor into a second process, observes the original read-only reply and verifies a signed C4b fixture denial for the exact same local challenge. It **does not** prove the signer corresponds to the installed native guest or that independently enrolled challenge/current history exists.

## WATCH OUT FOR / DECISIONS

Matching two locally generated pieces of evidence is not independent attestation. SO_PEERCRED is kernel-authentic for the connecting process and can remain stale as a message-writer attribution after an FD transfer. A signed UNAVAILABLE is not a transaction-committed receipt. A local consumed SQLite challenge can be restored and replayed. No positive release/host/seat/consent/history/terminal/retry/Sign-In flags are added.

DOC 1 owns protected root, issuer, challenge and current history. DOC 2 owns the installed Silverblue producer and its CI. DOC 5 and DOC 6 retain C5 and Identity command/settlement. The accepted local-first development → separately protected hardware later policy is unchanged. Any future protected source authenticated over a remote transport needs **a separately approved contract and independent custodian**. Nurse 2 exact-head review and operator merge and production decisions remain separate.
