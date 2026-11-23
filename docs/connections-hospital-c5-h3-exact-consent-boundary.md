# 🏥💜 DOC 4 // Hospital C5-H3 exact consent challenge boundary

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5 native operator consent  
**STAFF ROLE:** DOC 4 · external Hospital-compatible  
**PX OWNER:** The-Post-Apollo-Dev-Exp protected writer #130 / #133, unmerged at start  
**C3e OWNER:** DOC 1, storage-independent trust #2229 is merged but protected custody absent  
**STATE:** source/CI development only · PRODUCTION HOLD

## IMPLEMENTATION

The real native issuer already obtains protected PX PREPARE containing a
fresh request nonce and source Room, Patient, repository, revision, digest,
eligibility, retention and writer instance. It independently checks the
requester executable, host and login1 seat, then calls Polkit.

**Problem:** DOC 4 #2194 passed exact Room context into Polkit, but omitted
the PREPARE nonce from structured details. Two separate operations against
the same unchanged Room can otherwise yield indistinguishable displayed
context. A future trusted operator-consent witness must bind the
specific operation, not only the Room state.

This milestone adds `hospital-request-nonce` to the existing trusted
issuer's `pkcheck --detail` request, sourced exclusively from its previously
validated protected PX PREPARE. It never asks QML for a nonce. It preserves
the distinct native TRASH/RESTORE action IDs, the existing revalidation
after Polkit and the one-use PX commit protocol.

A **separate test-only** C5-H3 reference constructs canonical review bytes
covering: purpose, action, Room, Patient, repository, revision, graph
SHA-256, PX request nonce, real-issuer-asserted operator UID, login1
seat, bound host, retention policy generation, issue time, expiry and permanent
preservation/no-Burn restriction.

It computes a domain-separated SHA-256 review digest for interoperability
testing and compares deliberately untrusted candidate "shown" and
"confirmed" claims against the review. It rejects altered, malformed,
stale or crossed claims, but **all** results set:

- `externalConsentProducerAuthenticated: false`
- `humanConsentVerified: false`
- `independentHistoryVerified: false`
- `signingAllowed: false`
- `nativeRoomMutationAllowed: false`
- `productionAuthorized: false`
- `safeActions: []`

Even a matching claimed agent release digest is NOT actual release
enrollment or proof of human action. The candidate claim is not an
approved protocol. The reference is not imported into native production
code, and `production_admission` always refuses.

## HOW TO USE

There is **no new workstation/UI action**. Ordinary GitHub CI runs the
new exact-review matrix and prior DOC 4 Polkit-detail checks. No real
session, Polkit agent, protected writer, signed key or Hospital records
are used by this test. Native Room mutation remains disabled.

## VERIFY

- Existing DOC 4 test now checks that structured Polkit details include
  the PX-generated nonce and change when a new prepared request is used.
- New 23-test hostile suite exercises source eligibility, changed Room/
  revision/graph/nonce/host/seat/UID, policy epoch, issuance time, expiry, withheld
  confirmation, fake release, noncanonical/duplicate JSON, altered digest,
  and absolute no-authority flags.
- The inherited C5-H2 source and signature suites must still pass. This
  source change does not claim a native installed acceptance test.

## WATCH OUT FOR

A source digest proves only that certain bytes match. A callback saying
`claimedVisible: true`, even if signed by a disposable key, does not
prove the operator saw or approved those details. Polkit may be bypassed
by installed rules or show a generic prompt. There is no approved trusted
agent/renderer, no independently enrolled signing key or executable
release, no trustworthy display receipt and no security guarantee that
Sway/Wayland actually displayed the requested text.

An accepted *future* design needs operator-approved independent
producer identity, native seat/lock/display checks, exact digest
rendering, genuine explicit operator gesture, fresh nonce and deadline,
one-use consumption, protected challenge/outcome history (not restored
with the Hospital SQLite database), and trusted issuer integration.
A replayed local snapshot must not reauthorize an operation.

Real production admission must not become possible by loading this
CI fixture, an env var, a caller-selected public key or a Python import.

## CHECKLIST

- [x] Source-only PX nonce forwarded into Polkit detail context
- [x] CI-only exact review byte/digest reference with negative claims
- [ ] Exact-head GitHub CI and independent Nurse 2 security review
- [ ] DOC 1/Identity approved host + independent custodian enrollment
- [ ] PX owner approved native PREPARE/COMMIT, durable receipt and all-writer cutoff
- [ ] Real trusted operator display/gesture evidence and installed agent testing
- [ ] Operator production acceptance

## NEXT

Obtain independent pre-merge review of this bounded code. Coordinate
the **real producer contract** with DOC 1 identity, PX protected writer
and Hospital UI owner before implementing any authorizing runtime agent.

## DECISIONS

No new signer, root key, Polkit policy installation, QML authorization,
PX branch edit, live database, local workstation write, merge or Burn.
This development reference has no production authority.
