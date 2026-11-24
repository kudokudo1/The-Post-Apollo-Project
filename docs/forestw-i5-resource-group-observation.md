# ForestW // I5 resource group observation

**Patient:** The-Post-Apollo-Project · **Room:** ForestW UI · **Role:** external ForestW DOC · **Production:** HOLD

## IMPLEMENTATION
Diagnostics gains a collapsible RESOURCE GROUP // I5 panel. Explicitly enter an existing authorized non-root cgroup hierarchy path and press CHECK GROUP. One direct invocation of the existing Core cgroup_observation_i5.py observe CLI takes five samples at 250 ms intervals. No discovery, shell expansion, polling, service change, sudo, model operation, or added backend accounting policy. The UI shows first/last charged memory, sampled maximum/increase, kernel peak separately, swap, overlapping anon/file/shmem counters, local limit, CPU-time delta, tasks and elapsed duration. Strict bounded receipt, all nonauthority fields false, optional unknown preserved; unsafe integer precision refuses. Complete successful stdout/stderr/exit required. Close/collapse/input change clears reports and discards pending results. The path is only local in-memory input, not a persisted preference.

## HOW TO USE
After review and merge, open Forest → Diagnostics → RESOURCE GROUP // I5. Enter the existing authorized group path (not /sys/fs/cgroup itself, and never root /). To identify an already running system Ollama service group if applicable, the existing Core instructions use `systemctl show ollama.service --property=ControlGroup --value`. An empty result means no known group; do not guess or start a service. Paste the verified non-root path, press CHECK GROUP. No permission escalation. Only inspect workloads you are authorized to inspect.

## VERIFY
python3 -B tests/forest/test_forest_group_observation_i5.py exercises actual I5 observer against disposable changing counter files, strict JS receipt validation, missing/invalid counters, group path validation and manual-only UI scope. Existing Core CI native kernel observations are separate from operator native acceptance. No workstation sampling performed during development.

## WATCH OUT FOR
Group counters include descendants and potentially unrelated workloads; no exact model allocation, membership, unique physical memory, effective ancestor limit, free capacity, complete workload peak or required resources. A sampled maximum is not a guaranteed peak, and kernel memory.peak has distinct semantics. Do not sum overlapping memory.stat categories. The group path is not authenticated runtime identity. I5 independent Core review was outstanding at reconciliation. Native QML and command acceptance pending. Separate-service attribution and I6 membership remain separate.

## NEXT / DECISIONS
Independent Forest Nurse 2 review and operator test. Integrate I6 counts-only membership separately only after its reviewed contract and explicit known same-owner PID selection; do not join unrelated observation snapshots or infer Ollama model identity. Maintain production HOLD.