# 🏥💜 DOC 5 // TimeW Scope A C5 test-only spend fence

**Patient:** The-Post-Apollo-Project. **Owner lane:** Connections DOC 5, TimeW-facing C5.
**Phase:** CI-only reference. **Activation:** PRODUCTION HOLD. **Hospital:** external/compatible, live registration unverified.

## Mechanism and scope

`tests/connections/timew/TimeWC5SpendFenceReference.py` is an isolated SQLite fixture for one precise problem: ordering a one-use SPENT record against revocation, even when two processes race and the caller loses its response. It is **not** a protected issuer, signing service, privileged writer, consent UI, or executable geometry adapter. It has no SwayPX/TimeW command path. Every public result says `production_authorized=false`, `native_action_allowed=false`, `retry_allowed=false`, and `production_revocation_ack=false`.

A fixture grant is bound to an exact selection digest, operation intent digest, source digest, operation ID, grant ID, current session, seat, issuer epoch and bounded issue/expiry. These are **caller-provided test inputs**, not independently proven observations. Real Scope A logical rectangles may contain binary64 fractional coordinates. The proposed TimeW/SwayPX native value/wire representation is not yet accepted, so the reference intentionally accepts only opaque hashes and **does not define a geometry serialization format**.

A single SQLite `BEGIN IMMEDIATE` transaction serializes each fixture SPENT versus REVOKED outcome. Revocation before SPENT means no future spend of that fixture; after SPENT, the result remains `SPENT_REVOCATION_PENDING_UNKNOWN_HOLD`, not an acknowledgement that native side effects cannot still occur. An absent database is an error, not proof of unused permission. A missing grant returns `ABSENT_UNKNOWN_HOLD`, not a reusable slot. Lost response after a committed SPENT is not retried.

**Important limit:** a same-UID actor can replace/rollback this disposable SQLite file. SQL `synchronous=FULL` and write ordering are not independent custody. Real release requires separate trusted signer/enrollment, key revocation, active unlocked seat, native SwayPX selection, protected nonrollback grant consumption and correlated per-command native receipts. A TimeW-local journal and the C5 authority are separate stores; either missing, conflicting or uncertain side must remain UNKNOWN/HOLD.

## Ownership

- **DOC 5:** This new independent C5 TimeW reference and eventual issuer-side interface proposal; no production wiring.
- **DOC 1/DOC 2:** C3e/C4b installed producer, process/release/host, signer/seat provenance; no writes from this PR.
- **DOC 4:** Hospital-specific C5 and protected Room writer; no sharing of Hospital signing audience, key or grant.
- **TimeW owner:** saved-checkpoint consumer, local journal and geometry state; no files modified here.
- **SwayPX owner:** real compositor-selected surface, lifetime, fractional-coordinate contract and guarded native commands; no files modified here.
- **Nurse 2/operator:** independent security review and distinct merge/native/production acceptance.

## Verify

Run from the repository root on Linux:

```sh
python3 -B -I tests/connections/timew/test_timew_c5_spend_fence_reference.py
```

Tests cover lost-reply replay, both SPENT/revoke orderings, issuer/seat/session/intent/source substitutions, wrong audience and bad time/type, duplicate issuance, absent store and **two separate Linux processes racing to spend the same fixture**. These tests demonstrate isolated fixture ordering only; they do not verify real kernel identity, actual consent, installed trust or native window mutation.

## Integration gates

1. DOC 5 and C3e/C4b/TimeW/SwayPX owners agree on a versioned protected Scope A selection + operation digest contract with exact binary64 geometry and source phases. This fixture is not the wire standard.
2. Independent approved installed C5 service establishes operator consent for the displayed exact selected surface, target, unlocked session/seat, and original requester, with issuer-owned keys and storage protected against same-UID rollback.
3. Real SPENT/dispatch/resize/move/final receipts are independently reconciled across C5, SwayPX and TimeW; all lost or contradictory outcomes hold, with no retry or undo.
4. Independent Nurse 2 pre-merge review, negative native tests, owner approvals and separately explicit operator production acceptance.

**Recovery pointer:** [TimeW integration issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067), [TimeW owner outcome matrix #2125](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2125), [SwayPX fractional geometry #173](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/173).
