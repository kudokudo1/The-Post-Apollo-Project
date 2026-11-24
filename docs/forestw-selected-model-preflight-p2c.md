# 🏥💜 ForestW // Selected-model P2C preflight (read-only)

**PATIENT:** The-Post-Apollo-Project  
**ROOM:** ForestW model popup → HARDWARE  
**STAFF ROLE:** ForestW DOC successor, external Hospital-compatible; live Hospital registration unverified  
**PHASE:** Source implementation; production generation/session/voice/benchmark HOLD

## IMPLEMENTATION

The existing ForestW P2C HARDWARE CHECK previously issued `performance_capacity_p2c.py inspect` without the selected model. P2C **already** supports a read-only exact `--model` filter that reports whether the named model was installed and resident at scan time, plus its reported installed artifact size and resident model memory/VRAM. This milestone wires **the exact selected Tree model** to that existing filter, and adds a small MODEL PREFLIGHT section above the existing host/GPU figures.

The operator presses CHECK to request the same P2C snapshot. The adapter validates the argument before launching and passes `["--model", wanted]` as explicit argv only for a valid, nonempty model name. Otherwise it obtains the same generic hardware snapshot as before, with no claimed model check. The P2C backend remains unchanged.

The pure P2C UI policy correlates **the actual model requested** with `selected_model.model` returned by P2C. Mismatched, malformed, fractional, negative or unreasonably large numeric values fail the whole observation. `runtime_requirement_calibrated` must be `false`; forged permission and benchmark fields remain forbidden. A full stdout + stderr + successful process exit is required before results appear. Unknown values display `?`, never zero or an estimated model requirement.

**Stale-result separation:** The UI exposes a model-specific result only when the currently selected model **exactly matches** the name captured at CHECK time and the P2C report completed successfully. If a Tree or selected model changes during the read, the old model report cannot appear as a new model's evidence. The UI does not poll or automatically start another read. The host-wide RAM/CPU/DRM values remain diagnostic hints independent of Tree.

**Single-source model LIVE continuity:** The top-right LOAD / IDLE badge and the MODELS popup still consume exactly one shared P0 `ForestResidencyAdapter`. P2C's result **does not** set or override either source, even if observation timing differs. Both diagnostics target the same pinned Ollama service, but P0 and P2C are different explicit, last-scanned observation purposes.

## HOW TO USE

After independent review, operator merge and native deployment:

1. Forest → select Tree → flower-shaped model popup → **MODELS** → choose a model with **USE**.
2. Switch to **HARDWARE** and press **CHECK**.
3. The new **MODEL PREFLIGHT** row displays the exact model name and P2C-reported `INSTALLED` / `RESIDENT` status, plus `ARTIFACT`, `RES MEM` and `VRAM REP` (MiB) where available.
4. Host memory, CPU and DRM GPU counters remain below the model row. Changing the selected Tree/model invalidates the displayed model-match comparison until another explicit check for that model.

No active execution, benchmark, private-session read, or chat SEND is triggered.

## VERIFY

```bash
python3 tests/forest/test_forest_launcher_contract.py
python3 tests/forest/test_forest_hardware_capacity_view_p2c.py
python3 tests/forest/test_forest_selected_model_preflight_p2c.py
```

New tests use synthetic P2C JSON only, covering strict argument validation, no command execution on invalid model, mismatched host result, nullable model fields, calibrated-requirement false, stale UI comparison, exact P0 source preservation, and all stdout/stderr/exit callback orderings. CI does **not** invoke native Ollama, GPU or benchmark commands.

## WATCH OUT FOR

- **Installed artifact size is not model RAM/VRAM requirement.** Resident memory and resident VRAM are snapshots, not future allocations, safely free VRAM or a calibrated resource budget.
- A `RESIDENT YES` result means P2C observed a loaded model, **not that it is generating tokens or installed on the intended Radeon GPU**. Backend observations may differ over time.
- Host `MemAvailable`, CPU affinity, and sysfs headroom are **not** cgroup-effective reservations. No owner-approved concurrency, thermal budget, consent, selected-model requirement or installed trusted C5 host has been established here.
- `HARDWARE CHECK` remains explicitly operator-triggered and read-only. No deployment, local system mutation, actual model run, timer, model pull, or automatic retry.
- Private session LIST, title disclosure, SEND and voice remain separate from resource observation.

## CHECKLIST / NEXT

- [x] Preserve existing P2C generic system snapshot with no selected model.
- [x] Add exact read-only `--model` filter with argument and response correlation.
- [x] Hide stale or mismatched model results after Tree/model changes.
- [x] Update UI, adversarial tests and ForestW source CI.
- [ ] Exact-head workflows / independent Forest Nurse 2 review.
- [ ] User/operator merge; native Quickshell visual acceptance.
- [ ] **Separate explicit operator authorization** needed before any actual P2B inference/benchmark run.

## DECISIONS

This milestone is **preflight observation only**. ForestW does not gain authority to launch models or evaluate readiness. No change to Forest Core P2B/P2C backend, DOC 1–3/Connections ownership, Ollama configuration, host service or live Hospital records. A successful GitHub test is not a verified native GPU benchmark, and operator final acceptance remains separate.
