# 🏥💜 ForestW // One shared model-residency indication

**Patient:** The-Post-Apollo-Project  
**Room:** ForestW UI successor, model popup and top-right status  
**Staff:** external Hospital-compatible DOC; Hospital registration unverified  
**State:** Source-only, production chat/voice/inference HOLD

## IMPLEMENTATION
The top-right `liveIndicator` previously displayed a hardcoded green `LIVE` for the **Quickshell workspace**. The popup's `LIVE ?` rows were unconnected placeholders. Neither reported a model state.

The existing B0 model discovery still uses **Ollama at literal loopback** via `ollama_inventory.py list-models` (GET `/api/tags`). To know whether a model is loaded, that inventory is insufficient. Reuse the existing Forest Core P0 **read-only** `performance_snapshot_p0.py snapshot` on that exact same Ollama provider; P0 reads GET `/api/version` and GET `/api/ps`, and also returns diagnostics that ForestW intentionally ignores.

A single UI-owned `ForestResidencyAdapter` runs P0 **only** when the operator explicitly opens the model popup, presses SCAN ALL / a row SCAN, or presses the existing top Reload button. A strict JS policy waits for stdout + stderr + normal exit and publishes only P0-validated resident model names. It refuses bad responses and never carries previous names into a new scan.

**The popup and the header consume the exact same observer object.** There is no separate header probe, fallback provider, polling timer, cached credentials, new API endpoint, or Ollama POST.

### Status meaning
- Header for currently selected Tree model: green dot **LOAD** when exact model is in latest Ollama `/api/ps`; orange dot **IDLE** when successfully observed but absent; cyan dot **?** if not selected or no valid observation.
- Popup for every inventoried model: **LOADED / IDLE / LIVE ?** according to the same latest snapshot and exact model name.
- `FOUND` continues to mean installed in B0 `/api/tags`. `ACCESS ?` remains unverified: residency cannot confer C5 permission.
- The header's **old LIVE meaning (workspace is open)** is replaced by **selected-model residency**; it must not be construed as token generation, connection liveness or benchmarking.

## HOW TO USE
After operator-reviewed merge and deployment: Forest → choose a Tree → choose an installed model via flower popup `USE` → `SCAN ALL` or top-right Reload. The top-right model badge and the selected row then report the **same last-scanned** P0 observation. Changing Trees reuses the last observation, does not silently start a new network probe.

## VERIFY
`python3 tests/forest/test_forest_launcher_contract.py` and
`python3 tests/forest/test_forest_model_residency_ui.py`, plus inherited ForestW session tests. Node-backed negative tests simulate Ollama replies and all process callback orders. CI does **not** query live Ollama or run a model.

## WATCH OUT FOR
- `/api/ps` reports **loaded residency**, not whether token generation is active. Residency can change after refresh. Not-loaded does not mean an installed model could not be loaded later.
- Two read-only GET helpers target the **same pinned Ollama origin**, but different endpoints because `/api/tags` cannot report loaded models. The header and popup never read different adapters for residency.
- Unknown/error must display `?`, not a green live claim. P0 provider data is not protected host attestation, GPU placement evidence, permission, token throughput or memory safety proof.
- No private sessions, new process listener, model benchmark, Ollama pull/start/unload, or local machine mutation.

## NEXT / DECISIONS
Forest Nurse 2 exact-head independent review; then operator merge and native Quickshell visual acceptance. Actual C5 `LIST_SESSIONS`, generation, voice and streaming remain separate HOLD.