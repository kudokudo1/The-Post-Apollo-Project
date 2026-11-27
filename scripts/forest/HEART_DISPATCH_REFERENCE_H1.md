# Forest Heart H1 // First-Tree dispatch reference

PATIENT: The-Post-Apollo-Project · DOC 1F Heart · DEVELOPMENT ACTIVE · PRODUCTION HOLD.

## IMPLEMENTATION
Owner coordination: issue #2161 comments 7139439017, 7139564594,
7139617637 and 7139601126. Reuse I1 recommendation, I2 binding and P1
resource governor, with canonical B6-R1 TaskContext supplied by Mind.
Runtime retains transport, actual admission/dispatch and terminal events.
This additive in-process candidate compares two exact references.

Proposed API: TransportSettings(model, num_ctx, max_predict);
DispatchSnapshot(binding, settings, operation_id, attempt_id, clock_domain,
captured_ns, request, requirement, budget, availability);
compare_dispatch(original, current, now_ns=...) returns fixed HOLD projection.
Settings digest is SHA-256 of sorted compact ASCII JSON with explicit
schema, fixed default literal loopback endpoint, model, num_ctx and
max_predict. This covers only the current B2 subset. No provider-wide
config attestation; DOC2F must confirm the encoding before integration.
Current B2 bounds: context 512–8192, output 1–512. Exact selected model,
explicit form, interactive base Tree, chat capability required.

Recompute I2 and P1. Require budget for every dimension, never treat
unknown demand as zero, and refuse zero incremental demand since B2
does not enforce CPU-only/device/threads. Require exact operation/attempt,
context, configuration, evidence, request and all resource values.
Proposed reference age limit 5 seconds on one supplied clock domain;
second capture strictly later, not future. A change, including available
capacity even if still fitting, holds rather than silently replaying.
This intentionally strict comparison may be impractical for noisy native
metrics; revise with Runtime before deploying. No numeric capacity
thresholds beyond the explicit supplied ceilings.

## HOW TO USE
Developer-only in-process module; run tests on disposable fixtures.
No native command, service, timer, queue or execution path.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_heart_dispatch_reference_h1.py' -v

## WATCH OUT FOR
Supplied clocks, resource evidence and identity references are forgeable.
Equality and age arithmetic are not actual freshness, independent source
authentication, reservation, thread/device enforcement or atomic dispatch.
P1 approve remains modeled fit only. Every result is UNKNOWN_HOLD;
safe_to_start_inference and all authority flags false. No automatic retry.
No shared B2/B3, journal, C5, UI or existing I/P-series source edits.
No native inference or workstation mutation.

## NEXT / DECISIONS
DOC2F accept/revise concrete interface and settings encoding; Nurse2F
independently review. Actual host-owned current resource observation,
safe conservative limits, one-in-flight custody, dispatch fence and
terminal resource-release evidence remain necessary. No new issuer, DB,
or substitute trust authority. No production or private access.


## H7 // Original Forest recovery: frozen resource request preparation

Recover the mechanism in original Bristlecone
[resources/request_preparation.py](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/28895aafdddb07cf402f1e75574eea1ee79a516d/raw-import/2026-09-22-transfer/The-Forest/bristlecone/resources/request_preparation.py)
(blob 3e7d3f46293b428046249da6d1306c5c3e0218c3). Its frozen form,
reasoning and context are now the already-integrated I2/I1/B6 references.
H7 adds `prepare_resource_request(binding, settings, *, priority, source,
reasons=(), may_defer=True)` inside H1, not a second resource governor.
It derives task, execution context, form and reasoning from the validated
binding, preserving exact settings and all existing first-Tree refusals.
H1 compares the derived request to its supplied request on evaluation.
The caller uses the exact returned request object to construct P1
ResourceRequirement, and retains the binding/settings in the snapshot.
P1 request equality alone is not proof of turn identity, source
authenticity, freshness or resource reservation. No priority inference.
No native execution, automatic model selection, provider callbacks or
reused historical resource measurements. R6 remains untouched.

