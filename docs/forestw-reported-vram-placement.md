# ForestW // Reported model memory placement

**Patient:** The-Post-Apollo-Project · **Room:** ForestW independent diagnostics · **Role:** external ForestW UI DOC · **Production:** HOLD

## IMPLEMENTATION
The existing selected-model P2C CHECK now projects the ratio of Ollama-reported resident VRAM bytes to reported total resident bytes. Both values are from the same exact-model cross-checked response. Positive total and a non-null VRAM count within that total are necessary for a ratio. Zero and equal counters are preserved; near-boundary fractional labels are not rounded into exact zero or one hundred percent. Missing VRAM, zero total, or VRAM exceeding total yields unknown rather than a clamped number. Nonresident models have no share. The ratio disappears during a scan, expiry, or selected-name mismatch.

The diagnostic panel labels the ratio **reported VRAM share**, displays one proportion bar, and explicitly labels CPU/GPU execution share UNKNOWN. It is not a CPU utilization bar, host RAM allocation measurement, device mapping, GPU kernel execution evidence, or calibrated resource requirement. No extra request, background polling, runtime action or ForestW main layout change. The existing P0 LIVE source, manual P2C CHECK, Coffee Bar, equipment, AUTO preview and BENCH work remain independent.

## HOW TO USE
After review and merge: Forest → flower → select an equipped SMALL or BIG model → top-deck medical-staff Diagnostics → CHECK. Scroll to MODEL MEMORY // REPORTED VRAM SHARE. Only a current exact-model report with usable resident counters produces a bar. No selected model, AUTO unresolved, model not resident, stale or incomplete report: no percentage.

## VERIFY
Extend the existing ForestW hardware-capacity tests with real P2C producer output from the disposable fake HTTP fixture. Cover zero, partial, equal, null, inconsistent and extreme fractions; absent model and no selected model; exact-name and process-completion barriers; no POST. Native rendering and actual device evidence remain separate.

## NEXT / DECISIONS
Verified model execution requires Forest Core's evidence contract, not arithmetic on residency. Ask the owning backend lane to establish reviewed process/device attribution and workload-scoped GPU evidence, and later model-specific calibrated requirements under separately approved trials. Preserve current inference and benchmark HOLD. Do not use DRM aggregate counters, estimated headroom or resident bytes as proof of actual GPU execution or safe capacity.