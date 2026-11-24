# 🏥💜 ForestW // P2C same-snapshot model evidence cross-check

**PATIENT:** The-Post-Apollo-Project  
**ROOM / ASSIGNMENT:** ForestW UI successor · exact selected-model P2C preflight integrity  
**STAFF / PROVIDER:** External Hospital-compatible ForestW DOC · OPEN AI / CHATGPT  
**PRODUCTION:** CHAT / SEND / VOICE / MODEL EXECUTION HOLD  
**STATE:** Source proposal; independent Nurse 2 review and operator acceptance pending

## IMPLEMENTATION

The prior ForestW P2C selected-model preflight (merged PR #2389) trusted its bounded P2C `selected_model` summary once the selected model name and numeric types matched. P2C returns the `installed_models` inventory and `resident_models` observations in the **same response**, so ForestW can also test whether that summary is internally consistent.

`services/forest/ForestCapacityPolicy.js` now validates each returned installed `name/size_bytes` and resident `model/size_bytes_reported/vram_bytes_reported/context_length_reported` for acceptable names, bounded safe integers or documented nullable values, and unique model names. For the exact selected Tree model, `selected_model.installed`, `resident`, installed artifact bytes, resident memory bytes and nullable VRAM bytes must agree with the corresponding entries in those two arrays. Any mismatch rejects the **whole P2C observation** and clears projected data. A read-only generic P2C CHECK without a selected model retains `selected_model=null` and still validates lists.

The existing hardware UI shows `P2C TAGS/PS CROSS-CHECK // MATCH (ONE RESPONSE)` only for a successful, matching selected-model check. A missing, rejected or stale report shows `P2C MODEL EVIDENCE // UNCHECKED OR REFUSED`; no implicit scan, retry, token generation or model-load action occurs.

**Same-source invariants:** This reconciliation uses data already returned by the **single explicit P2C CHECK**. It does not call another Ollama source. The top-right LOAD/IDLE and the model popup LIVE rows still consume one shared **P0 residency adapter** and are not affected by this check.

## HOW TO USE

After review and merge, in Forest: select Tree → flower popup → MODELS → choose model with USE → HARDWARE → CHECK. If the returned P2C selected-model evidence agrees with the installed/resident lists **inside the same P2C response**, the cross-check label says MATCH. Host RAM/CPU/GPU diagnostic estimates remain on the page.

If observations disagree, no model data is projected; use a subsequent explicit CHECK to obtain a new observation. Switching Tree/model continues to hide results of the old selection.

## VERIFY

```bash
python3 tests/forest/test_forest_launcher_contract.py
python3 tests/forest/test_forest_hardware_capacity_view_p2c.py
python3 tests/forest/test_forest_selected_model_preflight_p2c.py
python3 tests/forest/test_forest_p2c_model_evidence_crosscheck.py
```

Dedicated Node/Python adversarial tests use fake P2C JSON and cover contradictory Boolean flags, mismatched numeric fields, null VRAM discrepancy, duplicate and malformed installed/resident names, illegal/unsafe counters, generic no-model check, resident-only mid-observation state, all-absent state and unchanged permission flags. Native Ollama/GPU are not queried in CI. Existing process callback order regressions remain active.

## WATCH OUT FOR

- **Internal consistency is not original-host authentication.** P2C tags and residency come from separate GETs at the same pinned local Ollama provider, so they are not a fully atomic hardware-state snapshot. The P2C selected summary is derived from these arrays; cross-check only detects malformed or contradictory payloads, not independent tampering of all fields.
- Cross-check MATCH does **not** establish active inference, resource sufficiency, exact GPU mapping, model RAM/VRAM requirements, a safely allocatable reservation, C5 consent, title disclosure or any benchmark permission.
- Values that exceed JavaScript's safe integer precision are now rejected rather than displayed as rounded measurements.
- ForestW SEND/voice remain fail-closed. No extra provider, timer, socket, model load, benchmark, local workstation write, or production authority.

## CHECKLIST / NEXT

- [x] Preserve single P2C CHECK and single P0 model-live adapter.
- [x] Add strict same-response selected-model evidence reconciliation.
- [x] Deny inconsistent or unsafe counters.
- [x] Add visible explanatory state and adversarial tests.
- [ ] Exact-head CI and Forest Nurse 2 independent review.
- [ ] Operator merge and native visual acceptance.

## DECISIONS

No real benchmark or model activation is requested in this milestone. This is ForestW-only read-only presentation hardening; Forest Core/Connections retain the host, security, C5 and execution lanes. Merged PR #2389 and #2386 still require independent scoped review history to be reconciled separately. User final DONE is not inferred.
