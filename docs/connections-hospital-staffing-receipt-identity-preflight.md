# 🏥💜 Connections ↔ Hospital // Staffing receipt identity and protocol versions

PATIENT // The-Post-Apollo-Project (Connections issuer)  
COORDINATION PATIENT // The-Post-Apollo-Dev-Exp (Hospital protected writer)  
ROOM // Connections · Hospital Staffing Issuer  
ROLE // Connections DOC, operator-directed source-only issuer-side milestone; live Hospital registration unverified  
BASE // Staffing transport #2078 exact reviewed head 0f9c34e5cc8f32f674a4f5bd39611282c007f45b, stacked on interface #2077  
HOSPITAL SOURCE // Protected Hospital draft #133 exact head ee1dc74056fbd2c849d3391e3148b003514b2932  
PRODUCTION // HOLD, no native signer, writer installation, trusted receipt, credentials, database change or merge.

## IMPLEMENTATION

Four additive Connections staffing-owned files: the read-only StaffingReceiptIdentityPreflight.py, 32 adverse CI tests, a GitHub CI workflow and this recovery contract. Existing C5-H2 Room Trash/Restore, Hospital #133, parent #2078 transport, C3e and PX files are untouched.

### Actual current Hospital #133 protocols

| Phase | Exact schema | Trust |
| --- | --- | --- |
| PREPARE / COMMIT request | postapollo.hospital.native-staffing-request.v1 | Untrusted canonical bytes |
| PREPARED | postapollo.hospital.native-staffing-prepared.v1 | CI-only source snapshot |
| Current Hospital receipt | postapollo.hospital.native-staffing-fixture-receipt.v1 | CI fixture, NOT native |
| Connections candidate receipt | postapollo.connections.hospital.staffing-receipt-proposal.ci-v1 | New, NOT APPROVED by Hospital |

The current Hospital fixture has exactly these fields: schema, requestNonce, roomId, action, sessionId, grantDigest, fixtureTransactionCommitted, nativeInstallationVerified, operatorAuthenticated. Its flags are respectively true, false, false. It **does not contain writerInstance, original PREPARE digest, exact COMMIT digest, protected writer identity, release attestation, or a production signed receipt**.

The first helper compares the fixture to the original PREPARE, matching PREPARED Room/action/nonce/writer instance and exact canonical COMMIT candidate. It recomputes grantDigest as SHA256 over the Hospital staffing-grant domain followed by canonical signed-grant BODY. This is only comparison of supplied bytes, not Ed25519 authenticity.

### Proposed versioned receipt: planning aid only

The second helper accepts a separate, exact canonical candidate schema called postapollo.connections.hospital.staffing-receipt-proposal.ci-v1 with protocolVersion=1, kind=source-only-commit-receipt, and status=UNVERIFIED_PROPOSAL_ONLY.

Its exactly 15 fields are: schema, protocolVersion, kind, requestSchema, requestNonce, roomId, action, sessionId, writerInstance, expectedRevision, graphDigest, grantDigest, originalPrepareSha256, commitSha256, status. A proposed `revisionAfter = expectedRevision + 1` was **removed**: Hospital #133's Session Attach and Doctor Succession source does not guarantee that increment. The writer owner must establish any authoritative post-commit revision separately.

The parser compares them to the supplied original PREPARE, independently supplied PREPARED snapshot and canonical eight-field COMMIT. It rejects changed Session/Doctor identity, action, Room, request nonce, writer instance, source revision, graph or grant digest, altered PREPARE/COMMIT SHA-256, missing or added fields, duplicate JSON fields, unsupported version, boolean-as-version and incorrect status.

The packet wrapper reuses #2078 actual SO_PEERCRED/SCM_CREDENTIALS Linux sender observations on a disposable Unix SOCK_SEQPACKET connection. A caller-supplied expected UID remains *only a CI input*, not root-controlled writer enrollment. A kernel sender observation alone does not prove authenticated installed release, active seat, signed source or the truth of the reply.

Even when all candidate fields match, the helper returns only a format diagnostic. It forcibly returns false for independent writer authority, cryptographic verification, transaction commit, durable replay history, human consent, and all production/credential/Session/Doctor grants. Rechecking the same supplied bytes twice does **not** persist a replay tombstone or claim unique consumption.

### Hospital owner decisions needed for a real native receipt

