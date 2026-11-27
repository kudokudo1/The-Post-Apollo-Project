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


## FL4 // canonical reservation and next owner delivery seam

Nurse #2161 7217350418, Mind #3030. The FL3 bridge opts into a
fixed approved prompt when constructed by the disposable owner. The
existing B3 context conflict metadata preflight remains first;
the canonical Mind first_light_snapshot_in_transaction validates
single input and selects the snapshot in the same BEGIN IMMEDIATE
as the unique reservation INSERT. No general M2 fallback, legacy
exchange, capability selection or default native transport in this
mode. Wrong body now refuses before reservation (not local abort).
FL3's metadata resolver remains an independent currentness check
before/after reservation and before commit. Its transport parameter
comparison still binds the original exact B2 payload/settings.
This is local test composition, not authorization.

Next delivery interface requirements for Runtime/UI1/UI2/Spirit:
owner retains original operation and attempt outside the view.
Separate prepared local intent, admitted execution, original
provisional response and independently recorded local terminal.
Pin one independently observed view incarnation and its original
operation, observe withdrawal explicitly and before every delivery;
never reopen the old delivery or retarget replacement view.
Consume internal R3 sequence in order, bounded UTF-8 response at B1
MAX_BODY (16000), with no raw operation/attempt/session identifiers,
raw error or provider diagnostics in presentation. Coalesced response
snapshots have their own sequence and one response row; final commit
label only after exact original worker completion and journal linkage.
A failed or withdrawn delivery does not cancel/settle the operation
or imply receipt. Stop remains an explicit separately correlated
owner action. Do not relabel R4 status-only fixtures or count a
successful callback as authenticated receipt. Actual owner-side
delivery implementation and recipient authority remain separate
from this reservation patch.

Heart/Spirit native gates remain explicit: actual POST fence on
qualified original source/claim, independently observed pinned
artifact/runner and preventive isolation/egress; independently
current recipient before output release; original effect evidence
must survive crash or unknown. H14-D complete original lifetime
<=60s and <=1s observation gap do not follow from B2 120s deadline.
Do not select relaxed limits or H15 CPU-only exception here. Local
abort, STOP, observer loss or timeout never release a native claim.
No actual model invocation, new issuer, or UI connection in FL4.


## FL6 // Original worker iterator lifetime

The direct host iterator is now acquired once on the original worker,
not a bare suspended generator passed around by callers. Every next
and close checks the original thread object (not a recyclable numeric
thread ID) and refuses reentry. The owner host pins the original iterator
until explicit owner closure or exhaustion. An unstarted iterator that
is closed remains spent, with UNKNOWN_HOLD and no reservation or POST.
Foreign resume/close cannot consume the reservation or run cleanup.
STOP still uses the separate R2/R3 control path. FL5 uses the same
iterator/close contract, with no UI raw-frame exposure.

This is local lifecycle enforcement, not a Python sandbox or process
isolation. The owner must explicitly close/exhaust the iterator; abandoned
host/object finalization and process death are not independently recoverable
effect custody. No native permission, release inference or safe retry.
