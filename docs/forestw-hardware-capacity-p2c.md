# 🏥💜 ForestW // P2C read-only hardware capacity page

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** ForestW model popup / hardware diagnostics  
**STAFF ROLE:** ForestW DOC successor, external Hospital-compatible; no live Hospital registration verified  
**STATE:** source only; production READ / CHAT / VOICE / inference HOLD

## IMPLEMENTATION

ForestW's existing flower-shaped model popup now provides a **HARDWARE** navigation control alongside the existing **SCAN ALL** model inventory button. **MODELS** returns to the original selector without destroying the per-Tree choice. The hardware view stays *inside the same popup*, with its own scrollable content for compact chassis sizes. Closing the popup returns navigation to MODELS.

The new `widgets/ForestHardwareCapacityView.qml` uses **one** `services/forest/ForestCapacityAdapter.qml`. The operator must press **CHECK** before it starts the already-existing `scripts/forest/performance_capacity_p2c.py inspect` command. No timers, startup probe, implicit per-Tree request, model argument, new endpoint, benchmark, or runtime change.

P2C is a separate **diagnostic** from P0. It already collects fixed local Ollama GET `/api/tags`, `/api/version`, `/api/ps`, and fixed Linux `/proc/meminfo` and DRM sysfs counters. The hardware page renders strictly sanitized:

- Linux host `MemAvailable` in MiB (not cgroup-limited or reserved memory).
- Visible CPU thread count and process CPU affinity count (not free dedicated cores).
- One row per DRM card `card0`–`card7`: kernel-reported VRAM total, used and estimated difference, each in MiB; missing values display `?` and are **not** guessed.
- `GPU COUNTERS UNKNOWN` when the fixed Linux sysfs paths provide no card counters, not `NO GPU`.

The pure `ForestCapacityPolicy.js` validates P2C's schema, false permission/benchmark/production flags, numeric bounds, distinct GPU card IDs, nullable fields, and consistency of reported headroom. A scan publishes only after complete stdout + stderr + normal process exit. Failures clear all values.

**Important source separation:** The existing top-right LOAD/IDLE and model-popup LIVE statuses still read the **same single P0 `ForestResidencyAdapter`**, unchanged. P2C's hardware read is only operator-triggered from the separate HARDWARE page and **does not become another live-model state source**. Both existing P0 and P2C use the pinned **same local Ollama provider**, but P2C also reads separate Linux DRM counters necessary for diagnostics.

## HOW TO USE

After independent review, user/operator merge and deployment:

1. Open Forest and the flower model selector.
2. Select **HARDWARE** at the top of the existing popup.
3. Press **CHECK** to request one read-only snapshot; inspect memory, CPU and GPU counter estimates.
4. Select **MODELS** to return to the existing model selector and selected-model profile.

The page is read-only. A CHECK cannot pull/load/unload models, send inference or authorize a session. No automatic refresh occurs and results are the **last manually requested** snapshot.

## VERIFY

```bash
python3 tests/forest/test_forest_launcher_contract.py
python3 tests/forest/test_forest_model_residency_ui.py
python3 tests/forest/test_forest_model_profile_p0.py
python3 tests/forest/test_forest_hardware_capacity_view_p2c.py
```

The new Python/Node matrix uses fake P2C observations and verifies negative and nullable counter cases, exact card fields, false permission/benchmark bits, no untrusted model argument, barrier ordering, failed probes and unchanged P0 header source. GitHub CI does not run P2C against a real Ollama or inspect physical GPUs.

## WATCH OUT FOR

- **VRAM HEADROOM EST is not safely allocatable memory** and not a reservation. Sysfs card IDs are not independently mapped to the GPU used by Ollama. A host counter can be stale, missing or belong to a different GPU.
- P2C does not know the selected model's calibrated RAM/VRAM requirements, actual GPU placement, effective container memory, thermal headroom, or competing processes. The page never declares FIT, SAFE or PERMITTED.
- Missing GPU counters mean UNKNOWN, not absence of a GPU. `MemAvailable` is host-wide, not a per-task budget.
- The UI is source-only until operator-controlled merge and native Quickshell testing. Exact-head source CI does **not** establish visual geometry on Fedora.
- C5, Forest Core and installed host own all generation/session/title access. SEND and voice remain hard-locked.

## CHECKLIST / NEXT

- [x] Keep existing model selector, P0 LOAD/IDLE source and per-Tree selection intact.
- [x] Add one in-popup HARDWARE page with explicit P2C CHECK.
- [x] Reject malformed P2C snapshots and enforce no authority/benchmark semantics.
- [x] Add source/UI regression tests and CI.
- [ ] Verify exact-head GitHub workflows.
- [ ] Independent Forest Nurse 2 source/CI review before merge.
- [ ] User/operator merge and native Quickshell visual acceptance.
- [ ] Any actual Fedora GPU inference benchmark requires **separate** authorization and verified capacity/owner controls.

## DECISIONS

This is a UI diagnostics milestone only; not a protected model runtime, GPU capacity governor or production chat integration. No local computer edits, package changes, Quickshell restarts, model runs, Host or Connections code changes, and no authority transfer.
