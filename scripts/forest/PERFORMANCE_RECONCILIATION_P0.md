# Forest Core Performance P0 // Read-Only Baseline and Historical Reconciliation

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core performance foundation
STAFF: Forest backend DOC successor, external Hospital-compatible
STATE: additive source proposal, unactivated
PRODUCTION: HOLD
FOREST NURSE 2: independent exact-head review required BEFORE merge

## IMPLEMENTATION // Mechanism

This milestone reuses the B0 loopback endpoint parser; it adds **no new
background service, scheduler, queue, model runtime, or network listener**.

The explicit CLI runs exactly two GET requests on the same pinned literal
loopback host (unless an earlier response fails):
1. \`GET /api/version\`: provider-reported Ollama version;
2. \`GET /api/ps\`: the currently resident models, provider-reported size,
   GPU-memory residency and context length.

It then reads only fixed Linux \`/proc/meminfo\` (MemAvailable) and
\`os.cpu_count()\` (process-visible logical threads). No other proc files,
personal data, process lists, model manifests, or secrets are read. The output
is one bounded JSON snapshot. It has no persistent log or database writes.

Resident models may change between requests. The API is not a coherent
hardware allocation snapshot: \`size_vram\` is Ollama's reported resident
GPU-memory quantity, **not free VRAM**; MemAvailable is a broad kernel
estimate and may not reflect container/cgroup allocations; CPU count is
not a safe concurrency limit. A null quantity means UNKNOWN, not zero.
The reported round-trip time covers two GETs, not time to first token.

## HOW TO USE // Optional operator-run inspection

From the project root, only on a machine where Ollama is already running:

    python3 scripts/forest/performance_snapshot_p0.py snapshot

Optional fixed localhost port:

    python3 scripts/forest/performance_snapshot_p0.py snapshot --endpoint http://127.0.0.1:11434

Exit code 0 = bounded valid observation; 2 = safe refusal. Only
localhost/127.0.0.1/::1 are allowed, with canonical literal host normalization
reused from B0. No credentials, redirects, arbitrary URLs or network hosts.
The command does not preload, configure, pull, run or unload models.

GitHub CI never probes the runner's Ollama. It uses a disposable fake
127.0.0.1 HTTP server with deterministic responses.

## Historical provenance // Preserve instead of silently copying

Historical frozen source:
\`The-Post-Apollo-Forest-Project/raw-import/2026-09-22-transfer/The-Forest/bristlecone/resources/governor.py\`

Recovery authority:
\`The-Post-Apollo-Forest-Project/recovery/AUTHORITY.md\`

Historical L8 A backup result:
\`raw-import/2026-09-22-transfer/The-Forest/bristlecone/backups/phase14_11L8_A_governor_certified_20260813T005056Z/l8_governor_summary.json\`

The L8 summary reports historical governor.py SHA-256
\`9d25c7802f6e58d4b9e8d21eff0252afc84bcc13f6b78533e1aaea\`
and whole live pipeline median 449.952 microseconds in its old environment.
These are **historical** certification claims, not modern Fedora benchmarks.

The recovered governor evaluates a frozen request against budget,
requirement and current availability with outcomes \`approve/defer/deny\`.
Its semantics for \`None\` are meaningful: unknown requirement/availability
is not zero; no explicit budget ceiling is not a measured availability.
The original function performs no scheduling, hardware probing or runtime
modification. This P0 observer does **not** promote or execute that governor.

Compatibility matrix:

| Historical field / contract | Current P0 observation | Gap |
| --- | --- | --- |
| availability memory_mib | MemAvailable hint in MiB | Not an effective per-task budget |
| accelerator_memory_mib | Ollama reported resident size_vram | Not free accelerator memory |
| cpu_threads | Visible logical CPU count | Not free dedicated threads |
| ResourceRequirement | None | Needs measured model-specific calibration |
| ResourceBudget | None | Needs explicit owner policy and operating headroom |
| SharedModelResidency | /api/ps model names | Does not verify session/binding identity |
| Quick/Standard/Deep | None | B2 currently permits 512–8192 context |
| First-token latency | Not measured | Requires explicit, separately reviewed inference trial |
| Two Tree concurrency | Not measured | Requires controlled workload and safety budget |

## VERIFY

    python3 -m unittest discover -s tests/forest -p 'test_performance_snapshot_p0.py' -v

Includes endpoint abuse, malformed and oversized JSON, duplicate models,
unknown residency fields, fixed schema, no POST/inference, no data leak,
optional CPU hints, Linux MemAvailable parsing and CLI failure behavior.
No actual hardware benchmark is claimed by CI.

## WATCH OUT FOR / DECISIONS

- This observer is diagnostics only; \`generation_requested=false\` and
  \`production_authority=false\`.
- Historical CPU-only calibrations, such as 6144 MiB or 64000 context,
  are NOT migrated into current Fedora/GPU policy.
- C3e/C4b installed writer identity and C5 one-use permit/terminal custody
  remain separate prerequisites. Resource sufficiency is not consent.
- No ForestW UI, System Settings, Ollama environment variables, local
  machine config, model inference, benchmark workload or service changes.
- No inferred performance improvement until real before/after measures.

## NEXT

P1: read-only pure governor contract adaptation with synthetic fixtures and
explicit UNKNOWN handling, after reviewing Forest Nurse 2's P0 findings.
P2: independent operator-approved controlled inference benchmark recording
cold model load, warm TTFT, prompt_eval_duration, eval_duration, tokens/s
and GPU/CPU residency. Start with one model/one request, not a new daemon.
P3: concurrency and hot-context proposals *only if P2 justifies them*.

User final acceptance and native machine testing remain separate gates.
