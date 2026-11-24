# Heart H4 // Visible CPU constraints

DOC 1F · DEVELOPMENT ACTIVE · PRODUCTION HOLD.

## IMPLEMENTATION
Read existing explicitly selected non-root Linux cgroup-v2 only.
Reuse I5 bounded path, mount and descriptor helpers. Pin all visible
non-root ancestor directories; twice read each cpu.max quota/period
and leaf cpuset.cpus.effective. Refuse absent/malformed counters,
changed quota or exact normalized CPU mask, mount/scope change or
completed sampling window over one second. No controller writes.

CPU-time ceiling hint = minimum of effective CPU count and every
finite ancestor quota/period ratio, expressed in millicpus, rounded
down. 1000 millicpus represents one CPU's time per period on average;
1500 represents 1.5 CPU-equivalents, not a limit of 1.5 threads.
Unlimited quota is not idle capacity. Do not round fractions up.
No CPU IDs, paths or raw counters in public output.

## HOW TO USE
After independent review/merge, from repository root:
    python3 -B scripts/forest/heart_cpu_constraints_h4.py observe --cgroup /system.slice/ollama.service
Select only an explicitly established group. No model/service mutation.

## VERIFY
    python3 -B -m unittest discover -s tests/forest -p 'test_heart_cpu_constraints_h4.py' -v
Disposable fd fixtures and optional Linux self-group observation.
A skipped native check is not acceptance.

## WATCH OUT FOR
A quota is shared across descendants and does not describe idle CPUs,
instantaneous execution rate, burst behavior, thread affinity or
actual configured runner threads. Hidden ancestors, controller absence,
hotplug and competing workloads may affect effective capacity.
Selected path is not authenticated runtime identity. Missing counter
refuses rather than assuming unlimited. Two samples do not constitute
an atomic snapshot; the one-second window is a post-read check, not
a hard I/O deadline. Do not convert millicpus to P1 cpu_threads.
No inferred safe-start, resource reservation or permission.

## NEXT / DECISIONS
Use alongside H3 memory observations, not as trusted resource grants.
Runtime must establish enforceable device/thread settings, actual
service scope and calibrated requirements before native admission.
Nurse2F independent review and operator-approved native trial remain.
