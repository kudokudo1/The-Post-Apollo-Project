# Heart H6 // Context footprint scenario
DEVELOPMENT ACTIVE / PRODUCTION HOLD.

## IMPLEMENTATION
Offline bounded stdin JSON parser; no network, model load, writes, telemetry
or runtime authority. Accept Ollama show model_info for Granite or Qwen3
scalar uniform attention only. A hypothetical single-sequence dense FP16
key/value payload is layers × KV heads × (key width + value width) × 2
bytes × context tokens. GGUF explicit head widths take precedence; if absent,
use divisible embedding/head count as a labeled assumption. Missing KV
head count is not guessed. Special layout indicators refuse. Metadata
does not prove that all attention layers are dense or actual cache format.

## HOW TO USE
After independent review and normal merge, from repository root, supply
the existing local Ollama metadata endpoint response through stdin:
    curl --fail --silent --show-error --max-time 10 --noproxy '*' \
      -H 'Content-Type: application/json' \
      --data '{"model":"granite3.3:2b","verbose":false}' \
      http://127.0.0.1:11434/api/show | \
      python3 -B scripts/forest/heart_context_footprint_h6.py

/api/show is a metadata request, not /api/chat or /api/generate. The
estimator itself makes no request. Use shell pipefail when scripting.
Repeat explicitly for qwen3:1.7b. No raw template or unrelated fields
in output. Source provenance is not authenticated. 2 MiB input cap;
if model metadata exceeds it, refuse, do not truncate.

## VERIFY
    python3 -B -m unittest discover -s tests/forest -p 'test_heart_context_footprint_h6.py' -v

## WATCH OUT FOR
Payload excludes model weights, scratch/compute buffers, allocator padding,
runtime state and multiple sequences. FP16 is a scenario, not a measured
cache format. Quantized weights do not prove quantized KV cache. Actual
placement across RAM/VRAM, context allocation, concurrency, cache padding,
attention layout and runtime implementation remain unknown. Do not
add these scenarios to model file size and call the result a safe budget.
No direct P1/H1 admission or inferred resource requirement.

GGUF dimension definitions: https://github.com/ggml-org/ggml/blob/master/docs/gguf.md
Ollama head-width defaults: https://github.com/ollama/ollama/blob/main/fs/ggml/ggml.go

## NEXT / DECISIONS
Compare 512/1024/2048/4096/8192 context scenarios within model's reported
maximum. Granite/Qwen3 initial scope only. No automatic downgrade or
silent context truncation. Actual model demand remains pending approved
native trial and CPU++ memory headroom. Nurse2F review requested.
