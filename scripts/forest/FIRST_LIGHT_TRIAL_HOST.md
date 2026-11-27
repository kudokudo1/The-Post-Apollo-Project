# First Light FL3 // single original public trial host

Development ACTIVE; native/protected/production HOLD. Nurse coordination
#2161 7216643176 / 7216842078; Mind 7216672960; UI2 7216682287;
Heart 7216641267; Runtime 7216363730. One existing B1/B3/M2/R2/R3 route,
not a second production host, journal or scheduler. R5/R6 unchanged.

## IMPLEMENTATION

`first_light_trial_host.py` owns a fresh in-memory B1/B3 disposable
journal, one session, one original fixed public user turn and one
context-bound R3 operation. No path, personal history, Leaf, tools,
group/Clone, credentials, arbitrary prompt, model or endpoint input.
The fixed candidate is Granite3.3:2b, 2048 context, 32 output,
provider-default effort, "Reply with READY." These are evaluation
settings, not operator selection, token/capacity or actual locality proof.
No automatic model load or native transport is installed/defaulted.

Owner-side interface (not wire or UI permission):
- Construct on the owner worker with explicit disposable test transport.
- submit(exact fixed prompt) prepares one local original OperationRef;
  PREPARED is neither model admission nor UI draft consumption.
- run_internal() consumes the existing R3 stream once. Before M2,
  verify exact single-session/ordinal-one/revision-one metadata, then
  compare selected role/content and B2 options before transport entry.
  Internal frames are never forwarded as UI packets.
- request_stop(original operation, exact attempt) uses R2/R3; a STOP
  acknowledgement is not cancellation, provider quiescence or release.
- local_outcome() after worker termination inspects exact local attempt
  and journal linkage separately from R3 UNKNOWN_HOLD.
- close() disposes only this offline journal after worker closure;
  retain original phase and local result in the object, never retry.
  In-memory state is not durable across process death, is not physical
  erasure, and cannot serve as original native effect custody.

The explicit transport is a test dependency, not a grant or enforcement
boundary. It is not an authenticated provider source or sandbox.
No live transport factory, launcher, endpoint, adapter registration,
public API or installed ForestW change. Actual native binding must
replace this test seam only after independent evidence below, including
original custody that survives loss of this disposable journal.

## HOW TO USE / VERIFY

Existing B3 CI runs the new owner-host tests, including actual B2
HTTP encoding to an ephemeral fake peer (test-only endpoint override),
one exact prompt, duplicate submit/run, STOP vs local abort, wrong input,
extra history before body reads and early close. Do not run with actual
Ollama or personal content. No actual capacity or provider behavior claim.

## NEXT / shared trial checklist

1. Heart/Runtime: select exact actual local source/runtime/artifact,
   verified installed manifest and runner/placement, preventive egress,
   explicit bounded workload and enforceable resource ceilings; qualify
   independent demand/capacity and original claim/terminal accounting.
   H9/H14/H15 gates remain; no invented CPU-only or zero device demand.
2. Spirit/Connections: qualify actual operator-approved public source,
   actual recipient and permitted output/currentness, original operation
   and effect custody before dispatch; protected functions remain deny-only.
   No assumption that loopback alone prevents cloud routing.
3. Runtime: bind the exact qualified original dispatch/source/claim and
   independent effect/terminal custody to this one path; no fake grant
   or hidden fallback. Preserve unknown across detach, cleanup and crash;
   no provider retry, no replacement claim, no inferred release from STOP.
4. Mind: inspect exact eligible sole user input and no personal store
   access, actual B2 payload and separate local outcome on same host.
5. UI1/UI2: bind exact original submit/admission/response/STOP to existing
   composer/feed only through independently current authorized projection.
   Distinguish prepared/admitted, provisional, local terminal and unknown.
   Single submit, clear only matching admitted draft; late/withdrawn
   events cannot target replacement view or cancel underlying effect.
   Existing SEND remains locked; no R5/R6 fixture flag conversion.
6. Nurse and operator: approve exact bounded native public trial only
   after actual source/recipient/resource/terminal evidence; verify actual
   model response and independently scoped STOP trial. Then separately
   approve actual user-text scope; durable history/tools/groups later.

No separate preliminary approval for ordinary reversible development.
No native/protected/production permission, actual model invocation or
selected live host by this candidate. Operator integration separate.
