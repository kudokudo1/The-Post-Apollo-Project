"""H14-D Heart portion of the manual-only NO-MODEL witness, test tooling.

Runtime supplies independently pinned original host/cgroup identity and owns
launch/terminal; Security owns isolation. No launch, command, network,
device probe, controller write or authority. Do not invoke on operator host.
"""
from contextlib import ExitStack
from dataclasses import dataclass
from fractions import Fraction
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import cgroup_observation_i5 as I5
import heart_memory_headroom_h3 as H3
import heart_cpu_constraints_h4 as H4
from performance_snapshot_p0 import _host_memory_available_mib

GIB = 1024 ** 3
CAP = 6 * GIB
MIN_HOST_MIB = 10 * 1024
HOST_MARGIN_MIB = 4 * 1024
TASK_CAP = 128
QUOTA = (200000, 100000)
MAX_NS = 60_000_000_000
MAX_SAMPLE_NS = 1_000_000_000
MAX_SAMPLES = 121
MAX_GAP_NS = 1_000_000_000
EVENT_KEYS = (b"low", b"high", b"max", b"oom", b"oom_kill", b"oom_group_kill")


class Hold(ValueError):
    """Fixed reason only."""


def require(condition, reason):
    if not condition:
        raise Hold(reason)


@dataclass(frozen=True, slots=True)
class Level:
    identity: tuple
    current: int
    hard: int | str
    high: int | str
    quota: tuple
    cpus: tuple
    tasks: int
    pids_max: int | str
    events: tuple


@dataclass(frozen=True, slots=True)
class Sample:
    start_ns: int
    end_ns: int
    levels: tuple
    host_available_mib: int
    host_pressure: tuple
    peak: int | None
    swap: int | None
    swap_max: int | str | None
    cpu_usec: int | None
    populated: int | None


def _read(fd, name, cap=4096):
    # Only callers below supply fixed counter filenames.
    counter = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
    try:
        return I5._read_fd(counter, cap)
    finally:
        os.close(counter)


def _scalar(fd, name, limit=False):
    return I5._scalar(_read(fd, name, 64), limit=limit)


def _level(fd):
    events = H3._events(_read(fd, "memory.events"))
    require(all(k in events for k in EVENT_KEYS), "EVENT_COUNTER_MISSING")
    return Level(
        I5._identity(fd), _scalar(fd, "memory.current"),
        _scalar(fd, "memory.max", True), _scalar(fd, "memory.high", True),
        H4._quota(_read(fd, "cpu.max", 64)),
        H4._cpuset(_read(fd, "cpuset.cpus.effective", 32768)),
        _scalar(fd, "pids.current"), _scalar(fd, "pids.max", True),
        tuple(events[k] for k in EVENT_KEYS),
    )


