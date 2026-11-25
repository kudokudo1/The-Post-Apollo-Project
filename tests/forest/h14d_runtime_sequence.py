"""H14-D Runtime portion of the single harness: offline evidence ordering.

No runner, observer, process creation, controller writes, or authority.
Records are inputs to an offline consistency check, not independent OS proof.
Heart owns resource sampling/evaluation; Spirit owns isolation evidence.
"""
from dataclasses import dataclass
from h14d_resource_witness import (CAP, QUOTA, TASK_CAP, MAX_NS, MAX_SAMPLE_NS,
                                   MAX_SAMPLES, Sample, Hold, require,
                                   validate_prefix, evaluate)


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


def _check_launch(plan, *, parent_preflight_end_ns, outer_baseline_end_ns, launch):
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


def check_sequence(plan, *, parent_preflight_end_ns, outer_baseline_end_ns,
                   launch, terminal):
    """Offline original launch/terminal ordering; never OS proof or authority."""
    _check_launch(plan, parent_preflight_end_ns=parent_preflight_end_ns,
                  outer_baseline_end_ns=outer_baseline_end_ns, launch=launch)
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


@dataclass(frozen=True, slots=True)
class ReaderRef:
    """Synthetic independent provenance reference, not an OS Reader handle."""
    boot: str
    scope: Scope
    key: str


@dataclass(frozen=True, slots=True)
class Observation:
    reader: ReaderRef
    sample: Sample


@dataclass(frozen=True, slots=True)
class JoinedLaunch:
    process: Process
    inner: Scope
    image_digest: str
    launch_ns: int
    pinned_ns: int
    limits_ns: int
    limits: Limits
    release_ns: int


@dataclass(frozen=True, slots=True)
class IsolationRef:
    """Synthetic identity-bound reference only; cannot certify isolation."""
    process: Process
    inner: Scope
    observed_ns: int
    checks: tuple


ISOLATION_CHECKS = ("DESCENDANTS", "CONTROLLER_WRITES", "UID_CAPABILITIES",
                    "NAMESPACE_MOUNTS", "DEVICES", "CREDENTIALS", "NETWORK")


@dataclass(frozen=True, slots=True)
class TerminalRef:
    process: Process
    exit_status: int
    observed_ns: int
    disposed_ns: int


@dataclass(frozen=True, slots=True)
class _JoinedPrefix:
    """Caller-owned in-process fixture continuity, not a capability or proof of begin_join."""
    plan: Plan
    parent_reader: ReaderRef
    outer_reader: ReaderRef
    parent: Observation
    baseline: Observation
    first: Observation
    launch: Launch
    isolation: IsolationRef


def _reader(ref, boot, scope):
    require(type(ref) is ReaderRef and type(ref.boot) is str and ref.boot == boot
            and _scope(ref.scope) and ref.scope == scope
            and type(ref.key) is str and bool(ref.key), "READER_REFERENCE_MISMATCH")


def _observation(obs, reader):
    require(type(obs) is Observation and obs.reader is reader
            and type(obs.sample) is Sample and type(obs.sample.levels) is tuple
            and bool(obs.sample.levels), "OBSERVATION_REFERENCE_MISMATCH")
    return obs.sample


def _check_isolation(isolation, launch):
    require(type(isolation) is IsolationRef and _process(isolation.process)
            and isolation.process == launch.process and _scope(isolation.inner)
            and isolation.inner == launch.inner and _uint(isolation.observed_ns)
            and launch.pinned_ns <= isolation.observed_ns <= launch.release_ns
            and type(isolation.checks) is tuple
            and all(type(v) is str for v in isolation.checks)
            and isolation.checks == ISOLATION_CHECKS, "ISOLATION_REFERENCE_MISMATCH")


def begin_join(plan, *, parent_reader, outer_reader, parent, baseline, first,
               launch, isolation):
    """Validate synthetic prefix before simulated progression.

    No effect, permission, OS provenance or real isolation is established.
    All resource fields are taken from the original Heart Sample instances.
    """
    require(type(plan) is Plan and _scope(plan.parent) and _scope(plan.outer)
            and type(launch) is JoinedLaunch, "INVALID_JOIN_INPUT")
    _reader(parent_reader, plan.boot, plan.parent)
    _reader(outer_reader, plan.boot, plan.outer)
    require(parent_reader is not outer_reader and parent_reader.key != outer_reader.key,
            "READER_REFERENCE_REUSED")
    p = _observation(parent, parent_reader)
    b = _observation(baseline, outer_reader)
    f = _observation(first, outer_reader)
    # The single Heart prefix implementation owns all resource validation.
    validate_prefix(p, f, selected=plan.cpus, launch_ns=launch.launch_ns,
                    expected_leaf=(plan.outer.device, plan.outer.inode),
                    scope="RETAINED_OUTER", baseline=b)
    require(p.levels[-1].identity == (plan.parent.device, plan.parent.inode),
            "PARENT_IDENTITY_MISMATCH")
    derived = Launch(launch.process, launch.inner, plan.outer, launch.image_digest,
                     launch.launch_ns, launch.pinned_ns, launch.limits_ns,
                     launch.limits, plan.outer, f.start_ns, f.end_ns, launch.release_ns)
    _check_launch(plan, parent_preflight_end_ns=p.end_ns,
                  outer_baseline_end_ns=b.end_ns, launch=derived)
    _check_isolation(isolation, derived)
    return _JoinedPrefix(plan, parent_reader, outer_reader, parent, baseline,
                         first, derived, isolation)


def finish_join(prefix, *, parent, baseline, observations, terminal, isolation):
    """Audit original caller-held fixture references; no effects or authority.

    The caller must retain the actual begin_join result and original isolation
    reference independently. Object identity checks cannot authenticate a
    constructed or coherently replaced fixture, or prove kernel provenance.
    """
    require(type(prefix) is _JoinedPrefix and type(terminal) is TerminalRef,
            "JOIN_OR_TERMINAL_MISSING")
    require(type(prefix.launch) is Launch, "INVALID_JOIN_INPUT")
    _check_isolation(prefix.isolation, prefix.launch)
    require(isolation is prefix.isolation, "ISOLATION_REFERENCE_REPLACED")
    require(parent is prefix.parent and baseline is prefix.baseline
            and type(observations) is tuple and 2 <= len(observations) <= MAX_SAMPLES
            and observations[0] is prefix.first, "PREFIX_REPLACED")
    p = _observation(parent, prefix.parent_reader)
    b = _observation(baseline, prefix.outer_reader)
    samples = tuple(_observation(o, prefix.outer_reader) for o in observations)
    evaluate(p, samples, selected=prefix.plan.cpus, launch_ns=prefix.launch.launch_ns,
             expected_leaf=(prefix.plan.outer.device, prefix.plan.outer.inode),
             scope="RETAINED_OUTER", baseline=b)
    final = samples[-1]
    require(_uint(terminal.observed_ns) and terminal.observed_ns < final.start_ns,
            "TERMINAL_NOT_BEFORE_FINAL_READ")
    derived = Terminal(terminal.process, prefix.plan.outer, terminal.exit_status,
                       terminal.observed_ns, final.end_ns, final.populated,
                       final.levels[-1].tasks, terminal.disposed_ns)
    result = check_sequence(prefix.plan, parent_preflight_end_ns=p.end_ns,
                            outer_baseline_end_ns=b.end_ns, launch=prefix.launch,
                            terminal=derived)
    return dict(result, status="JOINED_OFFLINE_REFERENCE",
                progression_authorized=False, reader_provenance_verified=False,
                isolation_verified=False)
