# Forest Core B4e // Local Recovery Lineage Integrity

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core B4e, local writer recovery
STAFF: external Hospital-compatible Forest backend DOC, live registration unverified
SCOPE: Forest-only local synthetic status integrity; production authorization HOLD

## IMPLEMENTATION

Nurse 2 retrospective review #6018265030 found B4d's COMMITTED inspector
checked role and session but did not cross-check the originally reserved user
turn, ordinal, provider/model or expected revision. B4e closes that local
data-integrity gap WITHOUT altering the original B1/B3 SQLite schema.

The B4d inspector now joins B3 attempts with their original B1 user turn and
linked assistant reply, and validates:

- The reserved user turn exists, is a user role, and belongs to the exact
  owner-scoped session (a valid foreign key by itself is insufficient).
- The original user ordinal is positive; the attempt's expected revision
  cannot precede that ordinal. B1 session state transitions may increase
  revisions separately, so revision and ordinal are NOT required to match.
- Attempt timestamps cannot precede original user recording; update cannot
  precede reservation; local current session revision cannot precede reservation.
- COMMITTED replies must link to assistant role in the SAME session, with
  ordinal exactly one greater than the reserved user turn, model matching
  the original attempt, provider exactly ollama and recording after reservation.
  Session revision must have advanced past the reservation revision.
- RESERVED/ABORTED attempts still may not reference any reply turn.
- Invalid local lineage fails closed with LOCAL_INTEGRITY_HOLD; the separate
  host boundary maps such failures to uniform ATTEMPT_UNAVAILABLE, preserving
  owner and session isolation.

No prompt, answer body, title or owner identity is added to the read-only
response. Local FOREST_COMMITTED remains distinct from C5 trusted terminal
settlement (always UNKNOWN_HOLD in this synthetic module). There is no retry,
manual recovery mutation, new database opener, service listener or actor key.

## VERIFY

Run:
    python3 -m unittest discover -s tests/forest -p 'test_recovery_lineage_b4e.py' -v
    python3 -m unittest discover -s tests/forest -p 'test_recovery_inspect_b4d.py' -v

The new 21-case adversarial test suite corrupts otherwise FK-valid links:
wrong assistant within same session, wrong original user/other session,
wrong role/provider/model, revision and ordinal mismatch, timestamp drift,
and preserved later state-revision compatibility. CI also exercises B3,
B4a, B4b and B4c regressions.

## WATCH OUT FOR

This is a more reliable interpretation of *local* SQLite structure, NOT
independently attested writer custody or antirollback protection. Any writer
with unrestricted SQLite access can still fabricate consistent rows. Neither
C3e/C4b installed-peer proof, C5 human consent, serialized revocation,
authoritative writer receipt, encryption, native storage nor protected
UNKNOWN_HOLD reconciliation exists in this change. Provisional streaming
disclosure and cancellation are also unresolved.

Connections' versioned signed session binding remains separately owned.
No Connections, Identity, Hospital or ForestW files change. No production
personal data may be connected or model tools enabled.

## NEXT / DECISIONS

Require exact-head **independent Nurse 2 review before merge** and operator
acceptance. Retain production HOLD until real process authority, a protected
writer/issuer terminal proof and native secure storage are verified.
Issue #2161 remains the cross-owner handoff.
