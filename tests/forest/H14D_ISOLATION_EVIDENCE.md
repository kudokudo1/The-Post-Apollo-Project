# H14-D // Spirit effective isolation evidence contract

Status: draft, Security-owned portion of the bounded no-model containment
development authorization in #2806 comment 7172485574. No manual invocation,
native inference, protected operation or production authority. This document
does not install a probe, select an image, launch a process or grant release.

## 1. Separation and trust boundary

Heart owns the existing resource Reader and shared prefix/final evaluator.
Runtime owns the single launch, original process/descendant identity, terminal
and disposal sequence. Spirit owns the effective isolation/effect boundary.
The existing Runtime IsolationRef and its seven check labels are synthetic
references only. No label, Docker configuration field or successful resource
prefix is sufficient evidence of an effective control. Do not add a second
launcher, Reader, independent duplicate policy store or permission issuer.

A host-side observer within the explicitly authorized disposable CI environment
must bind each observation to the same original boot, pinned cgroup mount and
inode, container identity, original PID and start time, immutable image identity,
and monotonic observation interval. The observer must be outside the payload
and must not accept payload assertions as proof. Runtime must resolve the exact
inner process and scope before the first active resource observation and must
retain the original identity across the final audit. Missing, contradictory,
unreadable or replaced evidence is HOLD, not an assumed negative observation.

## 2. Evidence sources and refusal conditions

These are requirements for the subsequent integrated implementation, not a
claim that the selected runner provides any of the evidence.

| Runtime label | Independent evidence needed | Refuse when |
| --- | --- | --- |
| DESCENDANTS | Original host PID/start identity; pinned inner and outer hierarchy; bounded recursive process membership and original parent/child lineage; original terminal plus separate final empty observation | Unexpected member, migration, escaped or unaccounted task, missing original terminal, identity replacement or incomplete traversal |
| CONTROLLER_WRITES | Actual cgroup mount visibility and write restrictions in the payload mount namespace; effective process privilege and no inherited writable controller descriptors | Writable controller path, delegated modification capability, exposed controller descriptor or unknown effective access |
| UID_CAPABILITIES | Host-side process status including real/effective/saved/fs IDs, supplementary groups, effective/permitted/inheritable/ambient/bounding capabilities, NoNewPrivs and required seccomp status for each original member; independently resolved namespace mappings where applicable | Root inside payload, unexpected group or identity, any prohibited capability, missing privilege or seccomp restriction, unverifiable mapping |
| NAMESPACE_MOUNTS | Compare original namespace identities with host; actual mount table and pinned root from host-side process view; explicit allowlist of required private pseudo-filesystems and bounded scratch; read-only root; verify nested mounts independently | Host namespace sharing, host home/socket/device bind or writable host mount, unaccounted mount/scratch, unverified origin or effective flags |
| DEVICES | Actual effective device-access policy on pinned original inner hierarchy, including inherited restrictions and permitted character-device type/major/minor/access; verify no accelerator or block-device access and no inherited device descriptors | Unknown policy semantics, unknown effective inherited policy, broad device allowance, unexpected device access or descriptor, replaced cgroup |
| CREDENTIALS | Independently reviewed immutable benign image and fixed launch input; no injected secret, host home, credential mount, inherited host descriptor or external staging; inspect only presence/shape against fixed allowlist, never log values | Unreviewed image/input, credential channel or unaccounted inherited descriptor, inability to establish absence |
| NETWORK | Original distinct private network namespace; independently inspect interfaces, addresses, routing, sockets and inherited descriptors against loopback-only plan; no host publication or external endpoint | Non-loopback route/interface/socket, shared namespace, external or inherited host connection, unknown namespace evidence |

Root mount read-only is not proof that child mounts are read-only. Namespace
identity is not proof of allowed contents. NoNewPrivs is not a substitute for
capability and descriptor checks. Neither a count of cgroup members nor
absence of a device node proves that the intended original process is confined.

## 3. Effective device policy is an explicit feasibility gate

