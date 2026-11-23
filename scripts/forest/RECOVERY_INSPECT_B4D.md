# Forest Core B4d // Read-Only Local Recovery Inspection

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core B4d ↔ Connections C3e/C4b/C5
STAFF: External Hospital-compatible Forest backend DOC (live registration unverified)
STATE: SYNTHETIC ONLY / not installed / production Forest authorization HOLD
OWNER: Forest backend; ForestW and Connections remain independently owned

## IMPLEMENTATION // Actual data mechanism

A Forest attempt is already stored in a SQLite forest_attempts_b3 row
with one local status: RESERVED, ABORTED or COMMITTED. The row is local
writer history, NOT a protected C5 issuer/terminal-receipt database.

A client can lose the reply after the Forest SQLite transaction succeeds.
B4c correctly refuses to resend inference, but its host code deliberately
flattens internal UNKNOWN_HOLD into generic TURN_UNAVAILABLE. That makes
client-facing recovery ambiguous.

B4d adds an explicitly requested, host-authorized **read-only local status**
inspection path named INSPECT_ATTEMPT. It does not alter B3 transactions,
replay policy or the Connections issuer.

- Strict small JSON intent: schema, action, requestId, sessionId, attemptId.
- It accepts neither owner nor caller/permission claims from the request.
- Host verifies the peer and checks the separate INSPECT_ATTEMPT policy, not
  the GENERATE or READ_SESSION permission.
- It joins B3 attempt to B1 owner-scoped session and validates local
  committed replies against an assistant turn in the same session.
- It returns only coarse FOREST_RESERVED, FOREST_ABORTED or
  FOREST_COMMITTED, plus permanent c5Settlement=UNKNOWN_HOLD and false
  retry/revocation/receipt/production authority indicators.
- Missing, foreign-owner, wrong-session or broken attempts fail closed with
  the same host error, without revealing private prompt or output text.
- Works even with an injected SQLite read-only connection. Never opens a
  database path, calls Ollama, starts a service or changes any records.

**Meaning of the three local states:**
RESERVED = inference may still be running OR may have crashed. No replay.
ABORTED = local attempt did not save an assistant reply. That alone does NOT
prove C5 permit/consent was released or revocation completed.
COMMITTED = a local assistant turn is present and linked to the attempt.
That alone does NOT prove C5 issuer received or authenticated the terminal
writer receipt; client-visible completion still needs protected settlement.

The recovery report cannot convert a local COMMITTED row to trusted
COMMIT_CONFIRMED. There is no producer of authentic terminal evidence yet.

## HOW TO USE // Tests only

    python3 -m unittest discover -s tests/forest -p 'test_recovery_inspect_b4d.py' -v

B4d can be exercised against disposable B1/B3 SQLite using the existing
ForestHostAdmission(...) fixture. No new daemon, QML API or private storage
is activated. A future native host must own caller authentication,
process/seat evidence, approved identity, permission and data custody.

## VERIFY / EXPECTED INDEPENDENT REVIEW

Review strict input rejection, separate policy, scoped joins, corrupted
status/reply references, read-only database connection, no retry, no model
execution, lost ACK after actual SQLite COMMIT, and no leakage of model
output, title, prompt or untrusted issuer status. Run B3/B4a/B4b/B4c
regressions in CI to preserve source compatibility.

## WATCH OUT FOR

- Synthetic in-process policy callbacks can be fabricated; they are not
  C3e/C4b process identity or human C5 approval.
- B4d does NOT reconcile or clear UNKNOWN_HOLD. No protected issuer access,
  receipt verification, signing root, independent writer journal, trust
  history, C5 revocation completion, or native host exists here.
- Signed C5 v0 COMMIT intent currently omits Forest sessionId.
  Cross-owner decision remains pending in Issue #2161 and DOC 3 #2233.
- A read-only local SQLite observation is not disk fsync/antirollback proof,
  production authorization or a guarantee that remote revocation was ordered.
- Provisional DELTA disclosure/cancellation remains unresolved. This status
  cannot retract already streamed text.
- Do not connect real personal histories, Leaves, tools or ForestW to
  synthetic B1/B3/B4a/B4c/B4d modules before independent native security
  review and explicit operator deployment acceptance.
- No automatic retry or TTL-based UNKNOWN_HOLD settlement.

## NEXT / DECISIONS

Nurse 2 must independently review the exact PR source before any merge.
Connections DOC 3 owns C5 issuer and grant/receipt evidence, DOC 1 owns
independent installed source/seat trust, Forest backend owns writer and
local result lifecycle, ForestW owner retains UI. After approval, separately
design a protected, **authenticated** recovery inspection contract combining
real writer journal evidence and issuer outcome. Keep current source
non-authoritative and production HOLD.
