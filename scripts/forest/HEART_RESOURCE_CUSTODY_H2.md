# Heart H2 // Disposable single-slot custody

DOC 1F · Forest Heart · DEVELOPMENT ACTIVE · PRODUCTION HOLD.

## IMPLEMENTATION
One in-process ResourceCustody instance per disposable host. Claim
recomputes H1 inside a lock; only one active reference at a time.
Retain original TaskContext, turn, operation and attempt. Refuse reuse
of operation, attempt or exact context/turn. At 256 completed or active
claims, refuse further claims instead of forgetting history. No expiry
or automatic retry.

API proposed to DOC2F:
- claim_reference(original, current, now_ns=...) -> fixed reference status.
- observe_terminal_reference(AttemptRef, outcome=..., clock_domain=...,
  observed_ns=...) -> fixed state. Accept only NOT_DISPATCHED, COMMITTED,
  CANCELLED, FAILED or UNKNOWN fixture terminal references. STOP,
  transport COMPLETE/EOF and R2 commit entry are not terminal outcomes.
- account_release_reference(ReleaseReference, now_ns=...) -> fixed
  reference status. Require a separate later resource observation in
  the original clock domain, within H1 age limit, same availability
  source label, all capacity dimensions known, no active workload.
  Account for any resident model in remaining availability.
- status() -> redacted reference-only state, all authority flags false.

UNKNOWN and conflicting/repeated terminal reports retain custody.
Terminal alone does not release the slot. A different task needs new
H1 captures strictly after the previous release and a distinct attempt.
A low or zero post-release capacity is a valid observation, not a
promise the next task fits. The next claim recomputes H1.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_heart_resource_custody_h2.py' -v
Dedicated tests include 16 eight-thread simultaneous-claim races.

## WATCH OUT FOR
This is local reference accounting, not physical resource reservation,
provider cancellation, authenticated terminal evidence or durable
custody. Caller supplied references, times and source labels are
forgeable. A second instance/process is outside the lock. Restart
does not restore custody and must not be used to clear ambiguity.
Do not wire this as live admission or replace B3 original-attempt
recovery. A real host must own one custody boundary and recover
uncertain attempts; no actual generation or hardware mutation here.

## NEXT / DECISIONS
DOC2F accept/revise exact API and terminal mapping; align with R2
STOP/commit arbitration, not a duplicate. DOC4F journal and DOC3F
release ownership unchanged. 256-reference limit is a provisional
disposable test bound, not a production lifetime limit. Nurse2F
independent review required. Native resource producer, enforceable
runtime settings, durable custody and approved live trial remain HOLD.