Cgroup v2 device access is implemented through cgroup BPF rather than a
devices.list interface. The kernel evaluates access type and device identity
at device access. A host-side query of effective cgroup device programs
(including inherited programs) can be one evidence input, but the presence
of a program ID or tag alone does not establish the policy's semantics.
Use independently reviewed effective policy evidence that establishes only
the exact minimal benign allowlist and excludes accelerator and block-device
access, with no retained descriptor or alternate device route. A policy
program with unknown instructions, mutable unverified map state, unknown
attachment ancestry or unreadable query is HOLD. Do not load, replace or
detach a policy merely to manufacture passing observation. Do not create
device nodes or attempt accelerator access as a substitute for policy proof.
No external network probe or new privileged payload is permitted.

The approved runner/image/runtime combination must demonstrate that such
read-only evidence is obtainable before any actual launch is requested.
No specific policy decoder or runner capability is assumed here.

References:
- Linux cgroup v2, device controller:
  https://docs.kernel.org/admin-guide/cgroup-v2.html#device-controller
- Linux eBPF syscall, program query and effective query flag:
  https://docs.kernel.org/userspace-api/ebpf/syscall.html
- Docker security and runtime options:
  https://docs.docker.com/engine/security/
  https://docs.docker.com/reference/cli/docker/container/run/

## 4. Temporal and effect boundary

Before any launch, require the separately approved pinned pre-existing benign
image and host/ancestor preflight; absent image or inability to establish
required observer capabilities refuses before launch, without auto-pull.
The bounded startup handshake must prevent benign payload progression until
the original identity, effective inner limits, Heart's first-active prefix
and all independent Spirit controls have been observed on that original
scope. Startup itself is already an effect, not an authorized inference.

Use the same original Reader and samples for the full resource audit.
Bind isolation observation completion to the pre-progression interval;
recheck relevant effective controls and original membership during the
bounded observation and before any claimed successful terminal. If any
control changes or cannot be observed, hold the original attempt and preserve
its evidence; never substitute a new process, switch accounting scope,
retry, or claim no effect. The original terminal must precede final empty
sample start; final read completes before disposal. Runtime owns finite
timeout and cleanup decisions; no cleanup-derived terminal receipt.

No observed containment result is a protected writer permission, independent
Connections receipt, model capacity estimate, physical memory reservation or
production authorization. All authority outputs remain false.

## 5. Required offline and eventual native negative cases

Use fixed-public input for offline tests. Demonstrate refusal on each missing
or mismatched observation, stale/replaced original process or mount identity,
foreign descendant, policy program present but semantics unknown, no device
nodes with unverified access policy, read-only root with writable unexpected
child mount, inherited descriptor, non-loopback route, secret injection,
observer loss and terminal/disposal mismatch. Also refuse an observation
that finishes after progression and any label-only isolation assertion.
No positive synthetic fixture may be promoted to native evidence.

Only fixed aggregate status/reason codes, original operation reference and
bounded timings may leave the observer. Do not export environment, credential
values, raw descriptor targets, full mount tables or private paths. Actual
evidence source feasibility, exact implementation and integrated focused
tests require Heart/Runtime compatibility and independent Nurse review.
The eventual manual-only workflow remains uninvoked and requires separate
explicit operator/Nurse run approval plus successful preflight.

## 6. Read-only evidence feasibility and negative qualification

Design supplement authorized by Nurse #2161 comment 7185166925, with
Heart 7183374829 and Runtime 7184293060 compatibility. This is a
candidate evidence acquisition contract, not a selected runner, policy,
observer, permission, implementation or native acceptance.

| Evidence | Potential independent observation | Required feasibility / refusal |
| --- | --- | --- |
| Effective device policy | On the independently pinned cgroup FD, BPF_PROG_QUERY with BPF_F_QUERY_EFFECTIVE for BPF_CGROUP_DEVICE; program references via BPF_PROG_GET_FD_BY_ID and information via BPF_OBJ_GET_INFO_BY_FD | Require complete effective set and actual semantics, including inherited restrictions and applicable attachment composition; refuse inaccessible, truncated, ambiguous or changing results. |
| Original process and descendants | Host pidfd, boot/PID/start identity, pinned cgroup mount/inode, bounded recursive membership and lineage | Independently establish original identity and exclusive membership; refuse reuse, migration, incomplete traversal or unknown descendant. A pinned process handle does not pin its membership or prove absence of escape. |
| Namespace, mount and controller scope | Host-side process namespace handles, mountinfo, root identity, controller access and FD inventory | Verify exact namespace/root and every relevant nested mount and inherited descriptor against reviewed allowlist; refuse writable controllers, shared or unexpected host mounts, incomplete visibility or mutable scope. |
| Credentials and device/FD exposure | Per-member status, ID mappings, groups, capability sets, NoNewPrivs, seccomp evidence and independently classified descriptors | Refuse unapproved credentials, retained device or host descriptors, unaccounted transfer/acquisition, or unknown effective restrictions. A status bit alone does not establish seccomp policy semantics. |
| Network and credential channels | Original private network namespace interfaces, addresses, routes, sockets, descriptor and reviewed immutable image/input provenance | Require loopback-only boundary and absence of credential/external channels, including inherited or transferred descriptors; no external connectivity or device-access probe. Export only approved aggregate reasons. |

