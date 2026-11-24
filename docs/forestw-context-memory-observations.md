# ForestW // Context and resident memory observations

**Patient:** The-Post-Apollo-Project · **Room:** ForestW Diagnostics · **Role:** ForestW UI DOC · **Production:** HOLD

## IMPLEMENTATION
Extend the existing exact-model P2C projection to retain validated context length, resident bytes and VRAM bytes from the same response. Distinct successful checks have a local sequence number. HOLD A/B explicitly copies the current matching resident observation, model, Ollama version, sequence and local completion time. Samples are historical in-memory observations, not refreshed capacity. CLEAR removes both; a change in selected exact model clears them. Capture is unavailable during a check or without a current matching resident observation. Missing context/VRAM remains unknown. Comparison distinguishes repeated capture of one check, same reported context, different context, and different model/version; no claim of equivalent workloads.

## HOW TO USE
Open Forest → flower → select equipped SMALL or BIG model → Diagnostics → CHECK. If the model is already resident, HOLD A records the observation. At a later independently authorized observation, CHECK and HOLD B. No button changes the context, runs a model, or produces a benchmark.

## VERIFY
The existing hardware suite uses the actual P2C producer against disposable loopback fixtures for different context lengths, unknown counters, absent residency, same-check capture, changed version, model mismatch and stale state. No real inference or POST. Native layout acceptance remains separate.

## WATCH OUT FOR
Reported context length is not actual consumed tokens. Resident bytes are not peak memory, minimum requirement, available capacity, calibrated KV-cache growth, or verified GPU execution. Do not infer CPU allocation by subtraction. Same model name/version does not prove identical quantization, hardware or settings. Held samples are deliberately not current and are not persisted. The existing resource governor P1 remains synthetic-only.

## NEXT
Forest Core owns workload-scoped calibration and trusted model/runtime identity, peak requirements, context/reasoning/placement parameters, measurement provenance and budget/availability contracts. Separate explicit approval and capacity review before native trials. UI will consume a reviewed bounded projection; no competing governor or automatic inference.