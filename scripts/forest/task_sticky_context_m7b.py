"""Task-local derived context recovery. No authoritative store or runtime.

Owner supplies independently current dependency clocks and selected route.
Never use cached records to establish permission, policy, or provenance.
"""
from dataclasses import dataclass
from threading import RLock

from context_first_tree_m2 import ContextRefusal
from shared_context_b6r1 import TaskContext
from layered_hot_context_m7a import (
    HotRouteStamp, SelectedHotRecord, MAX_RECORDS, MAX_ASSEMBLY_BYTES,
    _generation, assemble_hot_context,
)


@dataclass(frozen=True, slots=True)
class HotDependencies:
    context: TaskContext
    input_generation: int
    policy_generation: int
    user_context_generation: int
    operational_generation: int

    def __post_init__(self):
        if type(self.context) is not TaskContext:
            raise ContextRefusal("INVALID_HOT_CONTEXT")
        for value in self.clocks:
            _generation(value)

    @property
    def clocks(self):
        return (self.input_generation, self.policy_generation,
                self.user_context_generation, self.operational_generation)

    @classmethod
    def from_route(cls, route):
        if type(route) is not HotRouteStamp:
            raise ContextRefusal("INVALID_HOT_ROUTE")
        return cls(route.context, route.input_generation, route.policy_generation,
                   route.user_context_generation, route.operational_generation)


@dataclass(frozen=True, slots=True)
class StickyLookup:
    user_records: tuple
    operational_records: tuple
    missing_user_ids: tuple
    missing_operational_ids: tuple

    @property
    def complete(self):
        return not (self.missing_user_ids or self.missing_operational_ids)


