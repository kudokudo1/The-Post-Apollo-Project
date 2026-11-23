# Forest Core Performance P1 // Pure Historical Resource Governor

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core Performance P1
STAFF: Forest backend DOC successor, external Hospital-compatible
STATE: synthetic-only contract, no runtime integration
PRODUCTION: HOLD

## IMPLEMENTATION

Resource governance is **not** a new scheduler. The P1 Python module defines
immutable ResourceRequest, ResourceRequirement, ResourceBudget,
ResourceAvailability and GovernorDecision values, and one pure function,
evaluate_resource_request(...). It imports no Ollama/ForestW/Connections
adapter and performs no file, network, process or hardware operations.

It preserves historical precedence:
1. Known resource requirement exceeding an explicit budget -> deny, even if
   the request allows deferral or availability is unknown.
2. Unknown minimum requirement in any dimension -> defer when may_defer,
   otherwise deny.
3. Known positive requirement with unknown/insufficient availability ->
   defer when may_defer, otherwise deny.
4. Otherwise -> approve **modeled resource fit only**.

Dimensions: memory_mib, accelerator_memory_mib, cpu_threads.
None in requirement means UNKNOWN; zero means no additional requirement.
None in availability means UNKNOWN; zero means measured no capacity.
None in budget means no explicit ceiling, NOT zero and NOT known availability.

A request retains task_id, execution_context_id, resolved model_form
(small/big), reasoning_mode (light/normal/deep), priority
(background/standard/interactive), source, reasons and may_defer. Historical
aliases quick -> light, standard -> normal are normalized. AUTO is not a
resolved model form. The ResourceRequirement must refer to the **same
request object**, not a different record with equal values.

A GovernorDecision always has:
- authority_scope = SYNTHETIC_RESOURCE_FIT_ONLY
- production_authority = false
- permission_granted = false
- safe_to_start_inference = false

Even APPROVE does **not** run a model, admit a request, grant C5 consent,
confirm terminal settlement, schedule resources, release revocation or
permit retries. Any resource-approved request needs independent live policy,
current measurements and authenticated authorization from its owning system.

## RECOVERY PROVENANCE

Original preserved Forest sources (read-only, never modified):
The-Post-Apollo-Forest-Project/raw-import/2026-09-22-transfer/
The-Forest/bristlecone/resources/

Files: governor.py, model.py, requirement.py, budget.py, availability.py,
decision.py; semantic normalizers from model_form/model.py and
reasoning/model.py.

Source identities observed at audit:
- governor.py Git blob SHA: 387c260750c6950124fba395fc031e7c70ac5d18
- model.py Git blob SHA: 4359bda6e5911470221c7d20613194e7622e814b
- requirement.py Git blob SHA: 870038a9f389d83c9e9dfe053bc68a74f288db86
- budget.py Git blob SHA: afb686797bb7adf333896b234047a0472803f9c8
- availability.py Git blob SHA: f79ad6078d0d8327bf7cf106daef3e78e3a4cfd0
- decision.py Git blob SHA: 7582ae46a1ef7020e482b57bffa48f6eb45bc2d0

The historical Phase 14.11 L8 A certificate records original governor.py
SHA-256:
9d25c7802f6e58d4b9e8d21eff0252afc84bcc13f6b78533e1aaea
That benchmark/certification is historical evidence, not current Fedora
latency, resource availability, or a production-ready current policy.
Follow recovery/AUTHORITY.md: frozen archaeological material is not
current canonical executable authority simply because a copy survives.

Adaptation differences: kept one isolated module for limited synthetic
tests instead of copying the old package hierarchy. Tightened validation to
reject bool/float/negative/oversized measurements, bounded textual labels,
made the non-authority flags explicit and immutable, and simplified
reason strings to static dimension identifiers rather than interpolating
arbitrary source text. Original policy ordering, reason classifications and
semantic preservation are retained.

## HOW TO USE // Disposable synthetic tests only

From The-Post-Apollo-Project checkout:

    python3 -m unittest discover -s tests/forest -p 'test_resource_governor_p1.py' -v

Tests construct all values in memory. No CLI and no machine integration
are exposed. To assess P1, developers can inspect unit tests and call the
pure function on their own synthetic fixtures. The local Fedora P0 output
(16 visible CPU threads, MemAvailable 2280 MiB, no loaded models at one
observation) is **not** an availability contract; it cannot establish
free GPU memory or model-specific requirements, and is not fed to P1.

## VERIFY // Safe negative matrix

Checks cover policy ordering, exact-budget equality, zero vs unknown
semantics, false/true may_defer, multiple violations, deterministic
reason order, rejected bool/negative/string values, invalid AUTO/model
forms/reasoning/priority, exact resource request object identity, frozen
decisions and non-authority outputs. The CI workflow runs P1 synthetic
tests and the P0 observer, B0 inventory and B2 streaming regressions.

## WATCH OUT FOR

* Not a shared model scheduler, global admission control or resource lease.
* No queue, lock, concurrent account, runtime binding or process watcher.
* No environment variables, Ollama model setting, prompt, output, memory
  storage, C5 authenticated permit or installer interaction.
* Even simultaneous approvals do not imply simultaneous capacity: this
  function does not reserve memory. Current live capacity must be measured
  and controlled by a separately reviewed resource owner.
* Permission and model fitness are different concerns. Approval from P1
  cannot override a C5 HOLD, protected writer uncertainty or revocation.
* No private data, installed DB, live workstation or UI file is changed.

## NEXT / DECISIONS

Independent Forest Nurse 2 must review exact source + CI **before merge**.
User has final acceptance. Keep production Forest HOLD.

P2 should evaluate a separately approved, explicit local inference trial
with cold load and warm first-token times, prompt_eval/eval durations,
tokens/second, memory/VRAM and single-then-parallel workload limits. First
calibrate model/resource requirements instead of copying historical CPU-only
6 GiB/64K assumptions. A P0 data snapshot must never become automatic
production authorization.
