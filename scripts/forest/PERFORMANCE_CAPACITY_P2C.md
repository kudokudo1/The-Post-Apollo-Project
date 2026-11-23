# Forest Core Performance P2C // Read-Only Fedora Resource Diagnostics

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core performance / native benchmark preflight
STAFF ROLE: Forest backend DOC successor (Hospital-compatible external)
STATE: source only, local execution not performed by this PR
PRODUCTION: HOLD

## IMPLEMENTATION

P2C adds a read-only, operator-invoked diagnostic. It reuses B0
inventory GET /api/tags and P0 GET /api/version plus GET /api/ps.
It does not send inference requests, load a model, start/stop a server,
change settings, write files or inspect private task/session storage.

It reads fixed Linux DRM sysfs counters for card0..card7:
- /sys/class/drm/cardN/device/mem_info_vram_total
- /sys/class/drm/cardN/device/mem_info_vram_used

These counters may exist on AMDGPU; their absence does not mean no GPU.
Virtual, integrated and multi-GPU devices may expose different
semantics. Total minus used is only a reported instantaneous headroom
estimate, NOT safely allocatable memory. No GPU is mapped to Ollama
or chosen automatically, and separate devices are not summed.

The report distinguishes kernel host MemAvailable, visible logical CPU
count, schedulable process CPU affinity and installed model artifact
size. None alone establishes a per-model requirement, safe free
RAM/VRAM, concurrency capacity or thermal headroom. Model names and
counts come from local Ollama; no private paths are queried.

The report includes permanent negative-authority fields:
benchmark_permitted=false, permission_granted=false,
production_authority=false, model_requirements_established=false,
resource_budget_established=false, exclusive_capacity_reserved=false,
ollama_device_mapping_verified=false.
No P2B run may infer approval from a P2C report.

## HOW TO USE

After independent Nurse 2 review, operator acceptance and merge,
from the project root:

    python3 scripts/forest/performance_capacity_p2c.py inspect

Optional exact installed model filter, manually selected:

    python3 scripts/forest/performance_capacity_p2c.py inspect --model 'MODEL_NAME'

This is observation only; no flags permit inference.
Optional endpoint is pinned to literal loopback by B0/P0 validation.
Remote hosts, credentials and redirects are refused. Unknown counters
remain null instead of invented zero. Output is one JSON record.
The diagnostic itself never persistently writes a result.

## VERIFY

Disposable CI uses a fake localhost Ollama service and mocked host and
sysfs counters, never a real model. Tests cover GET-only contract,
no approval authority, exact installed/resident model checks, malformed
or oversized GPU numbers, unknown/split GPU devices, invalid URLs,
failed provider responses, no private data leak and no runtime imports.
P2B, P1, P0, B0, B2 and C5 deny-only regressions also run.

## WATCH OUT FOR

- No actual Fedora free GPU memory or safe allocatable RAM has been
  independently measured yet.
- Earlier operator-reported P0: Ollama 0.32.14, no loaded model, host
  MemAvailable 2280 MiB and 16 visible threads. Those data may be stale.
- Installed model size is NOT the working RAM/VRAM requirement.
- Sysfs reports may be absent, virtual, inaccurate or on an unrelated
  GPU; absent metrics mean UNKNOWN, not zero.
- CPU affinity is not free dedicated execution threads.
- P2B relies on externally reviewed capacity numbers and operator flags,
  not trusted live memory reservation. P2C never fills those flags.
- Nurse 2 P2B review was still pending at this checkpoint; P2C review
  cannot substitute for that missing independent gate.
- No ForestW, C5, Hospital/PX or SwayPX changes are included.

## CHECKLIST

- [x] No new network route or model process
- [x] Fixed host sysfs reads only, bounded to eight card slots
- [x] Unknowns preserved, no inferred policy authorization
- [ ] Exact-head CI and independent Nurse 2 review
- [ ] Operator final acceptance/merge

## NEXT / DECISIONS

Before any real Fedora benchmark:
1. Review and accept P2B and this P2C diagnostic independently.
2. Establish selected installed model, calibrated model RAM/VRAM,
   effective memory/cgroup capacity and correct GPU mapping.
3. Verify other model-server owners, thermals, and desktop load.
4. Obtain operator approval for the exact single-run synthetic workload,
   model, limits and trial count. P2B never has autonomous retries.
5. Report actual first-content, load, prompt and generation metrics.

Forest production stays HOLD. P2C is observation only.