class TaskStickyContext:
    """Bounded volatile cache for one exact TaskContext lifetime.

    At most MAX_RECORDS immutable records in total, at most MAX_RECORD_BYTES
    UTF-8 content per record (M7a). No per-Tree shared mutable selections.
    All operations are synchronous under a local lock; no IO/callbacks.
    """
    def __init__(self, context):
        if type(context) is not TaskContext:
            raise ContextRefusal("INVALID_HOT_CONTEXT")
        self._context = context
        self._lock = RLock()
        self._deps = None
        self._route = None
        self._user = {}
        self._operational = {}
        self._closed = False
        self._shed_input_floor = None

    def _observe(self, current):
        if self._closed:
            raise ContextRefusal("STICKY_CLOSED")
        if type(current) is not HotDependencies or current.context != self._context:
            raise ContextRefusal("HOT_CONTEXT_CHANGED")
        old = self._deps
        if old is not None and any(a < b for a, b in zip(current.clocks, old.clocks)):
            # Refuse stale observations; do not replace or revive newer state.
            raise ContextRefusal("HOT_CLOCK_REGRESSED")
        if old != current:
            self._route = None
            if old is not None:
                if (current.policy_generation != old.policy_generation
                        or current.user_context_generation != old.user_context_generation):
                    self._user.clear()
                if (current.policy_generation != old.policy_generation
                        or current.operational_generation != old.operational_generation):
                    self._operational.clear()
            self._deps = current

    def observe(self, *, current):
        """Independent observation; meaningful input invalidates selection."""
        with self._lock:
            self._observe(current)

    def install_route(self, requested, *, current, dependencies):
        """Explicit re-selection. A new route never inherits old selections."""
        with self._lock:
            self._observe(dependencies)
            if (type(requested) is not HotRouteStamp or type(current) is not HotRouteStamp
                    or requested != current
                    or HotDependencies.from_route(current) != self._deps):
                raise ContextRefusal("HOT_ROUTE_CHANGED")
            if (self._shed_input_floor is not None
                    and current.input_generation <= self._shed_input_floor):
                raise ContextRefusal("STICKY_SHED_RESELECTION_REQUIRED")
            self._route = current

    def _require(self, requested, current, dependencies):
        self._observe(dependencies)
        if (self._route is None or type(requested) is not HotRouteStamp
                or type(current) is not HotRouteStamp
                or requested != current or current != self._route
                or HotDependencies.from_route(current) != self._deps):
            raise ContextRefusal("HOT_ROUTE_CHANGED")

    def remember(self, requested, *, current, dependencies,
                 user_records=(), operational_records=()):
        """Cache only current selected records; validate before any insertion.

        Same-generation conflicting content refuses rather than replacing an
        immutable snapshot. Unselected old records may be evicted to stay
        bounded, never selected records. No automatic load on miss.
        """
        with self._lock:
            self._require(requested, current, dependencies)
            candidates = (dict(self._user), dict(self._operational))
            selected = (current.user_record_ids, current.operational_record_ids)
            for records, pool, ids, generation, operational in (
                (user_records, candidates[0], selected[0],
                 current.user_context_generation, False),
                (operational_records, candidates[1], selected[1],
                 current.operational_generation, True),
            ):
                if (type(records) is not tuple or len(records) > MAX_RECORDS
                        or any(type(r) is not SelectedHotRecord for r in records)
                        or len({r.record_id for r in records}) != len(records)):
                    raise ContextRefusal("INVALID_HOT_SELECTION")
                for record in records:
                    if (record.record_id not in ids or not record.active
                            or record.principal_key != self._context.principal_key
                            or record.tree_key != self._context.tree_key
                            or record.generation != generation
                            or (record.kind == "operational-learning") != operational):
                        raise ContextRefusal("HOT_RECORD_SCOPE_CHANGED")
                    old = pool.get(record.record_id)
                    if old is not None and old != record:
                        raise ContextRefusal("HOT_RECORD_CONFLICT")
                    pool[record.record_id] = record
            # Bound storage independently of number of successive inputs.
            for pool, ids in zip(candidates, selected):
                for key in tuple(pool):
                    if sum(map(len, candidates)) <= MAX_RECORDS:
                        break
                    if key not in ids:
                        del pool[key]
            if sum(map(len, candidates)) > MAX_RECORDS:
                raise ContextRefusal("STICKY_CAPACITY")
            self._user, self._operational = candidates

    def lookup(self, requested, *, current, dependencies):
        with self._lock:
            self._require(requested, current, dependencies)
            uids, oids = current.user_record_ids, current.operational_record_ids
            return StickyLookup(tuple(self._user[k] for k in uids if k in self._user),
                tuple(self._operational[k] for k in oids if k in self._operational),
                tuple(k for k in uids if k not in self._user),
                tuple(k for k in oids if k not in self._operational))

    def assemble(self, requested, *, current, dependencies,
                 max_bytes=MAX_ASSEMBLY_BYTES):
        with self._lock:
            result = self.lookup(requested, current=current, dependencies=dependencies)
            if not result.complete:
                raise ContextRefusal("STICKY_RECORDS_MISSING")
            return assemble_hot_context(requested, current=current,
                user_records=result.user_records,
                operational_records=result.operational_records, max_bytes=max_bytes)

    def shed(self, requested, *, current, dependencies,
             drop_user=False, drop_operational=False):
        """Discard selected derived domains, not durable knowledge or RAM custody.

        Requires the exact currently installed route. A strictly newer
        independently observed input is needed before any further selection.
        Retained records are never implicitly selected or authorized.
        """
        with self._lock:
            if (type(drop_user) is not bool or type(drop_operational) is not bool
                    or not (drop_user or drop_operational)):
                raise ContextRefusal("INVALID_STICKY_SHED")
            self._require(requested, current, dependencies)
            if drop_user:
                self._user.clear()
            if drop_operational:
                self._operational.clear()
            self._shed_input_floor = current.input_generation
            self._route = None

    def counts(self):
        """Owner-local counts only; no record content or authority."""
        with self._lock:
            return (len(self._user), len(self._operational))

    def close(self):
        """Drop derived state only, permanently close this cache lifetime."""
        with self._lock:
            self._closed = True
            self._route = self._deps = None
            self._user.clear()
            self._operational.clear()