1. **Writer-produced schema/version:** Which fields Hospital will actually send, including originalPrepareSha256, commitSha256, writerInstance, Room graph, verified post-commit revision (if available), sessionId, grantDigest and any policy generation. The new candidate is NOT an accepted production wire protocol.
2. **Authenticated origin:** Whether the reply is signed by a separately enrolled Hospital writer key, or identified through approved root-controlled installed executable/unit provenance plus kernel packet credentials and fixed Unix socket identity. A claimed writerInstance is not writer authentication.
3. **Result states:** Distinct authenticated COMMITTED, REFUSED, UNKNOWN/INTERRUPTED and ALREADY_APPLIED semantics. An unanswered COMMIT must never be silently treated as committed, nor automatically replayed with the same consent.
4. **Version/transport bounds:** Exact response maximum, canonical bytes, READY/SCM_CREDENTIALS handshake, MSG_TRUNC denial, known-version-only dispatch and separate full 16384-byte COMMIT vs decoded 8192-byte envelope limits. Never fall back to the Room issuer's separate 8192-byte permission system.
5. **Transaction custody:** Hospital's root policy, single BEGIN IMMEDIATE source mutation and nonce consumption, durable receipt record/recovery, v13 migration/old-writer fencing and independent replay/rollback proof. Connections does not acquire a database write path.

Until the Hospital protected writer owner and Connections issuer owner approve this interface, this is exclusively source-only design and test work.

## HOW TO USE

The isolated GitHub Actions workflow checks out Hospital #133 at its exact commit into a disposable test directory. It imports the **real** Hospital transport, grant, protected coordinator and Linux peer source to check exact schemas, version and request/receipt fixtures. No installed service, private key or local workstation action is involved.

The 32 test cases cover matching fixture, false native flag enforcement, changed nonce/Room/Session/operation/grant digest, proposed receipt version/schema mismatch, wrong writerInstance, request/COMMIT hashes, revisions, graph, replay across changed PREPARE, malformed and duplicate JSON, forged authority/status, wrong kernel sender UID and real Unix socket packet observations. An inherited run retains the #2078 transport and packet security tests.

## VERIFY

- [ ] Exact-head new 32-test fixture/version/identity workflow PASS
- [ ] Exact-head inherited #2078 real Linux peer/transport workflow PASS
- [ ] Grammar and any other relevant workflows PASS
- [ ] Independent Nurse 2 review of exact head
- [ ] Hospital protected writer owner review of proposed 15-field receipt and native error/recovery semantics
- [ ] Separate issuer/operator acceptance and merge, no automatic merge

## WATCH OUT FOR

A syntactically matching future receipt is not independently trusted evidence. Any malicious caller controlling all expected inputs can construct the candidate. This module cannot verify Ed25519 keys, installed Python/unit source, true root writer peer, active seat, actual human consent or Hospital database commitment. Never feed its diagnostic into an installed issuer or UI permission.

Hospital's current coordinator fixture may claim a successful disposable transaction but never grants production authentication. Protected writing, actual grant verification, one-use consumption, schema v13, recovery, old-writer fencing and room data remain exclusively Hospital-owned. The C5-H2 Room Trash/Restore permission and Hospital Burn remain separate/off.

## CHECKLIST

- [x] #2078 reviewed commit has 3/3 CI and NRS-2 scoped PASS
- [x] Mark #2078 ready for review; no merge and no claim of issuer/Hospital owner acceptance
- [x] Create isolated, stacked issuer-side Phase 2 preflight
- [x] Implement current fixture and unapproved proposed schema checks with authority hard-disabled
- [ ] CI and independent review
- [ ] Owner agreement on actual native receipt and error/recovery state machine
- [ ] Only then separately authorize real native receipt verifier, writer process provenance and sign-in

## NEXT

Request Hospital owner feedback on this proposed 15-field CI schema and its recovery/identity questions before creating a native writer-response implementation. Reconcile any field or version changes on both sides first, then design the independent writer-identity/root provenance adapter under an explicitly approved assignment.

## DECISIONS

DRAFT / STACKED / SOURCE-ONLY. Previous C3e/Identity worker remains paused. No Hospital #133, C5-H2, PX, Room Trash/Restore or existing staffing owner file changed. No merge, machine installation, live signing key, database change or production authorization.
