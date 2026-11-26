# Forest I2 // Exact Model Form binding reference

PATIENT: The-Post-Apollo-Project · ROOM: intelligence management
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator approved continuation after I1. R2 #2423 merged 4b945976
with independent scoped PASS; I1 #2426 merged 063a747a, 75/75 and
4/4, independent review still due at preparation.

Original Forest archive model_form/registry.py blob
bda9f7063ef85fe61e59e228a25c0751a5d61f6b and resolution.py
82ed54f75d490560dab993f55584fc029f22e3c5: immutable form-to-binding,
freeze once, missing slot refuses rather than substitute.
I2 consumes already frozen I1 recommendation. Does not yet recover
full historical exact-turn/task override/pinned baseline control.
Adds exact synthetic artifact digest, runtime instance/version/release
digest and configuration digest/context/output bounds. No arbitrary
runtime options, endpoint, path, credential or adapter execution.
Digest strings are references, not computed or independently verified.
Registry scope is owner/Tree plus revision; per-turn evidence binds
the exact selected binding and R1 context/Clone/turn. Missing or
changed evidence, missing slot, unknown installed/capability data,
unsupported required model feature or insufficient context => no
matching reference. No downgrade or alternate-model selection.
Model features are illustrative normalized inference features, not
R2 Workshop capabilities or C5 permissions. Actual normalized producer
and feature registry remain unimplemented. Preserve exact input reference
on retry comparison only, no rebind or permission to retry.
Public status reports only reference match, static reason, requested and
recommended form. Actual resolved form/binding stay null.

## HOW TO USE / VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_model_binding_i2.py' -v

20 focused cases + I1/R1/R2/P1 regressions. No live model data used.

## WATCH OUT FOR / CALIBRATION
B0 model inventory and P2C reported bytes/context/residency do not provide
independent digest/currentness or peak incremental resource requirements.
No automatic import of same-login UI equipment preferences. Future
measured trial must bind exact model/runtime/config plus hardware/device,
context, workload, reasoning and isolation, and distinguish baseline,
peak, incremental demand and actual availability. P1 fit remains pure,
not allocation. Unknown is not zero. Do not use disk size, resident
bytes or DRM headroom as calibrated requirements. No trial authorized.

## NEXT / DECISIONS
Independent review I1/I2. Recover exact evidence producers and calibration
contract in bounded next work. Current C5 native private operation remains
deny-only. No model load, tool execution, DB, private data, OS mutation,
new service or production authorization.


## H16a // Model form and reasoning controls (design only)

Operator development direction #2161 7204485179 and Nurse 7204663398
authorize this one existing document. Heart 7204268249/7204297064,
Runtime 7204297523, Mind 7204266103 and Spirit 7204281045 concur.
No runtime code, persistence, adapter, issuer or model action.

### Historical semantics recovered

Frozen Forest repository 28895aafdddb07cf402f1e75574eea1ee79a516d,
raw-import/2026-09-22-transfer/The-Forest/bristlecone/:
- model_form/control.py dfecc786: context-specific Auto/Pinned baseline;
  task-specific Small/Big override is not a turn-counted lease.
  Changing baseline preserves the Task override; guarded clear matches Task.
- model_form/resolution.py 82ed54f7: resolve once, exact binding lookup;
  absent selected slot refuses, not fallback.
- reasoning/control.py 18d651ff: separate explicit, temporary, pinned and
  automatic reasoning; lease ID and mode checked before decrement.
- runtime/task_session.py a2458c4e lines 7375–7523, 7534–7765 and 12900+:
  successful-turn finalization reloads current state under write lock,
  preserves a replaced/cleared lease and updates matching lease after
  success. Detached preview can change its local copy, not durable state.
  Historical lock/atomic YAML and retry sequencing do not establish an
  independently durable one-use operation receipt across crashes/effects.
  The pure decrement helper alone can consume the same decision again
  while its matching lease remains active.
- model_form/handoff.py eb85443: actual effective Small/Big transition in
  one context/Task; no provider session, KV or continuity payload.

### Selection order (candidate recovery, not a new API)

| Priority | Model form | Reasoning |
| --- | --- | --- |
| 1 | Exact-turn Small/Big | Explicit turn effort; no lease consumption |
| 2 | Matching Task override | Current matching temporary lease |
| 3 | Pinned effective baseline | Pinned effective baseline |
| 4 | I1 Auto recommendation | Automatic reasoning |
| 5 | Historical Small recommendation when Auto result absent | No additional historical precedence |

