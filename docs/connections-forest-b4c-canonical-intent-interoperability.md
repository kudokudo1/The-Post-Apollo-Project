# 🏥💜 Connections Forest B4c // Canonical intent interoperability (reference-only)

**PATIENT:** The-Post-Apollo-Project
**ROOM:** Connections C3e/C4b/C5 ↔ Forest Core B4c
**ROLE:** DOC, external Hospital-compatible; live registration unverified
**STATE:** TEST-ONLY interop, no issuer or native authority, production HOLD

## IMPLEMENTATION

Nurse 2's independent reviews of merged #2168 (two-store revocation reference) and #2171 (signed Ed25519 evidence preflight) identified a real format mismatch. #2171 permits local model names like qwen3:1.7b, while #2168 restricted the model to simple identifier characters. The reference also names consentEpoch as epoch, expiry as expiresAt, and collapses independent claimed source/seat evidence into an untrusted issuerWitness string.

The newly added tests/connections/forest_b4c_fixture_interop.py bridges the *two disposable test fixtures only*. It verifies both distinct role signatures with the existing verify-only #2171 code and preserves the same exact signed canonical intent. The mapping is:

| Signed commit intent | Legacy reference field | Semantics |
|---|---|---|
| principal, tree, userTurn, attempt, request, grant, model, revision, audience, action | Same field names | Exact, no renaming or normalization |
| consentEpoch | epoch | Identical integer |
| expiresAtMs | expiresAt | Identical milliseconds value, no seconds conversion |
| SHA256 of all signed canonical intent bytes | issuerWitness | Untrusted fixture-only byte binding of release/process/seat/challenge claims |

The original #2168 reference now accepts the exact same restricted model grammar as #2171, including colons, dots, slashes and hyphens; the new interop tests compare regex patterns and flags and refuse invalid model identifiers. This does not convert a caller-supplied model string, PID, release digest, current seat or signer key into trusted evidence. The SHA is an exact data-binding witness inside the fixture, *not an independently attested operating system witness*.

The existing #2168 one-operation serial revocation invariant is retained: revoke-first refuses new permits; permit-first keeps revocation unacknowledged until a genuinely proven terminal outcome, and a lost outcome remains UNKNOWN_HOLD with no auto-replay or TTL-based release.

## VERIFY

The GitHub regression workflow runs 12 new signed-to-fence interop tests, the existing 12 signed-role tests, 12 two-store reference tests and 16 Forest B4b pre-commit tests. The new matrix covers local model spelling, typed epoch/time compatibility, exact original intent SHA binding of extra process/seat fields, failed Ed25519 role/intent changes, expired leases, no authority, and ordering in the disposable SQLite fixture. A passing test is **not an installed Forest or C5 authorization**.

## WATCH OUT FOR

The adapter exists under tests/connections only, explicitly marked FIXTURE_ONLY. All #2171 authority fields remain FALSE; #2168 terminal receipts remain test-forgeable. Do not import either into Forest or a live Connections issuer. PREPARE_GENERATE and COMMIT_GENERATE remain separate: initial inference admission is not the final protected commit permit. The actual protected issuer must independently enroll requester and reviewer keys, authenticate an installed Forest commit writer, prove the active seat and human approval, serialize revocation, and verify crash-durable terminal receipts before release.

## NEXT / DECISIONS

Connections DOC owns the Forest-facing C3e/C4b/C5 interface; other Forest backend, UI, Identity production and Hospital/TimeW owners remain separate. Request Nurse 2 exact-head **pre-merge** review for schema parity, no lossy mapping, test-only boundaries and production HOLD. No real personal conversations, signing keys, live host changes or production permissions involved.