Next: separately review workload-specific residency-aware requirements;
do not subtract generic resident bytes from available RAM or import
historical CPU-only calibration. Mind owns context selection, Runtime
owns actual execution. See issue #2161 comments 7160677299 and 7160733041.


## H17 // Reasoning selection versus actual provider behavior (design)

Operator standing ordinary development #2161 7204485179 / 7204663398.
H16a #2970 and H16b #2973 integrated; H16c #2985 is an independent
reference candidate, not a live adapter. This section does not require
its unmerged code or change any existing executable path.

### Recovered concrete source gap

Frozen original Forest 28895aafdddb07cf402f1e75574eea1ee79a516d,
bristlecone/reasoning/router.py 8174ccb0 computed prompt-shape signals
and selected Light/Normal/Deep. Its historical score used character
thresholds 800/2000, line threshold 20, question threshold 3, code
fences and up to three complexity-marker groups. Score >=3 selected
Deep; a small simple turn or eligible quick marker selected Light;
otherwise Normal. This is historical deterministic usefulness logic,
not token counting, permission, actual model effort or resource demand.
Do not run the old text extractor on protected content or accept
unbounded caller-provided markers/counts. Actual input eligibility and
bounded work remain independently required.

Original runtime/adapters/hermes.py f535c6a0 lines 1821–1877 mapped
Light/Normal/Deep to low/medium/high in model_options.reasoning_effort.
That is the historical Hermes payload request, not proof of model
support or applied effort, and not an Ollama API mapping.

Current Post-Apollo source at 0e9de42c:
- I2 e8a9a5d1 recognizes the feature label reasoning; this describes a
  reference capability, not a provider-specific supported option set.
- H1 62dc22ec retains canonical reasoning in the P1 request and original
  binding; its existing settings digest covers endpoint/model/num_ctx/
  max_predict only.
- B2 db572336 explicitly emits options.num_predict and options.num_ctx
  with no think or reasoning setting. The transport contract 010a5e12
  explicitly excludes thinking options.
- Therefore selecting Deep rather than Light in the reference does not
  establish a different actual request or different provider behavior.
  Do not claim connected reasoning controls from H16 or current H1.

### Next actual adapter boundary

Heart owns canonical requested effort, exact model-binding compatibility
and demand calibration. Runtime owns adapter option negotiation,
serialization, exact request dispatch and original effect identity.
Spirit owns control-source authority and recipient disclosure. Mind owns
eligible input and the actual payload boundary. No live option expansion
is authorized by this document.

Before a provider-specific effort can become executable:
1. Establish exact installed model/artifact, provider/runtime version
   and capability/option semantics from an independently qualified
   source. A reasoning feature label, generic model family, user
   preference or historical Hermes mapping is insufficient.
2. Distinguish requested canonical effort, the concrete supported
   option/value, and independently observable actual behavior. An
   unsupported or unknown mapping refuses the requested operation; do
   not silently downgrade, substitute another model, or assume omitted
   options enforce a provider default. A provider with only a binary
   control cannot be advertised as having three verified levels without
   an explicit supported policy and honest presentation.
3. Bind the exact effective request, adapter/version, options and model
   identity to the original input/operation and current eligibility.
   The existing H1 settings digest must remain unchanged for its old
   B2 subset; a reviewed versioned extension is needed for new settings,
   never an unbound side option added after original admission.
4. Calibrate the selected configuration and actual workload separately.
   Reasoning mode, output budget, context limit, generated tokens, peak
   RAM/VRAM, retained allocations and latency are not interchangeable.
   Do not infer demand from the historical routing score or setting.
5. Preserve original effect, lease reservation and terminal/accounting
   boundaries. A rejected option, transport failure or unknown effect
   is not permission to retry with a different effort or consume a
   temporary lease. Release still requires original H2/H11 evidence.

Review the actual Runtime adapter contract and source feasibility before
selecting a wire field or implementing provider negotiation. Reuse the
existing dispatch and model-binding ownership; no second provider
registry, settings writer, governor or synthetic authority.

No new code, classifier, model calls, storage, native observation or
changes to H1 digest, I2 feature grammar, B2 transport or protected
permissions in this slice. Native/protected/production HOLD.
