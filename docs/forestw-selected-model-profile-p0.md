# 🏥💜 ForestW // Selected-model P0 profile strip

**Patient:** The-Post-Apollo-Project  
**Room:** ForestW model popup  
**Staff:** ForestW DOC successor, external Hospital-compatible; live registration unverified  
**Production inference, private sessions, SEND and voice:** HOLD

## IMPLEMENTATION

The existing P0 read-only snapshot from `scripts/forest/performance_snapshot_p0.py` already includes a model's `size_bytes_reported`, `vram_bytes_reported` (nullable) and `context_length_reported` (nullable) for Ollama-resident models. Previously `ForestResidencyPolicy.js` published model names only.

This source-only UI milestone preserves those **already received** fields after strict bounded numeric validation and successful stdout/stderr/exit processing. The existing `ForestResidencyAdapter` now provides `records` alongside the same snapshot's model names. `ForestW` resolves `selectedModelProfile` for the exact model chosen in the current Tree.

On a popup at least 270px tall, a compact 48px profile strip appears under `OLLAMA // DISCOVERED`, above the scrollable model list:

- `PROFILE // <selected model>` (or a neutral no-selection label).
- `SIZE <MiB> / VRAM REP <MiB> / CTX <tokens>` from the existing P0 loaded-model record. Unknown nullable fields display `?`, not zero.
- Selected model not resident: `NOT LOADED // NO RESIDENT METRICS`.
- No valid observation/selected model: `P0 STATUS UNKNOWN // SCAN TO UPDATE`.

Popup heights under 270px omit the strip to preserve useful model-list space. The same P0 observation still drives the top-right `LOAD/IDLE/?` indicator and model row `LOADED/IDLE/LIVE ?`. **No new endpoint, adapter instance, scan trigger, process, permission or model action.**

## HOW TO USE

After review, merge and operator-controlled deployment: Forest → choose Tree → flower model selector → choose a model with USE → SCAN ALL or header Reload. The profile displays the latest explicit read-only Ollama P0 response. Changing Tree simply selects the matching entry from the last snapshot.

## VERIFY

```bash
python3 tests/forest/test_forest_launcher_contract.py
python3 tests/forest/test_forest_model_residency_ui.py
python3 tests/forest/test_forest_model_profile_p0.py
```

Dedicated tests use synthetic P0 JSON and Node.js. Negative checks cover malformed/negative/fractional/unsafe-sized counters, nullable VRAM/context, complete process-exit barrier and no stale records on failure. Native QML appearance is separate from source CI.

## WATCH OUT FOR

- `SIZE` is Ollama-reported *resident model size*, not proof of actual RAM consumption or an installed artifact size.
- `VRAM REP` is Ollama-reported resident VRAM bytes. It is **not free GPU memory**, exact kernel GPU allocation, proof that the selected model is using the intended Radeon card, or confirmed acceleration.
- `CTX` is Ollama-reported loaded model context length, not an effective Forest session capacity guarantee.
- A successful P0 GET is a **last-scan observation**; no automated monitoring or native inference benchmark was performed.
- This is not `ACCESS` authorization. C5 protected issuer, private session disclosure, live SEND/voice and real benchmark execution remain HOLD.

## CHECKLIST / NEXT

- [x] Reuse exact P0 shared snapshot for selected-model metadata.
- [x] Fail closed on bad measurements and failed process exits.
- [x] Preserve compact popup scroll space.
- [ ] Verify exact-head GitHub CI and independent Forest Nurse 2 review.
- [ ] Operator merge and native Quickshell visual acceptance.
- [ ] Forest Core / Connections separately deliver protected session-list provider and C5 trust.

## DECISIONS

ForestW owns presentation only. No changes to Forest Core P0/B2/B3/B4, Connections, hardware configuration, Ollama runtime or workstation. Source completion does not imply operator final acceptance or production chat permission.
