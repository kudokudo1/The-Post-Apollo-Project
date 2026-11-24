# Forest Heart H3 // Visible hierarchy memory headroom

DOC 1F · First-Tree resource observation · DEVELOPMENT ACTIVE · PRODUCTION HOLD.

## IMPLEMENTATION
Explicit existing non-root cgroup, reuse I5 bounded path/mount/directory
helpers and P0 MemAvailable reader. Hold descriptors for every visible
non-root ancestor; read memory.current, memory.max, memory.high twice
in opposite traversal order and sample host MemAvailable before/after.
Recheck visible path identities and mount. Refuse missing/malformed
counters, changed limits, changed visible scope or completed sampling
window over one second. The time check is post-read, not a hard IO timeout.

For each finite limit compute max(0, limit - larger sampled charge);
take minimum across ancestors, round down to MiB. memory.high is a
throttling threshold, not a hard ceiling. The reported headroom hint is
the minimum of host available and visible finite max/high headroom.
Unlimited is separate from zero; no omitted ancestor on missing data.
No swap treated as extra available RAM; no new CPU/GPU probes.

## HOW TO USE
After review and merge, from repository root on the intended Linux host:
    python3 -B scripts/forest/heart_memory_headroom_h3.py observe --cgroup /system.slice/ollama.service
Use only an explicitly verified service cgroup. This reads counters,
does not start, stop, load or modify a model/service.

## VERIFY
    python3 -B -m unittest discover -s tests/forest -p 'test_heart_memory_headroom_h3.py' -v
Tests use disposable directories and optional real Linux self-group
observation; a skipped native case is not native acceptance.

## WATCH OUT FOR
The selected path is not an authenticated runtime identity. Visible
hierarchy may omit hidden ancestors; mount namespace, sibling workloads,
reclaim, shared pages and concurrent allocations can change headroom.
Two samples are not atomic or continuous, and ABA changes can evade
rechecks. MemAvailable is a kernel estimate; cgroup charges are not
deduplicated physical memory. The hint is not a guaranteed allocatable
quantity or a workload requirement. No positive safe-start, permission,
reservation, CPU/GPU availability or production flags.

## NEXT / DECISIONS
Proposed one-second completed sampling window, max/high conservative
hint, no inference. Need verified provider group mapping, device scope,
enforceable runtime settings, independently established model demand
and headroom margins before safe native admission. Do not wire hints
directly into P1 as trusted availability. H2 remains local fixture
custody, not durable admission. DOC2F and Nurse2F review requested.
