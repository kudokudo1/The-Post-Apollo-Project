# Forest Core Performance P2A // Bounded Cold/Warm Benchmark Design

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core backend, performance measurement
STAFF: Forest Core DOC successor, external Hospital-compatible; no live registration verified
STATUS: DESIGN ONLY; no benchmark runner or inference
PRODUCTION: HOLD
REVIEW: Forest Nurse 2 independently, before merge; operator final acceptance

## IMPLEMENTATION // What actually happens

A local Ollama inference request uses the existing server to load a
model when needed, evaluate a synthetic prompt, and generate an answer.
A streaming client observes the first usable answer fragment and a
terminal provider packet. These timings measure different processes
and should not be collapsed into one "AI speed" number.

Forest P0 already performs two read-only local requests, GET /api/version
and GET /api/ps, and reads bounded host resource hints. Forest P1 is a
pure synthetic resource-fit policy (approve/defer/deny), not a reservation
of RAM, VRAM or CPU. Forest B2 performs explicitly invoked POST /api/chat
streaming, with context bounds from 512 to 8192 and limited output, but
its current public COMPLETE event excludes provider timing counters.
P2A does not modify any of them.

This proposal specifies a future dedicated benchmark. It does NOT create
a benchmark runner, make a model request, start a server, load a model,
change Ollama settings, write private files or activate ForestW/C5.

## HOW TO USE // Safe commands that already exist

Read-only observer on an operator-controlled host with Ollama already on:

    python3 scripts/forest/performance_snapshot_p0.py snapshot

Pure synthetic tests:

    python3 -m unittest discover -s tests/forest -p 'test_resource_governor_p1.py' -v

There is deliberately no P2 command or runner in this milestone.
Do not substitute direct ollama run, curl /api/chat, ollama stop, model
unloading, or service restart for the reviewed future benchmark.

## MEASURE // Two independent sources of timing

A future reviewed runner would use a monotonic clock for:

- request_start_ns: immediately before the request send;
- headers_received_ns: first successful HTTP response headers;
- first_content_ns: first nonempty assistant message.content fragment;
- terminal_received_ns: valid, final done=true packet.

Derived client measures:

- headers_latency_ms = (headers - start) / 1e6;
- time_to_first_visible_content_ms = (first_content - start) / 1e6
  if any assistant content appeared;
- client_complete_ms = (terminal - start) / 1e6, only if complete.

Stream fragments are NOT individual tokens. A first answer fragment
measures visible responsiveness, not exact internal first-token timing.
Thinking-only fragments do not count as answer content. Missing first
content stays null rather than zero.

Ollama terminal provider metrics (nanoseconds unless otherwise noted):
total_duration, load_duration, prompt_eval_count,
prompt_eval_duration, eval_count, eval_duration, optionally
prompt_eval_cached_count, and terminal model/done/done_reason.

- Report duration fields in milliseconds after dividing nanoseconds
  by 1,000,000.
- Generated-token throughput = eval_count * 1e9 / eval_duration only
  when both fields are valid and strictly positive.
- Do not divide by zero, substitute missing values with zero, or
  infer token count from the number of network stream packets.
- prompt_eval_cached_count is optional and version-sensitive.
  The running 0.32.14 installation has not been verified to emit it.
- Provider total_duration is not the same as network-inclusive
  client_complete_ms.
- These counters do not certify any C5 permission or GPU capacity.

Official documented API references:
https://docs.ollama.com/api/chat
https://docs.ollama.com/api/ps

## PROPOSED METADATA-ONLY RESULT CONTRACT (not implemented)

One bounded summary per synthetic trial would include only:

    schema: post-apollo.forest.performance-benchmark.proposal-p2a
    status: COMPLETE | INCOMPLETE | REFUSED
    scenario_id: fixed public synthetic-case identifier
    trial_index: bounded integer
    model_name: validated name; model digest if safely verified
    ollama_version: validated version
    model_resident_before: PRESENT | ABSENT | UNKNOWN
    model_resident_after: PRESENT | ABSENT | UNKNOWN
    requested_context_tokens: bounded integer
    requested_output_tokens: bounded integer
    requested_reasoning: explicitly documented fixed setting
    concurrency: 1
    headers_latency_ms: nonnegative number or null
    first_visible_content_ms: nonnegative number or null
    client_complete_ms: nonnegative number or null
    provider_total_ms: nonnegative number or null
    provider_load_ms: nonnegative number or null
    provider_prompt_eval_count: nonnegative integer or null
    provider_prompt_eval_ms: nonnegative number or null
    provider_prompt_cached_count: nonnegative integer or null
    provider_eval_count: nonnegative integer or null
    provider_eval_ms: nonnegative number or null
    provider_generated_tokens_per_second: number or null
    before_host_mem_available_mib: nonnegative integer or null
    before_resident_vram_bytes_reported: nonnegative integer or null
    c5_authority: NOT_EVALUATED
    permission_granted: false
    production_authority: false

Exclude raw prompts, answers, tool calls, thinking traces, private paths,
user/session identities, payload bytes, credentials, permissions and
model storage locations. The benchmark must discard generated content
without printing, persisting or sending it to ForestW or another service.
A fixed public synthetic prompt may be embedded in a *future* reviewed
runner; personal project content must not be used as benchmark input.

