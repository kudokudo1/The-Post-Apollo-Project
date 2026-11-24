# Forest I5 // Passive cgroup-v2 resource accounting

PATIENT: The-Post-Apollo-Project · ROOM: Spirit measurement infrastructure
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator continued I5. I1 #2426, I2 #2430, I3 #2435 and I4 #2441 merged;
independent reviews outstanding at preparation. Four additive Core-only
paths. No change to CPU++'s separate Quickshell PSS observer, ForestW,
Connections, I4 or existing resource governor.

I5 reads selected existing cgroup-v2 kernel counters, not individual RSS
sums. Kernel memory.current accounts memory charged to the cgroup and
descendants, including kernel and cache charges. It is not unique physical
memory, a PSS sum, model weights or full machine use. Shared pages may be
charged elsewhere; different accounting domains are not additive.
No automatic process or service selection. Operator supplies exact
non-root hierarchy path. Restrict mount layout and path segments;
walk anchored no-follow directory descriptors; only fixed counter files,
bounded reads, pin selected group and compare device/inode and mount
reference at end. Detect observed replacement and discard partial report.
No claim of uninterrupted identity, membership, namespace or mount
continuity, model mapping or workload coverage. Read-only, no privileged
access, process discovery, process control, network, inference or writes.

Report memory.current first/last/sampled maximum and sampled increase;
separate optional kernel memory.peak, swap, local memory.max (including
unknown vs unlimited), memory.stat anon/file/shmem (overlap: do not sum),
CPU accounting deltas in microseconds, pids.current (tasks, not process
count). Kernel peak has kernel/version/reset semantics; not trial peak.
CPU includes descendants. Unknown values remain null. Local memory.max
is not effective ancestor limit, available capacity or reservation.
Refuse counter regression or observed local-limit change. At most ten
samples with 100–500 ms intervals (max 4.5s scheduled sleep, not a hard
wall-clock deadline). No automatic I3/P1 requirement conversion.

## HOW TO USE
After review, merge and operator acceptance, inspect existing systemd
service group from the repository root (no sudo):

    group="$(systemctl show ollama.service --property=ControlGroup --value)"
    printf '%s\n' "$group"

Only if it is the intended existing non-root group:

    python3 -B scripts/forest/cgroup_observation_i5.py observe --cgroup "$group" --samples 5 --interval-ms 250

If Ollama is not a system service, use the actual appropriate existing
group, not a guessed path or root. Do not start/restart it just to measure.
This is not authorization to inspect other users' workloads. Unsupported
mount or inaccessible counters refuse/return unknown. Paths and raw
counter files are not printed. The output is a diagnostic reference only.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_cgroup_observation_i5.py' -v

Native Linux CI reads its existing kernel group via private helpers;
fixture tests exercise public observer and scope failure paths. Native
test may read root only in the test harness if runner's own cgroup is
root; public CLI rejects root. No cgroup creation or limit changes.
I4/I3/P1/P2C regression checks included.

## WATCH OUT FOR
Actual Ollama service/runner membership, model ownership and device mapping
are not verified. A service may contain unrelated workloads, or model
workers may live elsewhere. Cgroup-v2 charged pages differ from process
RSS/PSS; do not sum across overlapping groups or compare different
measurement domains as though they were equal. memory.current and
memory.stat are sequential observations, not atomic. Kernel peak and
sampled maxima cannot establish guaranteed requirements. No effective
ancestor capacity, safe allocatable RAM/VRAM or CPU budget inferred.
No private data access, cache eviction, context resize or model load.

## NEXT / DECISIONS
Independent review. Next independently scoped runtime identity and
measurement attribution, then separately reviewed accelerator evidence
and native calibration plan. Existing P2C device-wide readings are not
model GPU memory. No automatic reservation or model execution.
