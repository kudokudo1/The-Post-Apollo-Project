# CPU++ KILL // K8c on-demand resource capability inventory

**Scope:** read-only probe and documentation. No UI mount, no collector timer, no actuator, no privilege request or host modification. The operator authorized K8c after K8b6. Patient: `kudokudo1/The-Post-Apollo-Project`. Development ACTIVE; native/protected/production HOLD.

## Mechanism

An explicitly invoked Python helper reads the selected process's `/proc/<pid>/stat` birth identity before and after inspection. It reads bounded process and cgroup files, and uses only read forms of `getpriority`, `sched_getaffinity`, and `resource.prlimit`. It never writes any resource limit, signal, cgroup setting or GPU/network configuration. A missing or stale identity refuses the result; no cached PID-only capability is published.

Output schema: `post-apollo-kill-capability-k8c-v1`. All mutation/permission fields are **not_verified** regardless of read success. The checked file being present proves observability only, not delegation, permission, suitability or an implemented control.

| Resource | Existing source and read evidence | Potential kernel control, **not implemented in K8c** | Caveat |
|---|---|---|---|
| CPU | `/proc/PID/stat`, `getpriority`, `sched_getaffinity`; cgroup v2 `cpu.max`, `cpu.weight`, cpuset effective | priority, affinity, cgroup CPU quota | CPU permission and cgroup delegation unverified |
| Memory | `/proc/PID/status`, `prlimit(RLIMIT_AS)` read, `memory.max/high` | existing RLIMIT_AS backend, future cgroup controls | RLIMIT_AS caps virtual address space, not RAM/RSS |
| Swap | `VmSwap` in status; `memory.swap.max` | cgroup v2 swap budget | cgroup budget is group scope, not a single PID |
| Disk I/O | `/proc/PID/io`; cgroup `io.max/weight` | I/O priorities and cgroup I/O budget | I/O counters are not reliable block-device bandwidth guarantees |
| Threads | `Threads` in status; cgroup `pids.max` | task-count budget | cgroup counts tasks in shared group |
| GPU | bounded `/proc/PID/fdinfo` DRM evidence | no supported process GPU/VRAM actuator proven | absence is not proof of no GPU usage |
| Network | `/proc/PID/net/dev` is network-namespace totals | no process-specific bandwidth actuator proven | never attribute namespace counters to one process |

`/sys/fs/cgroup` sources are optional, cgroup v2 only. Cgroup file readable ≠ controller delegated. Missing or inaccessible sources stay missing/permission_denied, not zero. Host-specific facts cannot be claimed until the probe is actually run on the operator's machine.

## Run explicitly (observation only)

`python3 services/kill/resource_capability_probe.py --pid <PID> --start-ticks <START_TICKS> --comm <COMM>`

Only use a selected current process identity from KillStore, never guess the birth ticks. Command emits bounded evidence as JSON, with no process commands or write side effects. This command is documentation, not authorization to run on the operator's workstation.

## VERIFY / WATCH OUT FOR

Hosted regression uses only disposable Python child processes, stale identity mocks, and cgroup escape tests. A successful hosted Linux test does **not** prove desktop permissions, cgroup delegation or GPU capability. The real host must later be observed read-only; production control registration remains HOLD.

## NEXT / DECISIONS

K8d can use these bounded descriptors as a *read-only* source for the right-panel inventory. Keep the left instruments, shared KillStore custody and existing buttons unchanged. Do not advertise CPU/GPU/network actuators until the specific backend, scope and permission model are verified. No background poller or escalation.
