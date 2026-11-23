# Forest Performance P2B // One-Shot Synthetic Benchmark Runner

PATIENT: The-Post-Apollo-Project
ROOM: Forest Core P2B performance measurement
STAFF: Forest backend DOC successor; external Hospital-compatible
STATE: source-only opt-in implementation; CI uses disposable fake HTTP server
PRODUCTION: HOLD
REVIEW: independent Forest Nurse 2 before merge, operator final acceptance

## IMPLEMENTATION

One new Python CLI, performance_benchmark_p2b.py, reuses:
- B0 inventory and literal-loopback URL parsing;
- P0 snapshot of reported Ollama version, loaded model residency and
  coarse system MemAvailable;
- P2A's reviewed distinction between client visible first-content time,
  final Ollama generation counters and resource policy permissions.

It sends at most one explicitly authorized local POST /api/chat with the
literal synthetic prompt "Reply with exactly the word READY.", stream=true,
think=false, num_ctx=2048, num_predict=32. It omits keep_alive, so it does
not force model unloading or residency changes beyond the normal model
load/cache caused by an inference request. It starts/stops no server.

The response is read incrementally, within a 120-second monotonic deadline,
45-second socket timeout, 512 frame, 64 KiB/line, 512 KiB total stream,
4 KiB transient output, fixed context and token caps. The program counts
bytes but discards contents and thinking. It rejects tool calls, thinking
content, model mismatches, malformed JSON, duplicate terminal packets,
invalid done reasons, incomplete/truncated streams and invalid counters.
There is no automatic retry, output printing, permanent log or session.

Results show request->headers, request->first nonempty assistant content,
request->valid terminal completion, and separately provider-reported
load/prompt-eval/generation durations in milliseconds. Ollama stream
packets are not tokens. Tokens/sec uses the terminal eval_count and
eval_duration only when both positive; missing cached-count remains null.
An error yields one fixed REFUSED JSON without prompt, response, model,
endpoint or external exception. An expected cold/warm residency mismatch
returns SKIPPED without POST; it is not a successful measurement. A nonnegative provider counter is a
server report, not a verified hardware timer.

## HOW TO USE // CURRENT: tests only, NOT a native benchmark request

Run safe disposable CI/local unit tests:

    python3 -m unittest discover -s tests/forest -p 'test_performance_benchmark_p2b.py' -v

**Do not yet execute the benchmark CLI on Fedora.** The runtime command
requires explicit approval, verified resource observations and selected
model. No selected model, host RAM requirement, free accelerator capacity,
or exact operator-approved trial has been established in this PR.

A future reviewed operator trial would supply one model name and scenario
(cold/warm), plus all independent capacity review fields and three explicit
operator acknowledgment flags. The flags are acknowledgments, NOT actual
trusted resource measurements or cryptographic authorization. Without all
flags, valid exact model, and numeric capacity facts, no HTTP request runs.
One CLI invocation attempts one request, not a batch of four. A separately
approved campaign can at most contain one cold and three sequential warm
calls; enforce that manually until a reviewed trusted campaign coordinator
exists. Do not use this runner for arbitrary user tasks or private data.

## Capacity caveats and source limitations

- HOST MemAvailable is a Linux host snapshot, not cgroup-limited RAM,
  task-reserved memory, swap headroom, or an atomic resource lease.
- The required-host and free-accelerator inputs are manually supplied
  reviewed facts, NOT automatically trusted measurements. If unknown,
  DO NOT supply guessed zeros; HOLD and decline native execution.
- GPU free-memory telemetry is not furnished by P0. Its size_vram is
  *resident used* memory, not free. The runner checks manually supplied
  available accelerator >= required accelerator, and observed RAM >=
  required host + a 512 MiB fixed buffer. These are only necessary
  conditions, not sufficient safety or any guarantee of VRAM.
- Cold requires the selected model ABSENT from /api/ps immediately before,
  warm requires it PRESENT; another resident model means refusal. The
  target must appear in read-only installed /api/tags.
- Even if no other model appears in /api/ps, another process might be
  starting an inference concurrently. The no-competing-inference flag is
  an operator statement, not a protected concurrency lock.
- The program inspects GPU/CPU residency only via Ollama's reported
  size_vram. It does not verify kernel GPU use or exact quantization.
  Different model contexts, acceleration, think behavior or server versions
  are separate experiments, not comparable samples.
- The code cannot autonomously detect every thermal throttle, competing
  process, memory pressure change or service restart. Stop immediately on
  such observations. Cancellation with Ctrl+C yields a fixed status.
- This is NOT a scheduler, a policy admission lease, a C5/Connections
  permit, a native writer, a signed disclosure grant or ForestW streaming.
  A P1 resource-fit APPROVE does not authorize execution.

## VERIFY // CI

CI uses a disposable local fake HTTP server (GET /api/tags, /api/version,
GET /api/ps, POST /api/chat); tests intentionally send synthetic fake
messages, not real Ollama inference. Negative tests cover no-approval,
capacity unknown, wrong model/mode, cold/warm mismatch, no competing
model proof, remote URL, wrong content type, incomplete stream, dual
terminal, invalid counters, privacy, zero throughput, tool/thinking
refusal, GPU/CPU mismatch and cancellation.

The dedicated workflow also runs P0, P1, B0, B2 and C5 provisional
disclosure security regressions. Only exact-head successful CI is
automated verification, not a measured Fedora performance result.

## NEXT / DECISIONS

1. Obtain independent Forest Nurse 2 source/CI review BEFORE merge.
2. Operator accepts scope and decides merge; no local runtime is changed.
3. Before any actual trial, separately verify model, model-specific
   host/accelerator requirements, actual free capacity, thermal desktop
   headroom, Ollama status and competing workload ownership.
4. Only after explicit separate operator authorization for exact model,
   limits and total calls may a trusted worker or operator run P2B on
   Fedora and report real cold/warm numbers. No model pull, unload,
   restart, forced eviction or auto retries are permitted.

Historical Bristlecone governor and L9/L10 benchmarks are recovered
architectural evidence, not modern Fedora/GPU speed proof. Forest remains
PRODUCTION HOLD. User final DONE is distinct from automated tests.
