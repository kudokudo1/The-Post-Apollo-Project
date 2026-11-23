# 🏥💜 DOC 3 // Forest C5 Native Disclosure Handoff Proposal

PATIENT: The-Post-Apollo-Project
ROOM: Forest C5 · Connections-owned issuer/recipient/revocation interface
ROLE: DOC 3, reports through Forest Nurse 2
CONNECTION: EXTERNAL / Hospital-compatible; live registration unverified
STATE: Proposed, uninstalled, deny-only
PRODUCTION: HOLD

## IMPLEMENTATION

Forest B3 yields assistant text to its caller before the final database commit permission check. Those bytes can become irreversible once transmitted to an external recipient. B4f/B4g local SQLite records are restorable and cannot establish protected C5 consent, enrolled writer identity, or present revocation.

Previously merged DOC 3 #2314 describes a separate DISCLOSE_PROVISIONAL candidate with exact original COMMIT intent/session/attempt binding and intended recipient fields. It does not grant permission.

This milestone adds ForestC5NativeDisclosureHandoffPreflight.py with three strictly scoped, **caller-supplied test fixture** records: (1) claimed protected issuer one-use permit, exact candidate/COMMIT digest, recipient and budget; (2) claimed original recipient instance/release/seat, process PID/start/UID, host boot and peer digest; (3) claimed revocation issuer generation, stream budget/sequence/in-flight send state.

The three wires are untrusted. Matching even a fabricated REVOKED-and-drained claim always yields UNKNOWN_HOLD, emitEvent=None, emittedBytes=0, safeActions=[], and all protected authority flags false. Mismatched recipient, reused commit grant, stale generation, wrong budget, false revocation ACK while sends are in flight, malformed JSON, forged positive flags and private text injection are refused. No origin identity, private token output or consent is returned.

The fixture-v0 schema is NOT the accepted native wire protocol. There is NO signer, protected issuer, operating-system identity reader, durable counter, live Forest writer, daemon, network client, process controller, model execution or GUI. Other workers' code is untouched.

## HOW TO USE

Disposable tests only:

    python3 -B -I -m unittest discover -s tests/connections -p 'test_connections_forest_c5_native_disclosure_handoff.py' -v

The output is an untrusted diagnostic HOLD even when fixture records agree. No installed Forest or personal data is touched.

## PROPOSED TRUSTED NATIVE CALL SEQUENCE (NOT IMPLEMENTED)

1. C5 issuer independently validates separately approved human DISCLOSE_PROVISIONAL consent, original signed COMMIT session/Tree/userTurn/attempt/model/revision, enrolled process/seat, recipient identity and revocation epoch. It durably allocates a one-use disclosure permit distinct from COMMIT_GENERATE. Never copy a client permit ID or trust a fixture signature as issuer authority.
2. DOC 1/DOC 2 provide independently observed original process PID/start/UID, release, boot, live seat and recipient channel identity, enrolled to an issuer root. Inherited AF_UNIX socketpair SO_PEERCRED alone is insufficient.
3. The existing trusted Forest host holds a serialized outbound send gate. Before the first externally visible byte it checks issuer permission and recipient. For each chunk it checks live revocation generation, valid lease, UTF-8 cumulative budget and cancellation; records in-flight sequence **before** submitting bytes; and accounts for sends before release. No per-token remote HTTP query or new always-on service is assumed. A local lease requires native issuer invalidation and recovery; a stale process cache is insufficient.
4. Revocation first durably increments the issuer generation and blocks new sends, then fences the host's outbound queue and waits for pending sends to drain or be permanently closed. Only then may it ACK **no new sends**. A lost ACK, crashed host, uncertain kernel buffer or offline recipient is UNKNOWN_HOLD. Previously delivered bytes and recipient-buffered text cannot be recalled, so do not claim universal erasure.
5. A separate COMMIT_GENERATE permit and independently authenticated original writer terminal receipt control durable SQLite reply commit. Disclosure never authorizes persistence; a local COMMITTED outbox event never authorizes disclosure or revocation release. The proposed V2 native terminal receipt in Forest issue #2161 still awaits owner acceptance.
6. Integrate with existing Forest P1/P2 resource governance and current host to keep latency low. Forest Core owns streaming and model runtime; ForestW owns the display/UX. DOC 3 owns C5 security checks; DOC 1/DOC 2 own native original process and trust custody.

## VERIFY

33 new adversarial tests cover strict parser domains, original exact scope, separate issuer/recipient/permit, forged permission, process/boot evidence, lease/budget, replay, revocation generation and in-flight output. Inherited C5/Forest tests run in CI. All tests are synthetic and cannot authenticate a native process, human consent or protected issuer.

## WATCH OUT FOR

Owner/operator decisions remain outstanding: actual provisional streaming consent, revocation ACK's scope, treatment of already displayed text, recipient destination, separate terminal receipt, and native protected history. An in-process fixture that reports zero pending bytes is not a kernel or remote-recipient witness. A valid nonce or signed-looking packet is not independent authority.

## CHECKLIST

- [x] P2B/P2C reviewed milestone state reconciled.
- [x] Connections-owned negative fixture and tests prepared.
- [ ] Exact-head CI/raw logs verified.
- [ ] Forest Nurse 2 independent pre-merge security review.
- [ ] Forest Core/ForestW/operator disclosure policy acceptance.
- [ ] DOC1/DOC2 installed writer/recipient origin and protected issuer transport.
- [ ] DOC3 live one-use permit, revocation ordering and terminal evidence verification.
- [ ] Explicit final production acceptance.

## NEXT

Review as a proposed test contract, not a production implementation. Seek Forest Nurse 2 scoped PASS/REVISE/HOLD; route native origin and issuer questions through Forest Nurse 2 to Connections Nurse 2. Implement in an isolated owner-approved native milestone only after actual interface semantics and custody are accepted.

## DECISIONS

No C5 V1 reinterpretation, no production permission, no local machine mutation, no cross-owner source changes, no merge. Production HOLD.