A deliberately restricted, independently reviewed deterministic map-free
device-policy profile is a candidate for first qualification. An approved
profile would have bounded known instructions and exact device
type/major/minor/access semantics, default refusal outside the minimal
benign character-device allowlist, no permitted accelerator or block-device
access, and no opaque helpers, external mutable inputs or unverified
effective composition. Compare actual translated instructions and relevant
kernel semantics to the reviewed profile; an ID, tag or program count is
not semantic evidence. Even freezing a map does not prevent BPF-program
writes. A program FD retains the object, not its attachment. Require
independently established prevention of policy/attachment changes
throughout the original interval, including inherited controls; matching
endpoint queries cannot exclude intervening change. If the existing
runtime policy cannot be independently qualified in this restricted
profile, HOLD and seek a separate design decision, not a policy rewrite,
universal interpreter or substitute device probe.

Host visibility and permission are explicit prelaunch feasibility gates.
The intended approved disposable runner, pinned image, kernel/runtime
and observer capability must be identified and separately qualified;
procfs views and descriptor access can be restricted by namespace and
ptrace checks. A missing record may mean denied visibility, not absence.
No privilege grant or payload-side observer is implied. The reviewed
host/runtime must establish prevention of unobserved process migration,
controller/policy mutation, namespace escape and unexpected descriptor
acquisition/transfer throughout the attempt; snapshots alone cannot
establish continuous confinement. Actual feasibility remains UNKNOWN.

Before any separately authorized creation, assess the planned observer
and policy capability without consuming or relaxing the final parent
and optional outer baseline freshness (each complete within 1s before
actual launch). After creation, independently pin the original inner
identity before first-active observation. The trusted startup gate
must prevent payload progression until the original Heart prefix and
all Spirit effective observations complete, with progression no later
than actual launch plus 1s. Keep the original monotonic launch
reference, preselected scope, Reader and samples; no substitute
process or scope. Do not infer this deadline is achievable from
synthetic test durations. Preserve bounded rechecks, original terminal
before final empty sample and disposal after final read.

Additional negative qualification cases for future separate review:
incomplete effective query, matching program ID with unknown semantics,
opaque/mutable map state even when frozen, pinned program detached or
inherited policy changed, denied procfs visibility misread as empty,
transient membership/control/descriptor change not excluded, prelaunch
feasibility mistaken for actual original evidence, stale parent/baseline,
late Heart prefix or late Spirit completion, and observer loss before
progression or terminal. Any such failure is HOLD; after creation retain
the original attempt/evidence with no payload progression on a failed
startup gate, no assertion of no effect, no retry or replacement.
Runtime owns bounded cleanup and original terminal; cleanup cannot
manufacture terminal evidence. No new observer, launcher, workflow,
BPF program, policy attach/detach, native probe or privilege authorized.

Reference interfaces (not evidence of runner support):
- https://docs.kernel.org/userspace-api/ebpf/syscall.html
- https://docs.kernel.org/admin-guide/cgroup-v2.html#device-controller
- https://docs.kernel.org/filesystems/proc.html
- https://man7.org/linux/man-pages/man2/pidfd_open.2.html
- https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html
- https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html

Exact Heart, Runtime and independent Nurse design review before operator
integration. Any executable acquisition, native run or privilege decision
requires separate explicit authorization. Connections F1–F6, native
containment, protected operation and production remain HOLD.
