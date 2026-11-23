# Forest Core B4g // Attempt-Scoped Local Outbox Expectation

PATIENT: The-Post-Apollo-Project
STAFF: Forest backend DOC · external Hospital-compatible
ROOM: Forest local recovery classification ↔ protected C5 writer
STATE: SYNTHETIC/DISPOSABLE ONLY
PRODUCTION: HOLD

## IMPLEMENTATION

B4f's read-only inspector returns `LOCAL_EVENT_NOT_OBSERVED` both when a
terminal event was not required and when it should exist but is absent.
An old/restored local database cannot prove which history is genuine.

B4g adds a nullable, checked `outbox_expectation_b4g` column to the B3
**synthetic fixture bootstrap**. The explicit opt-in writer option
`synthetic_outbox_expectation_b4g=True` requires the existing B4f opt-in
`synthetic_terminal_outbox=True` and a B3 fixture with the new column.

The writer inserts `OUTBOX_EXPECTED_V1` in the SAME SQL INSERT and
transaction as the original RESERVED attempt. There is no backfill or
automatic migration. A writer without B4g keeps the nullable field NULL.

`ForestOutboxExpectationInspector` runs the existing B4e/B4f read-only
lineage and local event checks first. It classifies:
- marker present + RESERVED + no event: `EXPECTED_EVENT_PENDING_HOLD`;
- marker present + COMMITTED/ABORTED + no event:
  `EXPECTED_TERMINAL_EVENT_MISSING_HOLD`;
- marker present + valid local event: `EXPECTED_EVENT_OBSERVED_LOCAL_ONLY`;
- marker absent (including old DB without column) + no local event:
  `INSTRUMENTATION_UNDETERMINED_HOLD`;
- marker absent + valid event: `EVENT_OBSERVED_EXPECTATION_UNDETERMINED`;
- malformed marker: `LOCAL_EXPECTATION_INTEGRITY_HOLD` refusal.

An absent marker does **NOT** prove an old legacy writer. A privileged process
can rewrite both the marker and local event, or restore the whole database.
No variant supplies authenticated custody, replay authority, C5 settlement,
revocation completion, or permission to use private conversations.

## HOW TO USE

Only disposable B1+B3+B4f fixtures, never a user's existing database:

    python3 -m unittest discover -s tests/forest -p 'test_recovery_expectation_b4g.py' -v

The inspector requires a host-selected owner/session/attempt scope, but does
not itself verify the host. Do not expose it directly as a network API or
promote its classification to a production security decision.

## VERIFY

Tests cover atomic reservation insertion, failed marker-write rollback,
successful COMMIT/ABORT, event loss following either terminal state,
unmarked B4f history, missing/tampered markers, older fixture without the
column, read-only inspection, wrong owner/session, restored old snapshots and
no private body leakage. B3/B4a–B4f regressions run in dedicated GitHub CI.

## WATCH OUT FOR

Every valid result retains `c5Settlement=UNKNOWN_HOLD`,
`terminalReceiptAuthenticated=false`, `custodyAuthenticated=false`,
`safeToRetryInference=false`, `safeToReleaseRevocation=false` and
`productionAuthority=false`. Missing event evidence cannot permit retry,
even when the local B3 attempt says RESERVED.

No keys, installed issuer, model execution, native service, Linux writer
identity, C5 permit, signed receipt, personal database or ForestW UI changes.

## NEXT / DECISIONS

The next major integration requires independently protected installed writer
identity/current history from Connections DOC 1/2 and genuine one-use C5
authorization/terminal settlement from DOC 3. Mid-stream provisional output
disclosure policy remains open. Independent Nurse 2 review **before merge**,
then operator acceptance; production Forest HOLD.
