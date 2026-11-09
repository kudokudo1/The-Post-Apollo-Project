# 🏥💜 C3e-S // Exact signature-verified bytes in durable evidence ledger

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · Protected signed evidence  
STAFF ROLE // DOC · Original protected Connections assignment  
ASSIGNMENT // Fix independent Nurse 2 finding R-1, C3e-R signed-evidence digest TOCTOU  
BASE // Current main after merged C3e-Q #1615 and C3e-R #1618  
CONCURRENT OWNERS // C2v/C4b Silverblue runtime and rollback, C5 consent  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-Q verifies a detached signature over a bounded, nofollow file snapshot, then parses that exact byte sequence. C3e-R previously **reopened the original evidence pathname after Q verified it** to compute the SHA-256 stored in the durable challenge ledger. An attacker replacing that file between signature verification and the second read could cause R to record bytes that were never signed or checked.

C3e-S closes that specific audit-integrity gap without adding an external trust authority:

1. C3e-Q now includes `verifiedEvidenceSHA256` in its CI receipt, computed directly from the **same `signed` bytes** returned by `verify_detached` and already parsed and checked. No second evidence file opening is required.
2. C3e-R takes only the digest in that verified receipt and validates its exact lowercase SHA-256 shape before doing the existing `BEGIN IMMEDIATE` atomic single-use challenge consumption.
3. An adversarial test hooks the exact point **after** Q's valid signature and independent pin checks, but **before** R commits, replacing the caller-controlled evidence pathname. The ledger must contain the original signed content's digest, not the substituted bytes. Subsequent duplicate challenge use still refuses.
4. C3e-Q's original 20 real detached GPG tests, C3e-R's prior durable replay suite, C3e-I signed recovery, and C2n deny-only invariants stay in regression CI.

This is a narrow DOC-owned repair to source that already merged. The extra diagnostic digest does **not** change production authentication, credentials, grant/consent or host enrollment. No C4b guest files, C2v rollback logic or TASKS C5-owned code were modified.

## HOW TO USE

Only the ephemeral GitHub Actions workflow `.github/workflows/connections-c3es-verified-byte-digest.yml` executes these tests. The user does not need to modify their Fedora/Silverblue desktop.

## VERIFY

- [ ] Exact-head C3e-R entire durable replay suite, including path-swap adversary, passes.
- [ ] C3e-Q detached-signature and signed recovery regression suite passes.
- [ ] Root-pinned admission, fake signed RPM, Grammar pass on exact head.
- [ ] Independently review TOCTOU repair, tests and associated trust boundary.
- [ ] Operator decides merge/acceptance separately from CI.

## WATCH OUT FOR

The repaired audit digest proves only **which input bytes the CI test signer signed**. It is **not a real Silverblue guest measurement**. The C3e-R SQLite database is **not independently rollback-resistant**; a privileged actor could restore the entire local database. C3e-Q's ephemeral signer is not operator enrolled, and its statement could describe false process facts. These tests do not show signed package installation, a running systemd/D-Bus/SELinux origin, independently trusted cross-guest signer or human consent.

The new receipt digest is diagnostic, not a production attestation, approval token or authorization for Connections credentials. C4b owner still controls the actual guest measurement and rollback, tracked by [issue #1606](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/1606).

## CHECKLIST

- [x] Confirm C3e-R corrected mainline CI finished 4/4 and independent review finding R-1.
- [x] Fix exact signed-byte digest reuse and add post-signature pathname substitution test.
- [x] Keep C2v/C4b and TASKS C5 files untouched, all production flags false.
- [x] Add independent CI and durable handoff.
- [ ] Run exact-head tests and independently review.
- [ ] Operator merge/acceptance separately.
- [ ] Actual C4b guest producer, independently enrolled attestation origin, durable protected nonce/witness custody and consent remain unsolved.

## NEXT / DECISIONS

After C3e-S is verified and reviewed, work should move to real C4b-owner guest-origin evidence, not another simulated identity contract. Preserve source ownership, release trust and production HOLD. No local machine changes, live credentials, provider calls, production activation or Hospital registration.
