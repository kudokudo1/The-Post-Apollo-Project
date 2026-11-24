# 🏥💜 ForestW // Local observation freshness

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** ForestW UI successor / model and hardware observation  
**STAFF:** ForestW DOC · External Hospital-compatible browser ChatGPT  
**PRODUCTION:** SEND / voice / inference / private sessions HOLD  
**PHASE:** source-only implementation; independent review pending

## IMPLEMENTATION

ForestW previously displayed a P0 `LOAD` or `IDLE` status and a P2C hardware snapshot indefinitely after successful manual observations. This was a stale-data risk, especially for a model that Ollama could unload or whose GPU memory consumption could change without a ForestW refresh.

`ForestResidencyAdapter.qml` and `ForestCapacityAdapter.qml` each now stamp **local UI completion time** in `HH:mm:ss` only after its own strict source/stdio/exit validator reports `OBSERVED`. Both have a **single nonrepeating five-minute timer** started after successful completion. The timer only expires cached display evidence. It never calls Ollama, P0, P2C, a model, a private host or another service.

- **P0 expiry:** status becomes `STALE`, reason becomes `SNAPSHOT_EXPIRED`, `models` and `records` clear. The original `ForestResidencyPolicy.modelState` already projects any non-`OBSERVED` status as `UNKNOWN`, so the header's former green LOAD/orange IDLE becomes cyan `?` on expiration. The MODELS popup receives the **same** P0 object, never a second probe.
- **P2C expiry:** status becomes `STALE` and the hardware observation values clear. Any `currentModelObservation` is false; an old selected-model report cannot reappear as current. The hardware view still retains the displayed last local completion time so users know when their data expired.
- **Manual rescan:** opening the model popup or pressing SCAN ALL / top Reload still explicitly requests B0 + P0, exactly as before. Pressing HARDWARE CHECK still explicitly requests one P2C snapshot. Any new request stops its previous expiry timer, clears its old time/results and starts a fresh five-minute window only after validated normal completion. Failed attempts do not stamp success.
- **Display:** MODELS provider row shows `P0 CHECKED HH:mm:ss` or `P0 STALE // SCAN AGAIN`; HARDWARE shows `P2C CHECKED HH:mm:ss` or `P2C STALE // CHECK AGAIN`. The top-right model badge's accessible text includes P0 status/time. No resizing of the 60px badge or popup window required.

These times come from the UI's **local clock at successful process completion**, not from Ollama or trusted signed provider evidence. They are not guaranteed synchronized clocks, atomic snapshot times, token-generation proof or C5 permissions. The five-minute window is a *display expiry policy*, not certified accuracy while the timer is active.

## HOW TO USE

After independent review, merge and operator deployment: Forest → choose Tree → MODELS → USE. The header LOAD/IDLE and popup show P0's last-check time, then degrade to unknown after five minutes without refresh. Press the top Reload or SCAN ALL to explicitly update. For host/GPU figures select HARDWARE → CHECK; after five minutes the values clear until another CHECK.

No automatic network polling, model load, benchmark or chat access is activated.

## VERIFY

```bash
python3 tests/forest/test_forest_launcher_contract.py
python3 tests/forest/test_forest_model_residency_ui.py
python3 tests/forest/test_forest_hardware_capacity_view_p2c.py
python3 tests/forest/test_forest_selected_model_preflight_p2c.py
python3 tests/forest/test_forest_p2c_model_evidence_crosscheck.py
python3 tests/forest/test_forest_observation_freshness.py
```

ForestW CI covers the old source checks and new structural one-shot timer / presentation source tests and a pure JS P0 expired-state test. **Native runtime QML Timer behavior and actual wall-clock readings require a separate Fedora visual acceptance**. No CI benchmark, real Ollama observation or GPU actuation is claimed.

## WATCH OUT FOR

- The timer expiry is **not polling**. `repeat: false`; there are no GETs or additional process invocations in timer callbacks. It merely clears values.
- The displayed time is from a local UI clock. Clock changes or a suspended Quickshell can make a timestamp misleading; an expired timer gives a conservative unknown state when processing resumes.
- Five minutes is a UI expiration interval, **not a guarantee** that GPU/memory/model status remains valid for five minutes.
- B0 discovery inventory and selected Tree preference remain separately managed, but neither is converted into model execution authority.
- P2C remains separate from P0; the top-right badge and MODELS popup use only the **same shared P0 adapter**.
- Independent Forest Nurse 2 review of previous merged PRs #2386, #2389 and #2393 is still unresolved if not separately recorded; successful source CI does not retroactively certify independent review.

## CHECKLIST / NEXT

- [x] Read Syntagma agent and Hospital protocol; verify merged #2393 and current main.
- [x] Add successful-observation timestamps to existing adapters.
- [x] Add one-shot five-minute display expiry; clear old P0/P2C evidence.
- [x] Show local check/stale indicators without changing source authority or geometry.
- [x] Update inherited no-polling guards and add focused source tests.
- [ ] Exact-head GitHub CI and independent Forest Nurse 2 review.
- [ ] Operator merge, actual Quickshell timer and layout acceptance.

## DECISIONS

The ForestW UI lane is still read-only observation and presentation. No model inference, hardware benchmark, permissions, CPU/GPU policy, local host mutation, independent LIVE data provider or C5/Forest Core implementation. Final DONE remains operator-controlled.