The operator's Tree-level default profile is a proposed refinement to
historical per-context baselines. Independently establish the authorized
context baseline or authorized absence permitting a Tree default. A
missing, unreadable, denied, ambiguous, stale or foreign control snapshot
is not authorized absence. Do not silently substitute Auto or Small.
Historical default Small and historical five-turn reasoning setting are
not newly selected product defaults, resource requirements or permission.

Bind original owner/Tree/member, TaskContext and execution lifetime, turn,
input revision/commitment, control and registry revisions, operation and
attempt, purpose and recipient. Independently qualify control mutation
and metadata disclosure separately from effective decision and use.
No hidden override/lease details in public refusals. Resolve the chosen
form and reasoning once for the original governed turn; preserve I1/I2
exact comparison and H1 settings digest semantics. Explicit unbound or
unsupported form refuses. Provider-specific actual reasoning behavior,
token/context/output limits and current calibrated resource demand are
separate prerequisites, not inferred from the preference. No automatic
model installation, downgrade, new form registry or second governor.

### Temporary reasoning and original settlement

The historical success/supersession semantics are retained. A future
implementation needs a separately owner-defined governed successful
meaningful-turn event and durable original operation settlement, with
independent current lease identity, revision, mode and remaining count.
Reserve/account concurrent uses against that exact lease so competing
turns cannot exceed the remaining allowance. Do not select a durable
transaction topology or receipt source in this document.

A preview, selection, navigation, explicit/pinned/automatic decision,
failed or unknown effect must not persist a decrement. Unknown original
use remains pending and fenced until independently reconciled; it is
not a free retry or restored allowance. Repeated observation of one
settled original turn cannot decrement again. Newer replacement/clear
must remain intact when a prior in-flight turn settles; retain original
outcome and pending custody rather than mutate the replacement. Lease
supersession does not establish absence of a prior effect. No transfer
or reset through another member, task, restart or execution incarnation.
Task override persists for its exact authorized task, not a turn lease
or automatic inheritance to a successor assignment.

Runtime owns the actual governed event, original transaction and effect
reconciliation; Spirit owns current control authorization and recipient
scope; Heart owns effective form/effort and resource references. The
historical local write lock is not independent authority or crash-safe
external settlement. No executable lease consumption is implemented.

### Continuity and resource boundary

Persistent Tree/member/chat identity does not pin provider identity or
grant simultaneous capacity. A genuine effective Small/Big transition
is a form handoff; same-form model replacement and execution succession
are different events. Do not rewrite earlier authorship/history, copy
old KV/cache, transfer permissions or assume old context remains
eligible. Mind owns independently authorized context recomposition and
provenance, including M7e exact input/recipient boundary. A model change
requires fresh exact binding and independently qualified resource claim;
settle any outstanding original execution separately with H11/H2,
independent terminal/quiescence/retained accounting and Spirit
settlement. No release from model selection, chat persistence or a
temporary lease adjustment. Shared Tree defaults and model weights do
not imply shared active context, resource credit or tool permissions.

### Negative acceptance cases for later separate executable scope

| Case | Required behavior |
| --- | --- |
| Exact-turn vs Task vs pinned vs Auto conflict | Apply original precedence only to independently qualified controls. |
| Different Task override or foreign context/lifetime | Never transfer override; establish authorized current absence before lower precedence. |
| Missing, stale or denied control snapshot | HOLD; no implicit Auto/default. |
| Missing selected binding or unsupported actual reasoning | Refuse; no silent downgrade or substitution. |
| Baseline changed with matching Task override | Preserve authorized Task override for its original scope. |
| Explicit effort while lease active | No temporary consumption. |
| Preview, failed/unknown effect, repeated original completion | No persistent decrement from preview/failure/unknown or duplicate; reconcile original pending use. |
| Concurrent governed turns exceed remaining count | Refuse excess; no overconsumption or new lease identity bypass. |
| Old completion after lease replacement/clear/revoke | Preserve replacement; settle original only, never infer prior effect absence. |
| Same form with different model/recipient, or execution succession | Not a form handoff; independently qualify new binding/context/permissions/resources. |
| Form handoff with old terminal/accounting unknown | Retain original custody; no resource transfer, replay or replacement admission. |

No source of independently current control/policy, durable lease
consumption, effective adapter behavior or native resource qualification
is established by this document. Existing I1/I2/H1/H2 code unchanged;
exact candidate reviews and CI required at substantive completion.
Operator integration separate. Native/protected/production HOLD.
