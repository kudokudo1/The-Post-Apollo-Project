"""Task-local derived context recovery. No authoritative store or runtime.

Owner supplies independently current dependency clocks and selected route.
Never use cached records to establish permission, policy, or provenance.
"""
from dataclasses import dataclass
from hashlib import sha256
from threading import RLock

from context_first_tree_m2 import ContextRefusal, _key
from shared_context_b6r1 import TaskContext
from layered_hot_context_m7a import (
    HotRouteStamp, SelectedHotRecord, MAX_RECORDS, MAX_ASSEMBLY_BYTES,
    _generation, assemble_hot_context, KINDS,
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



# Fixed-public M7f witness. These are owner-local fixture values, not
# authenticated observations, durable knowledge or production wire types.
PUBLIC_CONTEXT = TaskContext("fixture-owner", "cherry", None, "task-a",
                             "ctx-a", 1, "INTERACTIVE")
PUBLIC_SCOPE = ("public-fixture-source", "fixture-compose",
                "public-fixture-recipient")


@dataclass(frozen=True, slots=True)
class PublicVersion:
    source: str
    record_id: str
    kind: str
    revision: int
    record_generation: int
    commitment: bytes
    active: bool

    def __post_init__(self):
        _key(self.source)
        _key(self.record_id)
        if (type(self.kind) is not str or self.kind not in KINDS
                or type(self.active) is not bool
                or type(self.commitment) is not bytes or len(self.commitment) != 32):
            raise ContextRefusal("STICKY_VERSION_INVALID")
        for clock in (self.revision, self.record_generation):
            _generation(clock)
            if clock == 0:
                raise ContextRefusal("STICKY_VERSION_INVALID")


@dataclass(frozen=True, slots=True)
class PublicSelection:
    route: HotRouteStamp
    source: str
    purpose: str
    recipient: str
    versions: tuple

    def __post_init__(self):
        for key in (self.source, self.purpose, self.recipient):
            _key(key)
        if (type(self.route) is not HotRouteStamp
                or type(self.versions) is not tuple
                or len(self.versions) > MAX_RECORDS
                or any(type(v) is not PublicVersion for v in self.versions)):
            raise ContextRefusal("STICKY_VERSION_SELECTION")
        ids = self.route.user_record_ids + self.route.operational_record_ids
        if tuple(v.record_id for v in self.versions) != ids:
            raise ContextRefusal("STICKY_VERSION_SELECTION")
        for i, v in enumerate(self.versions):
            user = i < len(self.route.user_record_ids)
            clock = (self.route.user_context_generation if user
                     else self.route.operational_generation)
            if (v.source != self.source or not v.active
                    or v.record_generation > clock
                    or (v.kind == "operational-learning") == user):
                raise ContextRefusal("STICKY_VERSION_SCOPE")


@dataclass(frozen=True, slots=True)
class PublicUse:
    selection: PublicSelection
    eligible: tuple
    revoked: tuple = ()

    def __post_init__(self):
        if type(self.selection) is not PublicSelection:
            raise ContextRefusal("STICKY_VERSION_SELECTION")
        for values in (self.eligible, self.revoked):
            if (type(values) is not tuple or len(values) > MAX_RECORDS
                    or any(type(v) is not PublicVersion for v in values)
                    or len(set(values)) != len(values)
                    or any(v.source != self.selection.source for v in values)):
                raise ContextRefusal("STICKY_VERSION_USE")
        if any(v not in self.selection.versions for v in self.eligible):
            raise ContextRefusal("STICKY_VERSION_USE")


@dataclass(frozen=True, slots=True)
class PublicEntry:
    version: PublicVersion
    record: SelectedHotRecord

    def __post_init__(self):
        v, rec = self.version, self.record
        if (type(v) is not PublicVersion or type(rec) is not SelectedHotRecord
                or not v.active or not rec.active
                or rec.record_id != v.record_id or rec.kind != v.kind
                or sha256(rec.text.encode("utf-8")).digest() != v.commitment):
            raise ContextRefusal("STICKY_VERSION_CONTENT")


@dataclass(frozen=True, slots=True)
class PublicLookup:
    selection: PublicSelection
    entries: tuple
    missing: tuple

    @property
    def complete(self):
        return not self.missing


class TaskStickyContext:
    """Bounded volatile cache for one exact TaskContext lifetime.

    At most MAX_RECORDS immutable records in total, at most MAX_RECORD_BYTES
    UTF-8 content per record (M7a). No per-Tree shared mutable selections.
    All operations are synchronous under a local lock; no IO/callbacks.
    """
    def __init__(self, context, *, mode="legacy"):
        if type(mode) is not str or mode not in ("legacy", "public-versioned"):
            raise ContextRefusal("STICKY_MODE")
        if mode == "public-versioned" and context != PUBLIC_CONTEXT:
            raise ContextRefusal("STICKY_VERSION_SCOPE")
        self._mode = mode
        self._policy_floor = self._user_floor = self._operational_floor = None
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

    def _legacy(self):
        if self._mode != "legacy":
            raise ContextRefusal("STICKY_MODE")

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
            self._legacy()
            self._observe(current)

    def install_route(self, requested, *, current, dependencies):
        """Explicit re-selection. A new route never inherits old selections."""
        with self._lock:
            self._legacy()
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
        self._legacy()
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


    def _versioned(self, requested, current, dependencies, use, *, install=False):
        # Validate exact independent references before any invalidation.
        # No caller callback or external read while the lock is held.
        if self._mode != "public-versioned":
            raise ContextRefusal("STICKY_MODE")
        if self._closed:
            raise ContextRefusal("STICKY_CLOSED")
        if (type(requested) is not PublicSelection
                or type(current) is not PublicSelection
                or type(use) is not PublicUse or type(dependencies) is not HotDependencies
                or requested != current or use.selection != current
                or current.route.context != self._context
                or (current.source, current.purpose, current.recipient) != PUBLIC_SCOPE
                or HotDependencies.from_route(current.route) != dependencies):
            raise ContextRefusal("STICKY_VERSION_SCOPE")
        old = self._deps
        if old is not None and any(a < b for a, b in zip(dependencies.clocks, old.clocks)):
            raise ContextRefusal("HOT_CLOCK_REGRESSED")
        # An old request must not destructively replace a newer installed
        # route at identical clocks. Changes require a new observed input
        # or other dependency clock. Same-clock contradiction of a retained
        # version is handled below when explicitly selected on a newer input.
        if self._route is not None and old == dependencies and self._route != current:
            raise ContextRefusal("HOT_ROUTE_CHANGED")
        route_changed = old != dependencies or self._route != current
        self._observe(dependencies)
        route = current.route
        if self._policy_floor is not None and route.policy_generation <= self._policy_floor:
            raise ContextRefusal("STICKY_VERSION_FLOOR")
        # A valid current revocation must fence both pools even if a
        # separate domain or shedding floor already blocks selection.
        if use.revoked:
            self._user.clear()
            self._operational.clear()
            self._route = None
            self._policy_floor = route.policy_generation
            raise ContextRefusal("STICKY_VERSION_REVOKED")
        # A current explicit revocation is a destructive observation, not
        # permission to reuse a route. Process it before refusing a missing
        # or retired installation. Ordinary lookups still require selection.
        if not install and route_changed:
            raise ContextRefusal("HOT_ROUTE_CHANGED")
        if any(floor is not None and value <= floor for floor, value in (
                (self._user_floor, route.user_context_generation),
                (self._operational_floor, route.operational_generation),
                (self._shed_input_floor, route.input_generation))):
            raise ContextRefusal("STICKY_VERSION_FLOOR")
        if use.eligible != current.versions:
            # Missing/unknown is not a revocation. No selected body leaves
            # this call; no policy floor is invented.
            raise ContextRefusal("STICKY_VERSION_USE")
        for v in current.versions:
            operational = v.kind == "operational-learning"
            pool = self._operational if operational else self._user
            other = self._user if operational else self._operational
            old_entry = pool.get(v.record_id)
            # A cross-domain identity contradiction cannot silently relabel
            # an entry; retire both involved domains with bounded floors.
            if v.record_id in other:
                self._user.clear()
                self._operational.clear()
                self._user_floor = route.user_context_generation
                self._operational_floor = route.operational_generation
                self._route = None
                raise ContextRefusal("STICKY_VERSION_CONFLICT")
            if old_entry is not None and old_entry.version != v:
                pool.clear()
                if operational:
                    self._operational_floor = route.operational_generation
                else:
                    self._user_floor = route.user_context_generation
                self._route = None
                raise ContextRefusal("STICKY_VERSION_CONFLICT")

    def install_versioned(self, requested, *, current, dependencies, use):
        with self._lock:
            self._versioned(requested, current, dependencies, use, install=True)
            self._route = current

    def remember_versioned(self, requested, *, current, dependencies, use, entries=()):
        with self._lock:
            self._versioned(requested, current, dependencies, use)
            if (type(entries) is not tuple or len(entries) > MAX_RECORDS
                    or any(type(e) is not PublicEntry for e in entries)
                    or len({e.version.record_id for e in entries}) != len(entries)):
                raise ContextRefusal("STICKY_VERSION_SELECTION")
            route = current.route
            candidates = (dict(self._user), dict(self._operational))
            for entry in entries:
                v, rec = entry.version, entry.record
                if v not in current.versions:
                    raise ContextRefusal("STICKY_VERSION_SELECTION")
                operational = v.kind == "operational-learning"
                domain = (route.operational_generation if operational
                          else route.user_context_generation)
                if (rec.principal_key != self._context.principal_key
                        or rec.tree_key != self._context.tree_key
                        or rec.generation != domain
                        or sha256(rec.text.encode("utf-8")).digest() != v.commitment):
                    raise ContextRefusal("STICKY_VERSION_CONTENT")
                pool = candidates[int(operational)]
                previous = pool.get(v.record_id)
                if previous is not None and previous != entry:
                    raise ContextRefusal("STICKY_VERSION_CONFLICT")
                pool[v.record_id] = entry
            for pool, ids in zip(candidates, (route.user_record_ids,
                                             route.operational_record_ids)):
                for key in tuple(pool):
                    if sum(map(len, candidates)) <= MAX_RECORDS:
                        break
                    if key not in ids:
                        del pool[key]
            if sum(map(len, candidates)) > MAX_RECORDS:
                raise ContextRefusal("STICKY_CAPACITY")
            self._user, self._operational = candidates

    def lookup_versioned(self, requested, *, current, dependencies, use):
        with self._lock:
            self._versioned(requested, current, dependencies, use)
            found, missing = [], []
            for v in current.versions:
                pool = self._operational if v.kind == "operational-learning" else self._user
                entry = pool.get(v.record_id)
                if entry is None:
                    missing.append(v)
                else:
                    found.append(entry)
            return PublicLookup(current, () if missing else tuple(found), tuple(missing))

    def assemble_versioned(self, requested, *, current, dependencies, use,
                           final_use, max_bytes=MAX_ASSEMBLY_BYTES):
        with self._lock:
            result = self.lookup_versioned(requested, current=current,
                                            dependencies=dependencies, use=use)
            if not result.complete:
                raise ContextRefusal("STICKY_RECORDS_MISSING")
            self._versioned(requested, current, dependencies, final_use)
            split = len(current.route.user_record_ids)
            records = tuple(e.record for e in result.entries)
            # Preserve the exact selected versions alongside assembly.
            return result, assemble_hot_context(current.route, current=current.route,
                user_records=records[:split], operational_records=records[split:],
                max_bytes=max_bytes)

    def shed_versioned(self, requested, *, current, dependencies, use,
                       drop_user=False, drop_operational=False):
        with self._lock:
            if (type(drop_user) is not bool or type(drop_operational) is not bool
                    or not (drop_user or drop_operational)):
                raise ContextRefusal("INVALID_STICKY_SHED")
            self._versioned(requested, current, dependencies, use)
            if drop_user:
                self._user.clear()
            if drop_operational:
                self._operational.clear()
            self._shed_input_floor = current.route.input_generation
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
