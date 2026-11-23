# 🏥💜 DOC 4 // Hospital C5-H4 native exact-consent hard HOLD

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** Universal Connections · Hospital C5  
**STAFF ROLE:** DOC 4 · external Hospital-compatible, no live registration  
**DEPENDENCIES:** DOC 1 protected C3e custody; DOC 2 verified native host; PX #130/#133 protected Room writer; Hospital UI owner  
**STATE:** source-only signed-issuer development · production Hospital operations HOLD

## IMPLEMENTATION

The existing source-only native issuer validates Linux peer/process identity,
a local active unlocked login1 seat, the protected PX PREPARE nonce/Room/Patient/
revision/graph/preservation eligibility, separate Polkit TRASH/RESTORE actions,
and post-Polkit peer/seat/host/policy/expiry stability. However, before this
change a success status from `/usr/bin/pkcheck` could advance the issuer
to load its protected Ed25519 signing key and send a signed grant to PX.

That was **insufficient for verified human consent**. A permissive or cached
effective Polkit rule may return success without a visible prompt. A normal
authentication agent may ignore `pkcheck --detail` fields or show a generic
message, so no independent evidence exists that the operator saw and
confirmed the exact Room, Patient, action, revision, graph and PX nonce.

**C5-H4 adds a mandatory native hard stop after revalidating Polkit/seat/host/
PX source and before private-key loading.** The new
`_require_independent_room_consent(request, prepared, peer, seat)` currently
raises `HOSPITAL_NATIVE_HOLD // INDEPENDENT_EXACT_ROOM_HUMAN_CONSENT_UNAVAILABLE`
unconditionally. It does not accept an injected claim, environment override,
QML flag, signed local fixture, or disposable public key.

This means the issuer **cannot produce any new signed Room lifecycle grant**
through `_native_step`, even if root-installed, its Polkit action succeeds,
or the signer key is present. This is intentional until a separately
reviewed and independently authenticated consent producer exists.

The previously inherited H2 orchestration fixture has been corrected:
Polkit mock success now expects refusal before `load_installed_key`,
`sign_px_grant` and PX `COMMIT`. The direct disposable signer frame tests
still verify signature schema and PX v12 interoperability, but they are not
a runnable production issuer or an exception to this runtime gate.

## HOW TO USE

No workstation action. The source stays on an isolated GitHub draft branch.
Run the C5-H4 workflow for 16 new negative tests; the inherited C5-H2
workflow still checks the original signer/PX signature and C5-H1 contracts.
Until a future operator-approved independent agent and protected custody
integration, actual Hospital Trash/Restore through this signer is refused.

## VERIFY

The new suite uses mocked Linux/Polkit/PX boundaries and explicitly
asserts that a well-formed TRASH or RESTORE, a zero-exit Polkit decision,
a claimed approved test agent, and environment overrides cannot load
a key, generate a grant or reach PX COMMIT. It checks preflight source
failure, Polkit rejection/timeout, changed seat, revoked policy, and
the exact source ordering between Polkit, denial, signer and COMMIT.

The new 16-case reference and inherited 43 H2 + 40 H1 tests are CI
requirements, **not** native host/human-presence verification.

## WATCH OUT FOR

- This intentional hard stop is not a human-consent UI. No trusted prompt,
  real human gesture or signed native evidence has been created.
- It does not implement DOC 1 independent antirollback custody or PX's
  protected writer and recovery integration; those remain separately owned.
- An isolated test can still directly create synthetic Ed25519 frames for
  schema interoperability. Those local fixture signatures are not
  real operator approval and must never be installed or promoted.
- Replacing this unconditional denial is a **future security-critical scope
  change** requiring responsible-owner approval, real native producer
  executable/release/seat/display evidence, independent one-use consent
  history and an exact per-transaction PX nonce/Room digest match.
- Merely making a test green by mocking the new gate or passing an environment
  variable would be unsafe and must not be accepted.

## CHECKLIST

- [x] Explicit refusal positioned after Polkit and before private key
- [x] Existing positive H2 mocked issuer test changed to require denial
- [x] New fail-closed adversarial suite and CI proposed
- [ ] Exact-head CI verification
- [ ] Independent Nurse 2 pre-merge review
- [ ] Operator merge disposition
- [ ] Approved real trusted consent producer, independent custody and PX integration
- [ ] Real native host acceptance and operator production authorization

## NEXT

Review the C5-H4 exact-head CI and obtain Nurse 2 pre-merge security
assessment. In parallel, ask DOC 1 and the PX owner to agree to the
real consent producer's authenticated identity, exact binding and
durable one-use consume/terminal receipt contract before any future
code changes replacing the hard stop.

## DECISIONS

DOC 4 owns this Hospital C5 gate, not DOC 1 protected identity or
PX database. No production activation, root-key provisioning, local
workstation edits, new signer, QML grants, client fallback, merge,
Hospital Burn or automatic retry.
