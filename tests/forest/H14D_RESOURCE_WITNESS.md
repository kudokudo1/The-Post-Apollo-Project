# H14-D Heart measurement slice — no-model containment harness
Nurse #2806 comment 7172485574 explicitly approves development and
offline checks; actual manual invocation remains HOLD. Runtime owns
launch/original identity/terminal and Security owns isolation. This
is one test-tooling portion of the existing H14-D harness, not a
second launcher, general resource manager, or installed entry point.

Reader pins every visible non-root cgroup ancestor by independently
supplied original (device,inode), uses existing I5 path/mount/read
helpers, H3 pressure/event parsing and H4 quota/cpuset parsing. It
rechecks original paths and mount, reads bounded counters and brackets
host MemAvailable and PSI. Missing, changed or inaccessible data
refuses; caller must treat all exceptions as HOLD. No process creation,
controller writes, device or network probe, or model request.

Runtime integration contract: use a verified fresh external hosted VM,
explicit non-root parent, original ordered ancestry, actual boot/host
and image/device/namespace/mount/security evidence. Before spawning,
preflight parent resource observation against two selected CPUs and
actual launch monotonic reference (<=1s). Independently prove disk,
host CPU visibility, image, entire host/ancestor and isolation scope;
the resource function alone never authorizes launch. After creation
pin original child identity independently, observe with one Reader
until quiescence while original cgroup remains available. evaluate
takes parent sample, bounded tuple of child samples, selected CPUs,
actual launch_ns and independently expected_leaf; no path-derived or
first-sample-derived original. Up to 121 samples, <=1s observation
and gap, <=60s witness. Check exact leaf cap 6 GiB, zero swap,
200000/100000 quota, exact two-CPU set, 128 tasks, no leaf memory
events, bounded peak/current and CPU counter monotonicity, fixed
ancestor identities/limits/events, final observed empty group.
Require independently verified terminal outcome and original
descendant identity; empty group is not terminal proof.

Conservative proposal: require parent effective cpuset >=4, ancestor
hard/high headroom >=10 GiB at preflight, host >=10 GiB available,
and maintain >=4 GiB plus uncharged part of cap at host and ancestors.
Zero displayed host memory PSI and no observed PSI total change;
any ancestor memory event change refuses. These intentionally strict
conditions may block otherwise feasible runners. Review exact thresholds
with Runtime/Nurse; do not silently relax. No root-only ancestor layout
fallback. Missing kernel peak/oom_group_kill/cgroup.events or removed
original scope before last read refuses; Runtime must design lifecycle
preservation or propose a separately reviewed terminal evidence route.
No reset of peak/counters, no assertion continuous coverage or actual
physical reservation. Disk, scratch, process membership, effective
device denial, network and credential boundary, launch and terminal
remain independent Runtime/Security work. No manual workflow yet;
do not dispatch or launch from this PR.

Offline CI invokes only test_h14d_resource_witness.py (synthetic samples
and mocked identity reader tests), no model/image pull, container,
stress test or live observation. Resource result reports aggregates,
all actual admission/authority/terminal flags false. Independent
exact-head review and owner integration required before any manual run.

## Retained accounting alternative — explicit preselection only

Nurse #7174344329 conditional development approval is satisfied by Runtime
#7174798252 and Spirit #7174800788. Existing DIRECT scope remains default
for backward-compatible offline callers; actual Runtime must explicitly
select its accounting scope before any possible effect. No automatic
scope change or fallback. If the direct child cannot be retained through
the final read, a fresh exclusive outer cgroup may be preselected.

Runtime independently pins original mount/inode and ordered ancestry,
establishes fresh creation/exclusivity and uses the same Reader for
outer baseline, active and final samples. Call preflight_outer with
the uncapped parent observation and empty outer baseline before launch;
both observations must complete within 1s of actual monotonic launch.
Baseline requires exact cap/CPU/swap/pids, populated=0, pids.current=0,
zero swap/events, current and peak observed, never reset or presumed
zero. The existing parent preflight, ancestry, host pressure and margin
requirements remain. Call evaluate with scope="RETAINED_OUTER" and
that same baseline; first active sample within 1s of launch, <=1s gaps,
<=60s total, peak/CPU monotonic from baseline through final empty.
DIRECT refuses any outer baseline; retained mode refuses missing baseline.
Outputs distinguish scope, preserve observed baseline current/peak, and
compute CPU delta from outer baseline rather than first active sample.

Separate Runtime/Spirit evidence must bind the preselected scope, exact
same Reader lifetime, independent mount/boot/container/PID identity,
fresh creation, inner effective limits before payload progression, exact
one subtree, no foreign/escaped tasks or untrusted controller writes,
original terminal outcome and final original empty outer group before
disposal. Outer accounting cannot prove inner limits or terminal. Any
unknown HOLD, no retry/fallback. No new observer or launcher; no actual
invocation or model. Offline tests exercise both paths and baseline
refusals. Runtime's #2845 offline sequence reference is separate
ownership; integrate against reviewed Heart API without parallel
resource measurement.