An incomplete, malformed, timed-out or cancelled stream is INCOMPLETE,
not a successful generation. Never retry automatically.

## EXPERIMENT PLAN // P2B, only after separate approval

Start with no parallel model work or auxiliary model service.
Proposed exploratory maximum: one permitted cold attempt and three
sequential warm attempts, all with identical static synthetic prompts.

| Case | Preflight | Meaning |
| --- | --- | --- |
| C0 | Target model ABSENT in /api/ps; safe headroom independently established; new operator approval | Pre-request nonresident request, NOT clean OS boot |
| W1-W3 | Same model PRESENT before each; no intervening eviction/restart | Within-model warm timing variability |
| S0 | No active generation; P0 observation | Post-test residency and host hints |
| Later P2C | Matched settings and a separately approved larger sample | Potential comparison of model or configuration changes |

Never unload a running model just to make a cold sample. If the model
was already resident, C0 is SKIPPED; do not use ollama stop,
keep_alive=0, a new service or a forced cache flush. If the warm model
is absent, invalidate W instead of relabelling it.

Keep model digest/quantization, runtime version, context, output limit,
reasoning behavior, prompt, system load and other models consistent.
Actual initial values such as 4K context, 128 output tokens, and a
bounded deadline must be fixed and reviewed before running, not guessed
from CPU count or historical test parameters. Hermes 64K context and
B2-compatible 4K-8K context are different scenarios and cannot be
directly compared.

A cold trial can load weights and affect residency. A warm trial can
affect caches. Explicit operator authorization is required even if the
model is already installed. No benchmark starts automatically upon
install, merge, import or launching ForestW.

## SAFETY PREFLIGHT AND ABORTS

1. Obtain exact approval for model, prompt, context, output bound,
   maximum requests and local execution time. The design itself
   grants none.
2. Inspect current model identity, installed artifacts, memory
   requirements, available free GPU/RAM headroom, active inference,
   and desktop contention. P0 only reports occupied model VRAM,
   not free GPU capacity; 16 CPU threads and MemAvailable=2280 MiB
   previously observed do not establish safe additional capacity.
   Unknown requirements or GPU headroom require HOLD, not estimates.
3. Fix a literal loopback endpoint and refuse redirects, remote APIs,
   URL credentials, tools, cloud fallbacks and unbounded responses.
4. No model pulls, service starts/stops, forced unload, systemd edits,
   environment changes, additional daemons or persistent telemetry.
5. No second concurrent model request during the first campaign.
   Two P1 APPROVE results do not reserve capacity.
6. Abort on user cancellation, unexpected model substitution,
   unexpected co-running model requests, OOM, swap/thermal pressure,
   malformed final metrics, excessive time or over-limit output.
   No hidden retry, stale-session replay or release of C5 revocation.
7. C5 provisional text disclosure and authenticated terminal receipt
   remain separately owned by Connections. Synthetic benchmark text
   must never be treated as authorised ForestW streaming output.
8. No private prompts, Hospital/PX DB, local personal memory or
   protected keys. Even a local performance log needs separate
   operator-approved retention and storage scope.

## VERIFY // Planned disposable negative matrix

Before any future live benchmark:
- no approval => no POST or model load;
- invalid endpoint/redirect/model identity/context => refuse;
- free GPU requirement unknown => HOLD, not fabricated headroom;
- malformed JSON, duplicate keys, negative/boolean/nonfinite
  metrics, excessive body or line => refuse;
- stream truncated, no valid final packet, two finals,
  wrong model, tool call, thinking-only output => INCOMPLETE/refuse;
- missing optional cached count => null, never zero;
- zero eval_duration => no throughput value;
- cold/warm residency mismatch => SKIP/invalidated, never force unload;
- no content or private prompt/response/think values in result output;
- no auto retry, extra processes, external calls or configuration;
- B0/P0/P1/B2 and C5 contracts remain unchanged.

All CI for a future runner must use fake loopback/in-memory fixtures;
GitHub CI must never execute actual Ollama generation.

## RECOVERY PROVENANCE / EVIDENCE LIMITS

Historical Forest L9 and L10 A benchmarks are preserved in
The-Post-Apollo-Forest-Project/raw-import/2026-09-22-transfer/
The-Forest/bristlecone/backups/phase14_11L9_A_recovery_certified_20260813T023040Z/
and phase14_11L10_A_sustained_certified_20260813T033046Z/.

L10 A's eight real model turns support a historical sustained-session
health observation, but its own analyzer refused speed improvement and
memory-leak claims. Those Qubes/CPU-era values are not Fedora/GPU
measurements. This P2 design requires the same distinction between
observed sample, timing mechanism and causal performance conclusion.

## CHECKLIST / NEXT / DECISIONS

P2A definition of done:
- [x] Specify signals, units, cold/warm residency definitions and privacy
- [x] Define negative tests, host safety checks and concurrency limit
- [x] Preserve historical and current Forest source boundaries
- [ ] Independent Nurse 2 review of exact design before merge
- [ ] Operator accepts design and makes merge decision
- [ ] Separate, explicitly authorised P2B runner and live experiment

No benchmark runner, inference, configuration change or local write
is included in P2A. This document is not a permit, scheduler or claim
of performance improvement. Forest PRODUCTION remains HOLD.
