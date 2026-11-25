# Forest Heart H9 // First native model admission gate reconciliation

PATIENT: The-Post-Apollo-Project · DOC 1F Heart · external Hospital-compatible.
DEVELOPMENT ACTIVE / NATIVE MODEL AND PRODUCTION HOLD.

## IMPLEMENTATION
Design-only delta to P2A/P2B and H1–H8. No new runner, daemon,
measurement collector, governor, issuer, service, or executable action.
Original Forest recovery: frozen Bristlecone resources/live_providers.py
at 28895aaf (blob 02bb29e3) used observed cold memory and resident
subtraction; retain exact workload/residency accounting, reject old
aggregate subtraction and 6144 MiB historical CPU-only floor.
H7/H8 are independent draft PRs #2689/#2694, both exact-head CI green at
this writing, independent review and merge outstanding. No dependency
on those unmerged functions.

## VERIFY // Actual missing links on target main 52fb321a
- B2 blob db572336: sends model, messages, stream, options.num_ctx and
  options.num_predict only; no explicit thinking, thread, device, or
  keepalive control. Cancel shuts down client socket, not provider work.
- P2B blob b5b7233e: fixed public READY workload, context 2048,
  output 32, think=false, manual numeric inputs and acknowledgement
  flags; host MemAvailable and reported residency are not enforced
  capacity. P2B is timing-only and not equivalent to B2.
- H3/H4: visible hierarchy memory and CPU constraints; not verified
  runtime identity, actual free capacity or reservation.
- H4b/I6/I6b: separate client/cgroup/process/provider claims, not
  a joined trusted service-runner/device/model mapping. Same-UID
  inspection does not authorize cross-UID access.
- H6: Granite/Qwen metadata cache scenarios only. Operator's last
  MemAvailable 1765 MiB, swap occupied 11826 MiB; stale snapshot,
  not grounds to launch. Quickshell controlled comparison incomplete.

## NEXT // Owner agreements before any native model trial
A. Heart + Runtime: agree a single exact trial manifest with existing
   I2 binding and H1/H2 attempt references, selected installed artifact
   digest, runtime release/instance, effective settings, workload digest,
   output/context/thread ceilings, placement, one in-flight operation,
   and a bounded deadline. First candidate Granite3.3:2b, 2048 context,
   32 output, fixed public synthetic workload; proposed, not authorized.
   A CPU-only or GPU candidate must be separately selected and qualified,
   not silently substituted after admission. Context bytes or character
   limits do not prove model-token count including runtime template.
B. Runtime owns actual enforcement: prove exact accepted provider
   options and actual behavior, no silent fallback/retry or extra model
   load. Requested num_ctx/num_predict or prospective thread/device
   options alone are not enforcement. Prove exclusivity against other
   clients of the same provider, or propose separately approved
   disposable isolation. Existing shared service must not be restarted
   or changed to force a trial. No claim generic cgroup controls cap
   GPU VRAM; CPU quota is CPU-time constraint, not a thread count limit.
   Any isolated process/service setup needs separate operator authorization.
C. Heart: obtain independent exact-model conservative host/accelerator
   incremental demand and safety margin appropriate to the chosen
   environment BEFORE running. Fresh H3/H4 and mapped device evidence,
   account parent/leaf constraints, host pressure, current competing
   workloads, exact warm/cold baseline and no swap credit. No arbitrary
   guessed requirement, disk-size-plus-KV admission, resident subtraction
   or use of the trial itself as preflight proof. If no credible bound,
   HOLD. Prefer reviewed isolated disposable test host if workstation
   resources remain insufficient.
D. Heart + Runtime: agree same-domain before/peak/after collection
   during one approved request; bounded collection interval and duration,
   counter units, exact runner/cgroup lifetime and accelerator attribution,
   observed coverage and missed-peak limits, no raw prompts or private
   logs. Reuse I3/H8 and P2B timing semantics; choose one execution path
   (P2B timing experiment OR B2 conversation trial), never both for the
   same attempt. No background poller on ForestW.
E. Runtime + Security: exact terminal outcome and actual quiescence
   independently checked; STOP/socket close or EOF is not resource
   release. Unknown outcome keeps H2 custody held; no automatic retry.
   Native public execution is separate from protected C5 disclosure.
F. Nurse2F: independent exact-source and evidence review; operator
   explicitly approves exact host/workload/limits/one attempt before any
   native change. R6 remains fixed public fake-provider CI-only and
   independent of native admission.

## HOW TO USE // Read-only current-state check
Only existing observer scripts, no model generation:
    free -m
    cat /proc/pressure/memory
    ollama ps
    systemctl show ollama.service -p ActiveState -p MainPID -p User -p ControlGroup
    python3 -B scripts/forest/heart_memory_headroom_h3.py observe --cgroup /system.slice/ollama.service
    python3 -B scripts/forest/heart_cpu_constraints_h4.py observe --cgroup /system.slice/ollama.service

The cgroup path above is historical operator evidence; use the actual
ControlGroup reported by systemctl, and HOLD if service/scope differs.
These are non-atomic diagnostic observations, not admission.
No commands to start, stop, unload, pull, run or change Ollama.

## DECISIONS
First real inference remains HOLD until A–F evidence and explicit consent.
H9 is an owner coordination design, not approval to implement Runtime
changes or alter host configuration. No R6 wire changes, no new worker,
no second resource manager. CPU++ retains system-wide memory diagnosis
and recovery ownership; Heart does not attempt desktop reclamation.
