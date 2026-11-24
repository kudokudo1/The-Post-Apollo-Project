# DOC 3 // Forest C5 signed public egress race experiment

**Patient:** The-Post-Apollo-Project  
**Room:** Forest C5 issuer and outbound permission ordering  
**Staff:** Connections DOC 3, reporting through Forest Nurse 2  
**State:** disposable native Linux CI experiment only. Production HOLD.

## IMPLEMENTATION

This experiment follows #2385 (separate, always-refusing LIST and title operations), DOC 1's proposed custodian RFC #2388, and Forest Core B5b #2390 (real child process, single fixed public HOLD submission). It does NOT alter their source or select a production wire.

The new test-only gate creates its own unnamed AF_UNIX SOCK_SEQPACKET pair. An ephemeral Ed25519 test key signs two distinct operation-specific records: LIST_SESSIONS and DISCLOSE_SESSION_TITLES. Both signatures bind the same synthetic owner, Tree, random request and recipient identifiers, fixture epoch, local monotonic deadline and byte budget. The gate reconstructs the exact test bytes and verifies both signatures; it does not accept a caller-chosen payload, socket, signer key in a message, private owner, database, or actual consent record.

One local lock serializes signature checking, one-use consumption, budget and expiry checks, actual nonblocking kernel submission of a **constant public test marker**, and revocation. The state is marked SPENT_UNKNOWN *before* the only send attempt. A failed or uncertain send cannot be retried, and revocation does not convert it to a settled outcome. Successful local revocation closes the test sender, forbids further submits and may report LOCAL_TEST_FENCED_NO_NEW_SUBMITS. This is not an authenticated revocation ACK. Every production authority flag remains false, privateBytesSubmitted=0, revocationFencedAck=false and safeActions=[].

Real concurrency tests race two threads for send/revoke and replay. The legal local outcomes are revoke first (no packet), or send first (one public packet). The latter demonstrates that bytes already queued in the kernel can still be read after revocation, even when the receiver had not yet read the packet. Separate signatures do not imply separate human approval or independently administered signers.

## HOW TO USE

CI/disposable Linux only:

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_signed_public_egress_race.py' -v

Do not import the test class into Forest Core, ForestW or the existing C5 authority service. No workstation setup, protected root, private storage, model or production endpoint is involved.

## VERIFY

15 tests exercise actual local signature verification, scope/recipient substitution, wrong action/key, two distinct permissions, expired lease, budget, double spend, disconnect uncertainty, send/revoke ordering, concurrent replay, and the unchanged actual C5 boundary's refusal even after the public test succeeds.

CI also runs the merged C5 authority, handoff and B5b tests. Raw exact-head results and independent Forest Nurse 2 review required.

## WATCH OUT FOR

- The gate and signer are in the same disposable interpreter and administrative domain. Random recipient ID is a test binding, not process/seat or FD attestation.
- The local lock is not a distributed revoke barrier. Neither key nor state is durable; this does not solve independent currentness, rollback resistance, process death, remote issuer synchronization or crash recovery. No claim of terminal settlement.
- This single public-marker syscall does not prove serialized private UTF-8 streams, actual B5b host integration or safe disclosure of session titles. Forest Core owns the actual host/egress implementation. B5b runs independently as a regression, not through this gate.
- The local monotonic clock and synthetic budget are not protected issuer time or authorization. Do not promote signed fixture results into a real grant.

## NEXT / DECISIONS

DOC 1/2 must obtain an operator-approved independent Forest-purpose custodian/root, installed source and recipient witness. Forest Core must identify and approve the installed host and protected DB/serializer seam. DOC 3 can then implement reviewed C5 permit consumption and revocation against that actual authority. Preserve distinct list/title/stream/commit scope and unknown-outcome recovery. No native wire accepted or production capability granted by this test.
