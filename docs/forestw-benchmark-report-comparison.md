# ForestW // Benchmark report comparison

**Patient:** The-Post-Apollo-Project · **Room:** ForestW UI · **Role:** external ForestW DOC · **Production:** HOLD

## IMPLEMENTATION
The flower MODELS popup gains a small BENCH button beside AUTO PREVIEW. The new page accepts two manually pasted, complete P2B JSON reports (A and B), displays the exact model, cold/warm scenario, Ollama version, first visible content, provider generation rate, client completion, headers, load/prompt/eval/total timing, and token counts. Null metrics display unknown. The parser follows the current P2B metadata schema, checks bounded numeric values, exact field names and nonauthority flags, and refuses incomplete or malformed reports. A rejected import clears its target slot. The report view is in-memory only; closing it clears both reports and the input. No changes to equipment, Coffee Bar, persistence, diagnostics, shared components or runtime selection.

## HOW TO USE
After review and merge: Forest → flower → BENCH. Paste one complete P2B result and press IMPORT A. Paste another and press IMPORT B. CLEAR removes both; MODELS returns to inventory. AUTO PREVIEW and BENCH are mutually exclusive. If no approved benchmark receipt exists, expect NO REPORTS. The test suite supplies disposable fake-loopback receipts, not actual model measurements.

## VERIFY
Run python3 -B tests/forest/test_forest_benchmark_report_view.py from the checkout. Reuses existing backend fake-loopback fixture to produce actual P2B-format warm and cold results, then tests UI parser interoperability and negative cases. No real Ollama request. Native scroll, paste, sizing and close/reset acceptance remain separate.

## WATCH OUT FOR
The P2B report is metadata only, not a signed measurement. Paste provenance is unverified. Same scenario/version does not prove equivalent hardware, runtime acceleration, workload or model settings. The fixed task uses context 2048, output cap 32, thinking disabled and one request. Different model responses need not have equal token counts; provider rate is not a task-wide speed/quality score. First visible content is not a verified first-token boundary. No inference, intelligence score, automatic winner, resource-fit decision or permission is inferred.

## NEXT / DECISIONS
Forest Core owns benchmark execution, measurement provenance and any future campaign coordinator. Before a real trial, obtain separate explicit operator approval for exact model and scenario, independent capacity evidence, resource/competing workload review and appropriate security boundaries per PERFORMANCE_BENCHMARK_P2B.md. Do not launch the CLI from ForestW. Future trusted results and hardware mapping will be consumed only after owner-reviewed contracts. Production SEND/voice/private reads remain HOLD.