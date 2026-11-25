# Runtime H13 // Native enforcement intake

DOC2F Runtime, Forest Integration; development ACTIVE, native/production HOLD.
H9 owner agreement and Heart succession #2161 comments 7168380016,
7168891934; current source main dcf22ace4872fab3e408051650980483dbe52e7c.
This document specifies an evidence and decision contract, not an approved
native runner, implementation authority, or a workstation procedure.

## Actual execution seam and gaps

B3 turn_bridge_b3.py c5dbbc29 checks current context and STOP, reserves
a durable attempt, then calls its streamer. The generator is lazy:
construction of the iterator does not send a request. B2
ollama_chat_transport.py db572336 serializes model/messages/stream and
options.num_ctx/num_predict, connects to loopback, then calls
HTTPConnection.request("POST", "/api/chat", body=payload, ...). That
call is the first possible prompt-bearing network effect. The current
loopback restriction is not authentication, runner exclusivity, or an
exact model digest check. B2 STARTED is a validated HTTP response, not
runner placement. B2 COMPLETE is a response marker, not physical idle.
B3/R3 local commit/cleanup and socket shutdown do not prove provider
quiescence, external settlement, or released memory.

H1 TransportSettings digest binds the existing B2 subset, not all
effective native settings. H11 AttemptRef adds exact I2 ModelBinding
and H1 TransportSettings to task/turn/operation/attempt. Retain this
reference; do not silently broaden H1 digest meaning or reconstruct
from a mutable model tag. No native settings or admission inferred from
the R6 synthetic child.

## Proposed H13 decision and evidence sequence

1. H12 read-only intake first: existing Heart observers, exact service
   identity, installed artifacts, current load/pressure and device mapping.
   No guessed PID/FD or privilege escalation. An existing Ollama service
   cgroup and API inventory do not establish which runner handled a
   particular operation. Missing observation or stale scope is HOLD.
2. Choose exactly one reviewed execution path, placement and host.
   Either existing B2 conversation or existing P2B benchmark, not both
   for the same attempt. A proposed public Granite3.3:2b 2048/32 workload
   is not a selected installed artifact or authority. Shared service
   requires independently established exclusivity throughout admission
   to terminal accounting. A local mutex, no model in ollama ps, and
   one client socket do not exclude other clients. If exclusivity
   cannot be established, HOLD; a separately approved isolated
   disposable host/runner is an alternative proposal, not a fallback.
3. Freeze the owner-side manifest: exact TaskContext/operation/attempt,
   I2 binding (artifact, adapter, runtime instance/version/release),
   H1 settings, fixed public workload byte commitment, serialized
   request digest, requested context/output/thread/device/think/retention
   policy, independently evidenced effective constraints, clock domain,
   provider/runner lifetime, exclusivity lifetime and one-use admission
   bound to current Heart demand/budget/availability. No default
   assumption for an unsupported field. Any additional native settings
   require versioned owner agreement rather than changing H1 semantics.
4. Before body assembly and before request, independently recheck
   Security authority at each relevant effect boundary (read vs
   release), current original TaskContext and admitted attempt, immutable
   payload and recipient, current capacity and exclusivity. Protected
   use remains denied; the public trial needs explicit operator approval.
   Admission, one-use effect fencing and final pre-send ordering must be
   specified with Security. A boolean callback or an earlier read-only
   snapshot is not a protected fence. Refusal before send must not
   imply no effect from a preceding reservation. No automatic resend.
5. During one admitted attempt: bind actual runner/process lifetime
   (not PID alone) and request/attempt to exact loaded artifact and
   effective context/output/placement/limits. Provider accepted options,
   service cgroup ceiling and model tag are not evidence of effective
   runner behavior; CPU quota is time, not thread count, and host
   memory cgroup limits do not establish a GPU VRAM ceiling. Actual
   effective context/template token accounting, device attribution,
   thread policy and keepalive behavior need supported independent
   witnesses; missing one required witness prevents acceptance. Reuse
   Heart's same-domain bounded baseline/peak/post observations; no new
   background collector or shared-service mutation.
