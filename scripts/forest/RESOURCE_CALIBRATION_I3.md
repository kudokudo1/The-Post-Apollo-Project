# Forest I3 // Workload resource calibration reference

PATIENT: The-Post-Apollo-Project · ROOM: Spirit resource management
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator approved I3 after I2 #2430 merged 05dc8dc3. I1 and I2
independent reviews still outstanding at base reconciliation.
Responds to ForestW #7129692749 calibration handoff. Reuses exact
I2 binding, frozen reasoning, P2A/P2B trial design, P2C diagnostic
distinctions and P1 resource policy without changing those modules.

I3 is a pure, synthetic reference for observed baseline, peak and
incremental demand in bytes. A calibration profile binds exact model
artifact/runtime/config, machine/boot/hardware digest, measurement
scope, one accelerator target (or unknown), workload digest, baseline
residency/cache fingerprint, reasoning, prompt tokens and CPU thread
limit. Separate cold and warm scenarios; exact same profile only.
One cold or up to three warm trial references, duplicate IDs refused.
This is not an enforceable trial-count controller.
Incremental demand = observed peak - baseline within the same trial.
Across trials take maximum of per-trial deltas, not difference of
unrelated maxima. Unknowns propagate per dimension. Incomplete or
uncovered trial invalidates aggregate, no cherry-picking. A CPU limit
is configuration, not measured CPU requirement; absent accelerator
target never proves zero VRAM demand. Load, first visible content and
completion duration fields remain distinct, optional nanoseconds.
Observed peak is not guaranteed maximum, requirement, free capacity
or admission. Memory domain must be consistent and include baseline.
Match to I2 reference only; actual producer and evidence authentication
are not implemented. Metadata projection rounds bytes up to MiB and
keeps actual requirements, availability and reservation unresolved.

## HOW TO USE / VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_resource_calibration_i3.py' -v

20 new tests plus inherited I2/I1/R1/R2/P1. No probes, provider calls,
model load, tool calls, filesystem changes, actual calibration or private data.

## WATCH OUT FOR / native trial design (proposal only)
1. Independently verify exact installed artifact digest, original runtime
   instance/version/release, effective settings (including context,
   output, actual reasoning adapter behavior and CPU/GPU placement),
   machine/boot/device/driver, workload and measurement scope. B0/P2C
   names and resident bytes alone cannot supply that evidence.
2. Establish safe initial workload and conservative independent capacity
   estimate BEFORE trial approval; do not use the trial itself to justify
   starting an unknown-risk configuration. Read-only diagnostics first.
   If capacity cannot be independently established, HOLD.
3. Agree exact model, synthetic public workload, limits, one cold if
   naturally absent or at most three sequential warm if resident,
   deadline, thermal/memory/swap abort policy and separate operator
   consent. Do not force unloading, change service, or retry.
4. Measure process/cgroup host memory and exact accelerator allocation
   over the same run and verified baseline. Identify coverage limits,
   cache/other allocations and driver counter semantics. Do not sum
   devices or confuse RSS, shared memory, VRAM, residency and free
   capacity. P2B existing runner does NOT collect such peak evidence.
   P2C is diagnostic only. No native sampler implemented here.
5. Review exact measurement method, coverage and workload applicability;
   establish a conservative independent modeled requirement and margin
   separately. Do not turn an observed maximum into a guaranteed
   requirement. Only then pass exact request-bound requirements and
   independently current availability/budget to P1; reserve capacity
   separately before execution. This PR intentionally does not populate
   ResourceRequirement from observation alone, nor change P1.
6. Abort on changed identity/config/device, concurrent interference,
   OOM, pressure, invalid measurements or missing terminal response.
   Keep original outcome, no automatic retry. No private prompts,
   traces, output or new telemetry persistence.

## NEXT / DECISIONS
Independent review I1/I2/I3; next evidence-producer and trial measurement
design with ForestW, then separately approved native sampling scope.
No duplicate governor, scheduler or new service. No workstation changes.
C5 native private integration remains separately HOLD.
