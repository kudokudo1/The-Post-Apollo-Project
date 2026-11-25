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

## H14-B // Proposed isolated qualification evidence path (DOC1F)

Post-merge baseline b57277b160ad0019567bfdb713c88e3d115abb30.
Nurse2F #2161 comment 7170042098; H12-B 7169646369, H14-A
7169680093 and upstream review 7170193404. Runtime isolation
direction ACK 7170207581 is a proposal only.

### Why the shared workstation remains HOLD

Operator-reported Ollama 0.32.14 / Granite3.3:2b, nonresident,
installed size 1545321637 bytes. Available host RAM moved from 5903
to 2556 MiB in roughly a minute. DRM card1 reports 4294967296 bytes
total and 2023731200 bytes headroom estimate, without runner mapping
or allocatable capacity. The visible service hierarchy has no finite
memory or CPU quota. H6 2048-token hypothetical dense FP16 cache is
160 MiB, not total requirement. I6b does not authenticate artifact
or runtime. No causal attribution or desktop resource guarantee.

Upstream v0.32.14 api/types.go, envconfig/config.go, server/sched.go
and llm/llama_server.go: explicit num_ctx/num_predict/num_thread/
num_gpu/num_batch and residency settings are requests; scheduler
parallelism and VRAM fit margins are not client exclusion or hard
resource limits. PredictServerVRAM uses file size + approximate KV;
conditional scheduler fit and batch estimates are not an independently
supported upper bound. No guessed zero accelerator demand, no dummy
positive requirement to evade H1, no retry/fallback or inferred token fit.

### Evidence route proposal for review, not permission to execute

Prefer independently supported exact-artifact/runtime/placement demand
evidence if available. If absent, request a separately reviewed
isolated qualification scope outside the operator workstation, NOT
a waiver of H9 C or a normal Forest admission. A disposable CPU-only
environment is the first candidate to evaluate; GPU qualification
remains separate. No substitution of CPU-only for an admitted GPU
attempt and no claim that CPU results qualify GPU placement.

Existing tests/cpuplus_memory_native/README.md and
run-silverblue-cycle.sh plus cpuplus-memory-native-cycle.yml demonstrate
an offline KVM guest with finite guest RAM/vCPUs, no host disk/network
passthrough and runner preflight. They do not contain an approved
Ollama/model trial. The 6 GiB guest/3 vCPU values are precedent, NOT
a proposed model requirement or authority to reuse CPU++'s workflow.
Do not launch that guest on the observed low-headroom workstation.
No edit of CPU++ files or CI workflow in this slice.

Before any future external qualification request:
1. Identify an authorized separate host/runner, exact boot/hardware/
   runtime artifact and model digest, staged immutable inputs and
   a single fixed-public workload; no private content or shared
   operator-service access. No automatic download, external network
   release or use of existing credentials.
2. Establish independently reviewed host safety envelope: fresh
   headroom after other charges and explicit host margin, finite
   total containment including guest/hypervisor or runner overhead,
   CPU-time/affinity and swap policy. Do not claim guest RAM caps
   hypervisor RSS or that a cgroup cap guarantees successful inference.
   No GPU passthrough/device exposure for CPU-only candidate; prove
   absence of accelerator access independently, not merely num_gpu=0.
   No guessed numeric limits. If a feasible envelope cannot be
   established, HOLD before spawning anything.
3. Runtime to specify exclusive provider lifetime and exact execution
   path. Existing B2/B3/R3 is prospective integrated route; P2B is
   separate timing-only path, not H11 integrated. No automatic
   substitution, second attempt, retry, unload or service restart.
   Exact effective token/template/placement/thread/batch/output and
   immutable workload/settings commitment must be independently bound.
4. If H9 C exact demand bound is still unavailable, Nurse and operator
   must explicitly decide whether a separate containment-limited
   qualification experiment is acceptable, including possible guest
   OOM/refusal and the risk to its separate host. Until approved this
   is design only. Containment limits are NOT model demand; no trial
   as preflight for its own normal admission. No actual execution
   authorized here, including CI.
5. Agree bounded same-domain observation and exact terminal evidence
   with Runtime/Security. Reuse I5/H3/H4 and I3/H8 where their semantics
   apply; I5 short sampled maximum and historical kernel peak alone
   are not complete trial coverage. Require independent baseline,
   peak coverage, post-terminal accounting, pressure/limit events,
   process lifetime and outcome. Incomplete coverage, OOM, identity
   drift, ambiguous settlement or unproved no-accelerator access
   produces HOLD; do not interpret failed capped run as a demand
   upper bound. No model loading or sampling implementation in this
   document.
6. After separately approved qualification, independently review
   observed data, runtime-specific static allocation evidence,
   measurement coverage, conservative modeled requirement/margin and
   applicability to the target environment. Never convert a single
   observed peak into a guaranteed bound or credit swap/resident
   bytes. CPU-only zero accelerator requirement needs separate
   coordinated H1 revision with independently supported proof.
   Native workstation admission remains H9 A-F plus fresh evidence
   and operator consent; production remains HOLD.

### Owner decision

Heart owns demand/measurement and conservative admission arithmetic;
Runtime owns isolation/enforcement/exclusive execution/terminal identity;
Security owns authority and settlement; CPU++ owns desktop stability.
Nurse2F to review this exact evidence route, including the separate
qualification-vs-admission distinction and whether a suitable host exists.
No executable implementation, new collector, CI job, service, host change,
model download or trial in this proposal. No numerical safety claim.