def _host_pressure():
    fd = os.open("/proc/pressure/memory", os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        values = H3._pressure(I5._read_fd(fd, 4096))
        return values[b"some"], values[b"full"]
    finally:
        os.close(fd)


class Reader:
    """Pin a non-root hierarchy across observations; caller owns lifetime.

    expected is the complete independently resolved ordered tuple of
    (st_dev, st_ino) for the selected group and its non-root ancestors.
    No identity is inferred from a path alone. Scope removal before the
    final sample is HOLD; no attempt to re-open replacement as original.
    """
    def __init__(self, path, expected, *, leaf):
        require(type(leaf) is bool, "INVALID_SCOPE")
        self.parts = I5._parts(path)
        require(type(expected) is tuple and len(expected) == len(self.parts)
                and all(type(x) is tuple and len(x) == 2
                        and all(type(v) is int and v > 0 for v in x)
                        for x in expected), "INVALID_SCOPE")
        self.expected = expected
        self.leaf = leaf
        self.stack = ExitStack()
        self.fds = ()
        self.used = False

    def __enter__(self):
        require(not self.used, "SCOPE_ALREADY_USED")
        self.used = True
        try:
            self.mount = I5._mount()
            self.fds = tuple(self._open(i) for i in range(1, len(self.parts) + 1))
            self._check()
            return self
        except BaseException:
            self.stack.close()
            self.fds = ()
            raise

    def _open(self, i):
        fd = I5._open_group(self.parts[:i])
        self.stack.callback(os.close, fd)
        return fd

    def _check(self):
        require(self.fds and I5._mount() == self.mount
                and tuple(I5._identity(fd) for fd in self.fds) == self.expected,
                "SCOPE_CHANGED")
        for i, identity in enumerate(self.expected, 1):
            fd = I5._open_group(self.parts[:i])
            try:
                require(I5._identity(fd) == identity, "SCOPE_CHANGED")
            finally:
                os.close(fd)

    def sample(self):
        self._check()
        start = time.monotonic_ns()
        host_a = _host_memory_available_mib()
        psi_a = _host_pressure()
        levels = tuple(_level(fd) for fd in self.fds)
        peak = swap = swap_max = cpu = populated = None
        if self.leaf:
            fd = self.fds[-1]
            peak = _scalar(fd, "memory.peak")
            swap = _scalar(fd, "memory.swap.current")
            swap_max = _scalar(fd, "memory.swap.max", True)
            cpu, = I5._table(_read(fd, "cpu.stat"), (b"usage_usec",))
            populated, = I5._table(_read(fd, "cgroup.events"), (b"populated",))
        host_b = _host_memory_available_mib()
        psi_b = _host_pressure()
        self._check()
        end = time.monotonic_ns()
        require(type(host_a) is int and type(host_b) is int, "HOST_MEMORY_UNKNOWN")
        require(psi_a == psi_b, "HOST_PRESSURE_CHANGED_DURING_READ")
        return Sample(start, end, levels, min(host_a, host_b), psi_b,
                      peak, swap, swap_max, cpu, populated)

    def __exit__(self, *args):
        self.stack.close()
        self.fds = ()


def _number(v):
    return type(v) is int and 0 <= v <= I5.MAX_NUMBER


def _limit(v):
    return v == "unlimited" if type(v) is str else _number(v)


def _cpus(intervals):
    require(type(intervals) is tuple and 1 <= len(intervals) <= H4.MAX_CPUS,
            "CPUSET_INVALID")
    last = -2
    count = 0
    for pair in intervals:
        require(type(pair) is tuple and len(pair) == 2
                and all(_number(v) for v in pair), "CPUSET_INVALID")
        a, b = pair
        require(last + 1 < a <= b <= H4.MAX_CPU_INDEX, "CPUSET_INVALID")
        count += b - a + 1
        require(count <= H4.MAX_CPUS, "CPUSET_INVALID")
        last = b
    return count


def _covers(level, selected):
    return all(any(a <= c <= b for a, b in level.cpus) for c in selected)


def _validate(sample, *, leaf):
    require(type(sample) is Sample and _number(sample.start_ns)
            and _number(sample.end_ns)
            and 0 < sample.end_ns - sample.start_ns <= MAX_SAMPLE_NS,
            "SAMPLE_WINDOW")
    require(type(sample.levels) is tuple and 1 <= len(sample.levels) <= 16
            and _number(sample.host_available_mib), "SAMPLE_INVALID")
    require(type(sample.host_pressure) is tuple and len(sample.host_pressure) == 2
            and all(type(p) is tuple and len(p) == 4 and all(_number(v) for v in p)
                    for p in sample.host_pressure), "PRESSURE_UNKNOWN")
    # Conservative proposed witness threshold: no displayed PSI or
    # observed stall delta. False negatives are HOLD, not unsafe success.
    require(all(p[:3] == (0, 0, 0) for p in sample.host_pressure),
            "HOST_PRESSURE")
    for level in sample.levels:
        require(type(level) is Level and type(level.identity) is tuple
                and len(level.identity) == 2
                and all(_number(v) and v > 0 for v in level.identity)
                and _number(level.current) and _number(level.tasks)
                and all(_limit(v) for v in (level.hard, level.high, level.pids_max))
                and type(level.events) is tuple and len(level.events) == len(EVENT_KEYS)
                and all(_number(v) for v in level.events), "LEVEL_INVALID")
        require(type(level.quota) is tuple and len(level.quota) == 2
                and _number(level.quota[1]) and 1 <= level.quota[1] <= 1_000_000
                and (level.quota[0] is None or
                     (_number(level.quota[0]) and level.quota[0] > 0)),
                "QUOTA_INVALID")
        _cpus(level.cpus)
    require(len({l.identity for l in sample.levels}) == len(sample.levels),
            "DUPLICATE_LEVEL")
    extras = (sample.peak, sample.swap, sample.swap_max, sample.cpu_usec, sample.populated)
    if leaf:
        require(all(_number(v) for v in extras) and sample.populated in (0, 1),
                "LEAF_COUNTER_MISSING")
    else:
        require(extras == (None,) * 5, "PARENT_SCOPE_INVALID")


def _limits(level, selected, memory_needed, tasks_needed):
    require(_covers(level, selected), "ANCESTOR_CPUSET")
    q, period = level.quota
    require(q is None or Fraction(q, period) >= 2, "ANCESTOR_CPU_QUOTA")
    require(all(v == "unlimited" or v - level.current >= memory_needed
                for v in (level.hard, level.high)), "ANCESTOR_MEMORY_HEADROOM")
    require(level.pids_max == "unlimited"
            or level.pids_max - level.tasks >= tasks_needed, "ANCESTOR_TASK_HEADROOM")


def preflight(sample, *, selected, now_ns):
    """Check observed parent resource evidence only; never launch authority."""
    _validate(sample, leaf=False)
    require(type(selected) is tuple and len(selected) == 2
            and all(_number(v) for v in selected) and selected[0] < selected[1],
            "CPU_SELECTION")
    require(_number(now_ns) and 0 <= now_ns - sample.end_ns <= MAX_SAMPLE_NS,
            "PREFLIGHT_STALE")
    require(sample.host_available_mib >= MIN_HOST_MIB, "HOST_HEADROOM")
    require(_cpus(sample.levels[-1].cpus) >= 4, "HOST_CPUSET")
    for level in sample.levels:
        _limits(level, selected, CAP + 4 * GIB, TASK_CAP)
    return "RESOURCE_PREFLIGHT_REFERENCE"


def _expected_identity(parent, expected_leaf):
    require(type(expected_leaf) is tuple and len(expected_leaf) == 2
            and all(_number(v) and v > 0 for v in expected_leaf)
            and expected_leaf not in tuple(l.identity for l in parent.levels),
            "LEAF_IDENTITY_INVALID")


def _scope_sample(parent, sample, selected, expected_leaf):
    _validate(sample, leaf=True)
    require(len(sample.levels) == len(parent.levels) + 1, "ANCESTRY_MISMATCH")
    for original, current in zip(parent.levels, sample.levels[:-1]):
        require((current.identity, current.hard, current.high, current.quota,
                 current.cpus, current.pids_max, current.events) ==
                (original.identity, original.hard, original.high, original.quota,
                 original.cpus, original.pids_max, original.events),
                "ANCESTOR_CHANGED")
    child = sample.levels[-1]
    require(child.identity == expected_leaf, "LEAF_CHANGED")
    expected_cpus = tuple((c, c) for c in selected)
    if selected[1] == selected[0] + 1:
        expected_cpus = ((selected[0], selected[1]),)
    require(child.hard == CAP and child.quota == QUOTA
            and child.cpus == expected_cpus and child.pids_max == TASK_CAP
            and sample.swap_max == 0, "LEAF_LIMIT_MISMATCH")
    require(child.high == "unlimited" or child.high >= CAP,
            "LEAF_HIGH_THRESHOLD")
    require(child.current <= CAP and child.current <= sample.peak <= CAP
            and sample.swap == 0 and child.tasks <= TASK_CAP
            and child.events == (0,) * len(EVENT_KEYS), "LEAF_RESOURCE_EVENT")
    require(sample.host_pressure == parent.host_pressure, "HOST_PRESSURE_CHANGED")
    # Conservative uncharged cap and margin, not physical release credit.
    remaining = CAP - child.current
    require(sample.host_available_mib * 1024**2 >= 4 * GIB + remaining,
            "HOST_MARGIN")
    for level in sample.levels[:-1]:
        _limits(level, selected, remaining + 4 * GIB, TASK_CAP - child.tasks)
    return child


def preflight_outer(parent, baseline, *, selected, now_ns, expected_leaf):
    """Check original empty retained group before launch, not permission.

    Runtime must establish fresh exclusive creation and independently
    pin mount/ancestry/identity. Nonzero observed peak/current is allowed;
    neither this function nor Reader resets any kernel counter.
    """
    preflight(parent, selected=selected, now_ns=now_ns)
    _expected_identity(parent, expected_leaf)
    outer = _scope_sample(parent, baseline, selected, expected_leaf)
    require(0 <= now_ns - baseline.end_ns <= MAX_SAMPLE_NS, "BASELINE_STALE")
    require(baseline.populated == 0 and outer.tasks == 0, "BASELINE_NOT_EMPTY")
    return "OUTER_RESOURCE_PREFLIGHT_REFERENCE"


def evaluate(parent, samples, *, selected, launch_ns, expected_leaf,
             scope="DIRECT", baseline=None):
    """Evaluate explicit accounting scope, not model demand or terminal proof.

    DIRECT preserves original child behavior. RETAINED_OUTER is selected
    before launch and requires original empty baseline from same pinned
    Reader. Runtime must bind scope/timing to original launch; no fallback.
    Inner effective limits, original terminal and confinement are separate.
    """
    require(type(scope) is str and scope in ("DIRECT", "RETAINED_OUTER"),
            "ACCOUNTING_SCOPE_INVALID")
    if scope == "DIRECT":
        require(baseline is None, "UNEXPECTED_OUTER_BASELINE")
        preflight(parent, selected=selected, now_ns=launch_ns)
        _expected_identity(parent, expected_leaf)
    else:
        preflight_outer(parent, baseline, selected=selected, now_ns=launch_ns,
                        expected_leaf=expected_leaf)
    require(type(samples) is tuple and 2 <= len(samples) <= MAX_SAMPLES,
            "SAMPLE_COUNT")
    previous = baseline
    max_charge = baseline.levels[-1].current if baseline is not None else 0
    minimum_host = min(parent.host_available_mib, baseline.host_available_mib) \
        if baseline is not None else parent.host_available_mib
    for index, sample in enumerate(samples):
        child = _scope_sample(parent, sample, selected, expected_leaf)
        require(launch_ns <= sample.start_ns < sample.end_ns <= launch_ns + MAX_NS,
                "WITNESS_WINDOW")
        require(0 <= sample.start_ns - (launch_ns if index == 0 else previous.end_ns)
                <= MAX_GAP_NS, "SAMPLE_GAP")
        if previous is not None:
            require(sample.peak >= previous.peak and sample.cpu_usec >= previous.cpu_usec
                    and child.high == previous.levels[-1].high, "COUNTER_REGRESSION")
        max_charge = max(max_charge, child.current)
        minimum_host = min(minimum_host, sample.host_available_mib)
        previous = sample
    require(all(s.populated == 1 and s.levels[-1].tasks > 0 for s in samples[:-1])
            and samples[-1].populated == 0 and samples[-1].levels[-1].tasks == 0,
            "QUIESCENCE_NOT_OBSERVED")
    return {
        "status": "RESOURCE_ENVELOPE_OBSERVED",
        "accounting_scope": scope,
        "samples": len(samples),
        "outer_baseline_observed": baseline is not None,
        "outer_baseline_current_bytes": baseline.levels[-1].current if baseline is not None else None,
        "outer_baseline_peak_bytes": baseline.peak if baseline is not None else None,
        "host_available_mib_sampled_min": minimum_host,
        "charged_memory_sampled_max_bytes": max_charge,
        "kernel_peak_reported_bytes": samples[-1].peak,
        "cpu_usage_usec_observed_delta": samples[-1].cpu_usec - (baseline.cpu_usec if baseline is not None else samples[0].cpu_usec),
        "terminal_verified": False,
        "device_isolation_verified": False,
        "measurement_coverage_complete": False,
        "resource_requirements_established": False,
        "resource_reserved": False,
        "safe_to_start_inference": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }
