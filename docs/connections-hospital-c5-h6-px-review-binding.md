# 🏥💜 DOC 4 // C5-H6 protected PX writer-instance and review-context binding

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5  
**STAFF ROLE:** DOC 4 · external Hospital-compatible; live Hospital registration unverified  
**SOURCE:** dedicated DOC4 branch from application main, with PX #130/#133 under separate ownership  
**PRODUCTION:** HOLD

## IMPLEMENTATION

The reviewed native Hospital issuer generates a fresh 32-byte request nonce
using `os.urandom`, sends it in a `PREPARE` to the protected PX writer,
and validates PX's echo of that nonce. **The nonce is issuer-generated and
PX-echoed, not PX-generated.** PX additionally returns `writerInstance`,
`policyGeneration`, and `expiresAt`. These are validated independently
by `HospitalNativeIssuerCore.validate_prepared`.

Earlier C5-H3 forwarded Room, Patient, graph, revision, nonce, seat and
preservation fields to Polkit, but did not expose PX writer instance,
policy generation or expiry in the structured review details. The CI-only
review digest also omitted `writerInstance`. That could make two reviews
of otherwise identical Room state appear indistinguishable across a PX
writer instance change, even though the later protected `COMMIT` already
binds `writerInstance`.

C5-H6 adds three issuer-originated structured `pkcheck --detail` fields:

- `hospital-writer-instance` ← PX-protected `prepared["writerInstance"]`
- `hospital-policy-generation` ← PX-protected policy generation
- `hospital-review-expires-at` ← PX-protected expiry (integer UNIX seconds)

The source-only exact-review reference now uses **v2** test-only schema
`postapollo.hospital.c5h6.exact-room-review.v2` and a new domain
separator. It binds `writerInstance` within canonical review bytes and
requires it in the untrusted candidate claim. The v1 claim schema is
rejected rather than silently normalized into v2.

No versioned v2 review is a production wire protocol. No installed native
agent imports this CI reference. **No signed positive human-consent
response exists** in this milestone.

The C5-H4 native `_require_independent_room_consent()` remains
unconditionally deny-only **after** Polkit and before private-key load,
grant signing and PX COMMIT. No UI control, environment variable, local
fixture, self-signed agent or Polkit zero exit may bypass it.

## HOW TO USE

GitHub-only: the C5-H6 workflow checks the 8 focused Polkit details cases,
the expanded no-authority v2 review digest/claim matrix, and source-only
ordering. Inherited C5-H2/H4 and shared Connections workflows remain
separate regression gates. No workstation installation or Hospital action.

## VERIFY

- Changing the PX writer instance while holding the Room and nonce fixed
  changes the canonical review digest and Polkit review detail.
- Changing the PX policy generation or expiry changes review details.
- Changed source deadline, removed writer instance, cross-writer forged
  claim, old v1 claim, unknown authority fields or forged approval cannot
  grant authority.
- Two formerly duplicated test-method names are made distinct so the
  pre-issuance display check and duplicate-JSON check both execute.
- The normal issuer still receives its nonce from native `os.urandom`,
  and the protected writer must echo it and bind its own instance in
  `COMMIT`; this PR does not change source writer/schema validation.

## WATCH OUT FOR

**Polkit structured details are not a trusted visual receipt.** The
installed agent may ignore optional detail keys, show only a generic
authentication prompt, or be bypassed by effective local policy. A
matching SHA-256 review digest proves matching source bytes, not actual
display, attention, comprehension or operator gesture. Adding more
review context does not create human consent or antirollback protection.

Separate operator/owner decisions before native authorizing integration:

1. **DOC 4 + SwayPX/Hospital UI owner:** choose a trusted, independently
   enrolled display and input surface able to attest exact canonical
   review bytes on the *active, unlocked* seat. A normal untrusted QML
   callback or screenshot is not an adequate proof.
2. **DOC 1 / identity custodian:** approve enrollment root, producer
   release/signing role, host and executable evidence, revocation/fresh
   challenge and independent current trusted history. Never substitute
   caller-supplied test key or a local rollback-prone SQLite ledger.
3. **PX protected writer owner:** establish one-use original request
   custody across complete DB rollback, `writerInstance` binding,
   durable PREPARE→COMMIT/outcome semantics and all-legacy-writer fencing.
4. **Operator:** select the trust/custody architecture, installation
   plan and final production acceptance. No prior source merge does that.

A future signed producer claim must bind the exact domain, Room, action,
Patient, repository, graph, revision, issuer nonce, PX writer instance,
policy generation, expiry, operator/seat/host and approved renderer
release; its trust root must be independent of the requester and
the source Hospital SQLite rollback domain. Even then, only independent
one-use custody and protected writer transaction admission can decide
whether a Room mutation may execute.

## CHECKLIST

- [x] Protected PX writer-instance, generation and expiry details proposed
- [x] Versioned CI-only review v2 and cross-writer hostile tests proposed
- [ ] Exact-head CI and independent Nurse 2 source audit
- [ ] DOC 1, PX owner and trusted-renderer owner accept actual evidence protocol
- [ ] Independently installed producer/release/key/revocation trust
- [ ] All-writer cutover, protected rollback and native end-to-end acceptance
- [ ] Operator production acceptance

## NEXT

Review C5-H6 exact-head CI. Ask Nurse 2 for independent **pre-merge**
review and DOC 1 / PX owners for ACCEPT / REVISE / HOLD on the
future trusted producer, release and one-use custody questions.
Do not infer their consent from a merged source checkpoint.

## DECISIONS

No source-owned PX branch modifications, no QML credential permission,
no installed Polkit rule, native agent, local database, root key, service
activation, Hospital Burn or automatic merge. Production authorization
remains **HOLD**, including after green CI.