6. Terminal: separately reconcile B3 local outcome (B4d), transport
   result, attributable provider terminal and independent runner
   quiescence/no outstanding work, current H11 resource accounting and
   Security settlement. Do not equate socket EOF, STOP acknowledgement,
   HTTP done, local COMMITTED, no displayed resident model or old
   PID disappearance with all of these. Unknown stays fenced and
   conflicting admission blocked, no retry/unload/restart. Retained
   shared weights may stay only under independently current accounting;
   do not add resident bytes to available capacity.

## Revision 1 // Heart owner correction

Heart #7169431384 requests preventive enforcement, not retrospective
confirmation. The prospective integrated conversation route is B2 via
B3/R3 with the existing H11 reference. P2B is a separate timing experiment
which currently bypasses B3/H11; it must not be presented as the integrated
route or reuse its attempt. No route is currently authorized to execute.

Three distinct evidence objects must be agreed before executable scope:

- Requested immutable native manifest: versioned canonical commitment
  separate from H1's existing config digest. Bind exact original H11
  attempt, installed artifact and runtime release/instance, selected
  placement, fixed public workload/serialized payload commitment,
  requested options/limits and exclusive execution lifetime before claim
  and possible send. The future claim/settlement owner must retain this
  original commitment durably across loss/restart, not reconstruct it
  from a mutable tag, provider PID, later settings or current label.
  No persistence or new schema authorized by this document.
- Independently established preventive envelope: actual enforceable
  pre-send resource ceilings, placement, exclusion of competing clients,
  original process lifetime and current capacity/authority. Requested
  options alone, API success and measurements collected after send cannot
  qualify this envelope. Failure or unknown before send remains HOLD.
  Preserve existing H1 ZERO_DEMAND_UNESTABLISHED refusal. A CPU-only route
  cannot use guessed zero accelerator demand or dummy positive values;
  independent no-accelerator proof and a separately coordinated H1
  revision would be required.
- During-run observation: independently attributable effective runner
  settings, placement, process lifetime, actual context/template usage and
  bounded baseline/peak/post evidence tied to that original commitment.
  Evidence of a mismatch after dispatch is not a preventive control.
  Fence the original effect, refuse further admission, retain custody;
  do not infer rollback, retry, or alter a shared provider. Provider
  replacement invalidates new dispatch and cannot replace original
  terminal evidence. Terminal/quiescence and accounting must independently
  reference the original attempt and immutable manifest even after loss;
  missing original evidence remains UNKNOWN_HOLD.

H14 needs supported conservative incremental RAM/VRAM/CPU demand
including overhead and a safety margin for the exact artifact/runtime/
placement. Disk size, hypothetical KV arithmetic, a stale free-memory
snapshot and unmatched observed peaks cannot establish a bound.
Qualification on another approved host is a separate option only.

## Required review and negative acceptance matrix

- Wrong artifact, runtime generation, model label, config, workload,
  principal/Tree/task, operation/attempt, or current recipient: refuse.
- Stale/unknown demand, scope, capacity, clock, effective settings,
  unproved exclusivity or different runner/device: HOLD.
- Second concurrent client/request, provider replacement, lost runner
  identity, settings drift: refuse further dispatch and preserve
  ambiguous original effect, no inferred terminal.
- STOP before dispatch, STOP after dispatch, HTTP failure before
  response, lost completion after local commit, provider idle unknown:
  keep separate local/transport/provider/settlement evidence, no retry.
- Bounded observation coverage and exact post-terminal accounting;
  a missed peak is not a proven bound. Positive native acceptance only
  for the selected manifest and authorized attempt, never global
  admission or protected release.

Heart owns H12/H14 capacity and demand, H15 calibration evidence;
Runtime owns effective enforcement, exclusive dispatch and terminal
correlation; Security owns independent authority/effect/settlement;
Mind owns context assembly and source eligibility. Nurse2F approves
exact scope and verifies evidence independently. Operator approves
exact host, manifest and trial before any actual model execution or
configuration action. No source changes to B2/B3/H1/H2, no process
start, pull, service restart, model unload, native execution, new
daemon or store. R7b scope review remains independent.