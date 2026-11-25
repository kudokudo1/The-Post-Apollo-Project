"""H14-D Runtime portion of the single harness: offline evidence ordering.

No runner, observer, process creation, controller writes, or authority.
Records are inputs to an offline consistency check, not independent OS proof.
Heart owns resource sampling/evaluation; Spirit owns isolation evidence.
"""
from dataclasses import dataclass
from h14d_resource_witness import CAP, QUOTA, TASK_CAP, MAX_NS, MAX_SAMPLE_NS, Hold, require


@dataclass(frozen=True, slots=True)
class Scope:
    mount_id: int
    device: int
    inode: int


@dataclass(frozen=True, slots=True)
class Process:
    boot: str
    container: str
    pid: int
    start_ticks: int


@dataclass(frozen=True, slots=True)
class Limits:
    memory: int
    swap: int
    quota: tuple
    cpus: tuple
    tasks: int


@dataclass(frozen=True, slots=True)
class Plan:
    boot: str
    image_digest: str
    parent: Scope
    outer: Scope
    cpus: tuple


@dataclass(frozen=True, slots=True)
class Launch:
    process: Process
    inner: Scope
    outer: Scope
    image_digest: str
    launch_ns: int
    pinned_ns: int
    limits_ns: int
    limits: Limits
    first_active_scope: Scope
    first_active_start_ns: int
    first_active_ns: int  # completed observation, not sample start
    release_ns: int


@dataclass(frozen=True, slots=True)
class Terminal:
    process: Process
    outer: Scope
    exit_status: int
    observed_ns: int
    final_ns: int
    populated: int
    tasks: int
    disposed_ns: int


def _uint(v):
    return type(v) is int and v >= 0


def _scope(v):
    return type(v) is Scope and all(type(x) is int and x > 0
                                   for x in (v.mount_id, v.device, v.inode))


def _pair(v):
    return type(v) is tuple and len(v) == 2 and all(_uint(x) for x in v)


def _limits(v):
    return (type(v) is Limits and all(_uint(x) for x in (v.memory, v.swap, v.tasks))
            and _pair(v.quota) and _pair(v.cpus))


def _digest(v):
    return (type(v) is str and len(v) == 71 and v.startswith("sha256:")
            and all(c in "0123456789abcdef" for c in v[7:]))


def _process(v):
    return (type(v) is Process and type(v.boot) is str and bool(v.boot)
            and type(v.container) is str and len(v.container) == 64
            and all(c in "0123456789abcdef" for c in v.container)
            and type(v.pid) is int and v.pid > 0
            and type(v.start_ticks) is int and v.start_ticks > 0)


def check_sequence(plan, *, parent_preflight_end_ns, outer_baseline_end_ns,
                   launch, terminal):
    """Check ordering and identity of already supplied reference records.

    This is not a live evidence producer. No returned field grants admission
    or proves confinement, resource accounting, successful terminal custody,
    host/image provenance, or a right to dispose of a real cgroup.
    The retained outer path is selected before launch; there is no fallback.
    """
    require(type(plan) is Plan and _scope(plan.parent) and _scope(plan.outer)
            and plan.parent != plan.outer
            and plan.parent.mount_id == plan.outer.mount_id
            and plan.parent.device == plan.outer.device
            and type(plan.boot) is str and bool(plan.boot)
            and _digest(plan.image_digest)
            and type(plan.cpus) is tuple and len(plan.cpus) == 2
            and all(_uint(c) for c in plan.cpus) and plan.cpus[0] < plan.cpus[1],
            "INVALID_PRESELECTED_SCOPE")
    require(type(launch) is Launch and _process(launch.process)
            and launch.process.boot == plan.boot
            and _scope(launch.inner) and _scope(launch.outer)
            and launch.outer == plan.outer
            and _scope(launch.first_active_scope)
            and launch.first_active_scope == plan.outer
            and launch.inner not in (plan.parent, plan.outer)
            and launch.inner.mount_id == plan.outer.mount_id
            and launch.inner.device == plan.outer.device
            and _digest(launch.image_digest) and launch.image_digest == plan.image_digest,
            "ORIGINAL_LAUNCH_MISMATCH")
    times = (parent_preflight_end_ns, outer_baseline_end_ns, launch.launch_ns,
             launch.pinned_ns, launch.limits_ns, launch.first_active_start_ns,
             launch.first_active_ns,
             launch.release_ns)
    require(all(_uint(t) for t in times), "INVALID_CLOCK")
    require(0 <= launch.launch_ns - parent_preflight_end_ns <= MAX_SAMPLE_NS
            and 0 <= launch.launch_ns - outer_baseline_end_ns <= MAX_SAMPLE_NS,
            "STALE_PREFLIGHT_OR_BASELINE")
    require(launch.launch_ns <= launch.pinned_ns <= launch.limits_ns
            <= launch.release_ns
            and launch.pinned_ns <= launch.first_active_start_ns
            < launch.first_active_ns <= launch.release_ns
            and launch.first_active_ns - launch.launch_ns <= MAX_SAMPLE_NS
            and launch.release_ns - launch.launch_ns <= MAX_SAMPLE_NS,
            "EARLY_RELEASE_OR_LATE_OBSERVATION")
    expected = Limits(CAP, 0, QUOTA, plan.cpus, TASK_CAP)
    require(_limits(launch.limits) and launch.limits == expected,
            "INNER_LIMIT_MISMATCH")
    require(type(terminal) is Terminal and _process(terminal.process)
            and terminal.process == launch.process and _scope(terminal.outer)
            and terminal.outer == plan.outer,
            "ORIGINAL_TERMINAL_MISMATCH")
    require(type(terminal.exit_status) is int and terminal.exit_status == 0,
            "TERMINAL_NOT_SUCCESSFUL")
    require(all(_uint(t) for t in (terminal.observed_ns, terminal.final_ns,
                                   terminal.disposed_ns))
            and launch.release_ns <= terminal.observed_ns <= terminal.final_ns
            <= terminal.disposed_ns
            and terminal.final_ns - launch.launch_ns <= MAX_NS,
            "TERMINAL_ORDER_OR_WINDOW")
    require(type(terminal.populated) is int and terminal.populated == 0
            and type(terminal.tasks) is int and terminal.tasks == 0,
            "FINAL_OUTER_NOT_EMPTY")
    return {"status": "OFFLINE_SEQUENCE_REFERENCE",
            "actual_launch": False, "terminal_verified": False,
            "confinement_verified": False, "resource_verified": False,
            "disposal_authorized": False, "permission_granted": False,
            "production_authority": False, "safe_actions": []}
