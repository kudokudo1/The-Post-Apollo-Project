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

## H14-C // Concrete external host candidate (proposal only)

Nurse #2161 7170579213 and #2800 7170575185 independently accept
H14-B design and request an exact feasible host/envelope plan. H14-B
is merged (51f0a408); owner agreements 7170413011 / 7170407821.
No execution, runner creation, model transfer or workflow is authorized.

### Host selection and finite planning envelope

Repository visibility verified PUBLIC. GitHub standard public hosted
ubuntu-24.04 x64 runner is documented as a fresh VM with 4 CPUs,
16 GB RAM and 14 GB SSD (GitHub-hosted runners reference:
https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Prefer this separate disposable job VM with an additional bounded
container over nested KVM: avoids dependence on /dev/kvm, guest
installation, and hypervisor memory overhead inside the job. Runtime
and Security must agree this revised isolation route before execution.
Published capacity is NOT observed available capacity or guaranteed
allocation. Existing CPU++ KVM workflow is not modified.

Candidate outer job preflight (proposed numbers, not measured model
demand): independently verify GitHub-hosted fresh x64 VM and cgroup-v2
controllers; at least 10 GiB MemAvailable, four visible CPUs, at least
4 GiB reserve after 6 GiB workload cap, no competing qualification job
in that VM, no unstable pressure, no inaccessible ancestor controller.
Recheck after staged inputs and image preparation, immediately before
launch. Effective ancestor limits and current usage must support this
envelope; host safety cannot be inferred from nominal runner size.
Disk preflight must account verified archive/extracted/model sizes,
image layers, writable scratch and explicit reserve; 14 GB advertised
alone is not sufficient. Refuse rather than clean unrelated files.
No operator workstation or self-hosted runner as fallback.

Candidate container (review specification, not a launch command):
6 GiB memory.max; memory.swap.max=0; CPU quota 200000/100000
(two CPU-equivalents, not a thread count), affinity to two independently
selected allowed CPUs; pids.max 128; fresh non-root UID; no delegated
cgroup writes, no privilege, no capability, no-new-privileges; read-only
root/input mounts and bounded accounted tmpfs (256 MiB proposal).
No host socket, credential, home, device or writable host mounts;
network namespace without external interfaces, loopback only, no
published ports; exact effective device allowlist excludes GPU
render/card, KFD, NVIDIA and other accelerators, no /dev/kvm.
Verify enforced cgroup and ancestor readback, namespaces, mount/device
policy, UID and descendants before sending. Do not claim Docker flags
alone prove containment or exclusive access. Fresh hosted VM and
container scope must exclude unrelated clients and provider processes;
one trusted fixed client and one private Ollama instance, no host
Ollama access. Runtime owns exact reviewed launch implementation;
Security owns privilege/credential/egress boundary. No root capability
inside the workload. Docker infrastructure, host page cache and
preparation outside workload charged separately to host margin.

### Exact staged identity and execution proposal

Upstream release API v0.32.14 reports linux-amd64.tar.zst,
1421191399 bytes, SHA256
c620917a71e146ab3a7f893084f066069c4c65d144ef8379a91c3cbe8b27de8f.
This is a public release asset reference, not authenticated installed
runtime or downloaded bytes. Pin and verify release, archive, extracted
binary/runner/library hashes and immutable image digest independently.
Do not pull/install now. Granite3.3:2b operator short ID 07bd1f170855
is NOT a full manifest digest. Require full independently pinned
manifest and all referenced blob digests/sizes, exact tokenizer/template
and text-only/no adapters/projectors, verified staged model artifact
matching the selected identity. No private operator file or credentials
may be uploaded. Separate explicit approval needed for external public
artifact acquisition; preparation egress separate from offline execution.
Disk requirements and exact full model digest remain unestablished.

Select separate external containment qualification, not integrated H11
admission, and propose the existing P2B fixed public READY workload
semantics (2048 context, 32 output, think=false, one request, no tools).
Existing P2B does NOT enforce native options or isolation and its numeric
acknowledgments are not a demand bound. Runtime must agree exact
single request seam and manifest before code or execution; no reuse of
H11 attempt and no false claim of P2B/H11 compatibility. Proposed
native settings: num_gpu=0, num_thread=2, num_batch=128,
num_parallel=1, max_loaded_models=1, explicit no-auto context,
bounded residency policy (keep_alive=0 proposed), no adapters/projectors
or speculative draft model, no automatic fallback/retry. Verify support
and effective values; unknown/refusal remains HOLD. Exact rendered
template/token count + output allowance before request; no truncation.
Candidate deadline 180 seconds total from container launch including
provider readiness, single POST and terminal observation; no retry
or automatic second trial. A bounded normal isolated teardown is
separate from a forced timeout; forced termination records failed/
unknown outcome, not successful completion or demand proof.

### Independent observation and terminal gates

Host-side observer must not depend on workload self-report. Record
original boot/cgroup/namespace/process lifetimes, limits/readback,
memory.current and fresh-scope kernel memory.peak (including startup),
memory.events, swap.current, cpu.stat, pids and host headroom/pressure;
use I5/H3/H4 semantics where applicable, not repeated short snapshots
as full peak coverage. Separate before-provider baseline, startup,
pre-send, request, terminal and final teardown; bounded observation
interval and deadline, account host-side staging/cache separately.
Observe original provider/runner and exact one request and terminal
outcome; prove no second load/retry, original descendant quiescence,
empty workload scope before disposal, independent accounting and
Security disposition. No proof from socket EOF/HTTP done or container
exit alone. OOM/pressure/limit violation/observer loss/timeout/identity
drift/refusal remains failed or unknown; no retry and no requirement
credit. Capture only fixed public aggregate evidence; no raw environment,
credentials, private logs or prompt data. Preserve original outcome
before cleanup; no shared service or host cleanup.

### Required decisions

This candidate is a feasibility design, not an authorized job or
measurement. Runtime: ACCEPT/REVISE exact outer VM + container
isolation and existing P2B semantics/single effect seam; Security:
ACCEPT/REVISE staged public inputs, credential/device/egress denial
and independent terminal custody; Nurse: exact design review and
separate scope for a no-model containment verification if needed.
Operator must explicitly approve external staging/actual execution,
exact identities, tested envelope and one workload before inference.
No normal H9 admission, H1 zero-demand revision, guaranteed demand,
GPU readiness or production release follows from a successful capped
CPU experiment. No new CI job, runner script, source or host action
in this amendment.


## H15 // Resource dimension applicability (design only)

Nurse #2161 7189221566 authorizes this document only; Heart
7189047023, Runtime 7189169544 and Spirit 7189174213 agree.
Main d351c035 at intake. No change to H1/P1/H2 code, test, schema,
issuer or authority. No actual host or model qualification.

### Existing seam and representation gap

H1 62dc22ec _evaluate requires an explicit ceiling and positive
requirement in every P1 dimension; zero is ZERO_DEMAND_UNESTABLISHED.
P1 38f1723b uses None for unknown requirement, zero for no incremental
requirement beyond the exact baseline, and skips availability comparison
when requirement is zero. P1 approve is modeled fit only. H2 4ec58531
account_release_reference requires all three availability values known,
same source and clock, exact original AttemptRef, a separate terminal
reference and active_workload=False. These are local disposable reference
checks, not independent evidence or physical accounting.

H1 TransportSettings covers only B2 endpoint/model/context/output;
its digest is not a complete provider manifest. The existing six-field
H2 AttemptRef binds context, turn, operation, attempt, binding and
settings; it does not attest actual placement or device exclusion.
Do not change those meanings silently or invent a second governor.

| Resource state | Candidate interpretation (not an API or present acceptance) |
| --- | --- |
| Positive RAM/CPU requirement | Exact conservative demand, explicit budget and independently current availability required; existing arithmetic preserved. |
| Applicable accelerator, positive demand | Exact mapped accelerator requirement, budget, availability, placement and currentness required. |
| Applicable accelerator with measured zero free capacity | Known zero availability; cannot meet positive demand. |
| Unknown applicable demand or availability | HOLD for admission; no zero substitution or dummy positive demand. |
| Independently proven accelerator-inapplicable | Zero incremental accelerator demand only for the exact CPU-only execution under the proof below. Host VRAM availability may be unknown; do not fabricate measured zero. |
| Unproved CPU-only claim, uncertain retained charge or changed evidence | HOLD, including original custody at release; no inference from absent observed usage. |

No general zero RAM/CPU exception or new positive outcome. A known
budget violation remains a denial under P1. A modeled fit is never
authorization. The inapplicable case is a proposed narrower reference
meaning, not a presently accepted H1/H2 input or a new wire value.

### Independent evidence needed before any exception

Bind applicability to an independently established original H11 attempt
and exact model artifact, immutable provider/runner release and instance,
execution manifest, actual original process and descendants, placement,
configuration/workload commitment, boot/scope/lifetime and H2 accounting
reference. Reuse existing identity seams; an eventual representation
change needs separate coordinated review. CPU-only placement must be
selected before admission, never substituted after GPU admission.

Require independently verified preventive accelerator exclusion across
the relevant original lifetime, including effective inherited device
policy semantics and mutation prevention; no retained/inherited or
transferred accelerator descriptors, alternate provider/service socket,
network/offload or migration route. Local client restriction does not
qualify the actual provider/runner. Exact effective runtime behavior
and complete original descendants must be established. A requested
num_gpu=0, configuration flag, inventory, BPF ID/tag, absent device
node, no observed GPU usage or test-only CPU configuration is insufficient.
H14-D benign no-model isolation, even if later qualified, cannot prove
actual model execution placement. Unknown or inconsistent proof refuses.

Independently establish that no accelerator residency/charge is
attributable to this attempt, including startup, prior retained state
and terminal accounting. A negative access observation now cannot erase
an earlier or unknown charge. Other unrelated host device charges do
not become free capacity or resource credit. Do not unload, restart,
reclaim, or subtract historical resident bytes to manufacture proof.

### Temporal and custody boundary

For any future separately approved native path, establish the exact
preventive applicability evidence before the actual send and original
claim under independently current execution/effect fencing; preserve
H1 reference comparison/currentness and exact settings digest. Recheck
original identity, policy, placement and coverage through execution,
terminal and original accounting. Any unknown, change or observer loss
holds the original attempt; no retry, fallback, replacement identity or
automatic clearance. The no-model hosted qualification and separate P2B
timing-only trial do not supply H11 admission evidence.

Keep positive applicable dimensions, source/clock checks, original
terminal and independent quiescence, retained-residency accounting and
Spirit settlement separate. Release only the exact original custody
after independent qualifying evidence; a future inapplicable dimension
could remove a need for host VRAM measurement only if its original
proof and absence of attributable retained charge remain established.
Never change unknown applicable capacity into zero. Neither SQL
COMMITTED/ABORTED, STOP/EOF, cache close, roster absence nor a synthetic
reference establishes terminal or physical release. No new resource
credit, admission, restore or Winter inference.

### Negative acceptance matrix for separate future review

| Case | Required refusal or distinction |
| --- | --- |
| Zero accelerator demand with missing, stale, foreign or replaced original proof | HOLD; no exception from caller flag or settings digest. |
| CPU-only client but provider/descendant can use accelerator, inherited FD or alternate service/offload | HOLD; qualify actual execution lifetime, not client. |
| Effective policy opaque, mutable or incompletely observed | HOLD; matching tag/node absence not proof. |
| GPU-enabled placement, prior or unknown attributable device charge | Applicable/unknown dimension; no zero exception or release credit. |
| Positive applicable requirement, unknown or zero available quantity | Preserve unknown/insufficient refusal; no substitution. |
| Zero RAM or CPU demand | Preserve current H1 refusal; no general relaxation. |
| Original proof valid at intake but changes before send or terminal | HOLD original custody; no fallback/retry or replacement. |
| Exact CPU-only proof for another H2 attempt, stale terminal or uncertain quiescence | No release, no inherited accounting or automatic Winter. |
| Local commit/abort/STOP, logical cache removal or benign no-model test | No actual terminal, physical release or model admission. |

Candidate acceptance would require exact original independent evidence
and all existing applicable checks, not just a passing fixture. Actual
issuer, effective policy/observer feasibility, placement, demand bound,
original terminal and Connections custody remain unqualified. Request
Runtime/Spirit/Nurse exact design review before operator integration.
Any future executable H1/P1/H2 revision, tests or native qualification
requires separate explicit bounded approval. Production remains HOLD.


## H15b // Original applicability evidence lifecycle (design only)

Nurse #2161 7199718625 authorizes this existing document only.
Heart 7198813100, Runtime 7198782473 and Spirit 7196776273 define
the scope. H15 is integrated. No selected issuer, representation,
wire schema, new evaluator, or executable exception. Existing H1
62dc22ec and H2 4ec58531 remain unchanged: zero-demand refusal and
all-dimension release checks still apply.

### Candidate versioned vocabulary, not an API

Separate immutable original lineage from fresh independent evidence.
The six-field H11 AttemptRef and H1 TransportSettings fingerprint
retain their exact existing meanings. A future reference would need
a reviewed version and the following bound field groups, not merely
a caller assertion, a configuration digest or a zero quantity.

| Group | Required binding or evidence |
| --- | --- |
| Original operation | Exact H11 AttemptRef, task/turn/operation/attempt, model binding/settings, original claim incarnation; not a replacement context or reusable proof. |
| Planned configuration | Exact artifact, provider/runtime release and immutable execution/workload/placement manifest commitment; explicitly planned CPU-only, not actual observation. |
| Actual original lifetime | Independently pinned host boot, provider/process identity and start, scope and descendant boundary, actual artifact/runtime/manifest and effective placement. No invented precreation PID. |
| Preventive controls | Independent observer/policy source and revision, actual inherited effective device policy semantics, prevention of control mutation, descriptor transfer, alternative service/network/offload and migration; actual provider as well as descendants, not client alone. |
| Applicability and charge | Accelerator inapplicable only with independently established original exclusion and separate no-attributable-accelerator-charge evidence, including prior retained residency. Unknown applicable demand is not zero. |
| Currentness and coverage | Exact original lineage plus independently current source, policy/effect ordering, original clock domain, observation interval and completeness; independent original terminal/quiescence and later accounting are separate observations. |

Fresh observations naturally differ in timestamps, resource values
and coverage. Do not require byte-identical changing observations or
accept equal-value stale evidence as current. Pin the immutable lineage
and compare each new observation to that lineage and its independently
current source and applicable policy. A local lock can serialize local
reference checks only; it cannot prove continuous native prevention,
source authenticity, or revocation/effect ordering. No new issuer or
actual authenticated observer has been identified.

### Stage and custody matrix

| Stage | Required evidence and ordering | Missing or contradictory evidence |
| --- | --- | --- |
| Plan before creation | Independently reviewed planned manifest and selected CPU-only path, conservative applicable RAM/CPU demand, explicit ceilings and fresh available capacity, approved containment plan; no actual process identity or eligibility inferred. | No progression. No automatic GPU/CPU fallback or retry. |
| Separately authorized creation, before model/provider effect | Runtime pins actual original process/scope and provider/descendants behind trusted progression gate; establish actual preventive exclusion, independent original no-attributable-charge evidence, exact original attempt and claim incarnation. Revalidate plan and applicable resources. | Runtime retains original creation/unknown-effect custody; no successful H2 admission inferred, no progression or replacement. |
| Prospective original resource claim | Recompute exact applicable resource fit/currentness with independently qualified applicability; retain original evidence lineage within original serialized custody before effect. Existing H1/H2 cannot yet admit this case. | No new successful claim; preserve any original outstanding creation/operation. |
| Original progression and execution | Independently revalidate actual source/policy/placement and prevent unobserved control/FD/offload changes over the original interval. Preserve original H11 binding, one attempt and no new effect from evidence alone. | If original claim held, keep it sticky HOLD. No retry, replacement proof, reinitialization or release. |
| Terminal and later accounting | Independent original terminal and quiescence, same original source/clock and currentness, exact applicable remaining availability, retained residency accounted and original exclusion/charge coverage through terminal. Final accounting later than terminal, never inferred from cleanup. | Hold original custody; missing or uncertain attributable device charge is not zero or free capacity. |
| Hypothetical reference release | Only original matching custody after all prior evidence and independent settlement. No physical release credit or new permission. | No release or new admission. Existing refusal remains until a separately approved contract exists. |

The planned and actual stages cannot be collapsed: no positive claim
from planned CPU-only configuration, no model progression while actual
evidence is still incomplete. If an original isolated creation cannot
be qualified, its bounded cleanup and independent original outcome are
Runtime responsibilities; do not fabricate a terminal receipt to clear
it. H14-D's separately planned no-model startup gate and <=1s deadline
are unchanged; its success would not establish model placement.
P2B timing-only remains separate from H11 dispatch.

### Negative matrix for a separate future design/executable decision

| Case | Required result |
| --- | --- |
| Planned CPU-only manifest without actual original identity | No applicability exception, claim success or model progression. |
| Matching manifest with a different provider/process/start/scope/attempt/claim incarnation | Refuse; no proof transfer even if resource quantities match. |
| Client-only restriction, unverified inherited policy or retained/transferred accelerator FD, alternate service/offload | Refuse original applicability; no zero substitution. |
| Current negative access observation with prior or unknown attributable device charge | Hold; no retained-residency credit. |
| Fresh original observation with changed timestamp/value but unchanged lineage | Independently re-evaluate currentness and applicable fit, not an automatic mismatch or grant. |
| Same-value old observation, clock regression, observer loss or unproved intervening policy change | HOLD; historical proof is not current continuous prevention. |
| Creation succeeds but actual gate fails | Retain original Runtime creation/unknown-effect custody; no successful H2 claim, progression, fallback or retry. |
| Already held original claim, proof changes or is lost | Sticky original HOLD; no recreation/reclaim, replacement or release by local comparison. |
| Original terminal missing/unknown, quiescence incomplete, later accounting stale/foreign or attributable residency unresolved | Hold exact original custody; no physical release or Winter. |
| Local SQL COMMITTED/ABORTED, STOP/EOF, cache/roster changes or benign no-model test | No inference of original native terminal, applicability, release or admission. |
| Positive applicable requirement with unknown capacity, or zero RAM/CPU requirement | Keep existing refusal and positive applicable budget checks. |

### Decision boundary

No actual independently qualified original process/observer/policy
source or retained-charge coverage is established. H15b selects no
schema, source, dataclass, permission, implementation or native trial.
Before any proposed executable change, require separate owner-approved
representation and original claim/terminal/accounting compatibility
with H11/R7 and independent evidence feasibility. Otherwise retain
existing zero-demand refusal. Exact Runtime, Spirit and Nurse source
review and CI before operator documentation integration; all native,
protected and production gates remain HOLD.
