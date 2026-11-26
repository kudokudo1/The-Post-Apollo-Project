"""M7d-b: fixed-public, disposable exact-version resolution witness.

This file is deliberately test-only. No protected source, permission API,
persistence, callback-driven reader, cache admission, or provider dispatch.
All body bytes come from constants below. Owner observations are fixtures,
not authenticated policy or atomic revocation/read custody.
"""
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from context_first_tree_m2 import ContextRefusal
from shared_context_b6r1 import TaskContext
from layered_hot_context_m7a import (
    HotRouteStamp, SelectedHotRecord, assemble_hot_context,
    MAX_RECORDS, MAX_RECORD_BYTES, MAX_ASSEMBLY_BYTES, MAX_GENERATION, KINDS,
)
from task_sticky_context_m7b import TaskStickyContext, HotDependencies

SOURCE = "public-fixture-source"
PURPOSE = "fixture-compose"
RECIPIENT = "public-fixture-recipient"
CONTEXT = TaskContext("fixture-owner", "cherry", None, "task-a", "ctx-a",
                      1, "INTERACTIVE")
MAX_METADATA = 64

# Literal public content only; no caller-supplied body or filesystem lookup.
BODIES = (
    ("preference", 1, "Public fixture: original preference."),
    ("preference", 2, "Public fixture: revised preference."),
    ("lesson", 1, "Public fixture: verify before changes."),
    ("unselected", 1, "Public fixture: not selected."),
    ("large-a", 1, "A" * MAX_RECORD_BYTES),
    ("large-b", 1, "B" * MAX_RECORD_BYTES),
    ("large-c", 1, "C" * MAX_RECORD_BYTES),
    ("large-d", 1, "D" * MAX_RECORD_BYTES),
    ("oversize", 1, "E" * (MAX_RECORD_BYTES + 1)),
)


def refusal(reason):
    raise ContextRefusal("M7D_" + reason)


def digest(body):
    return sha256(body.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Version:
    source: str
    record_id: str
    kind: str
    revision: int
    record_generation: int
    commitment: str
    active: bool


@dataclass(frozen=True, slots=True)
class Selection:
    route: HotRouteStamp
    source: str
    purpose: str
    recipient: str
    versions: tuple


@dataclass(frozen=True, slots=True)
class Observation:
    selection: Selection
    metadata_visible: bool
    use_versions: tuple
    revoked: tuple = ()


@dataclass(frozen=True, slots=True)
class Resolution:
    selection: Selection
    assembly: object


def version(record_id, revision, kind, generation):
    # Build fixed fixture metadata commitments from known public constants,
    # before the trial starts; this is not an authorized source read.
    body = next(body for rid, rev, body in BODIES
                if (rid, rev) == (record_id, revision))
    return Version(SOURCE, record_id, kind, revision, generation,
                   digest(body), True)


CATALOG = (
    version("preference", 1, "user-preference", 1),
    version("preference", 2, "user-preference", 3),
    version("lesson", 1, "operational-learning", 2),
    version("unselected", 1, "current-context", 1),
) + tuple(version("large-" + c, 1, "current-context", 3) for c in "abcd") + (
    version("oversize", 1, "current-context", 3),
)


class FixtureOwner:
    """Independent fixture observation and read witness, not authority."""
    def __init__(self, state, catalog=CATALOG, after_first_read=None):
        self.state = state
        self.catalog = catalog
        self.after_first_read = after_first_read
        self.metadata_reads = 0
        self.body_reads = []

    def observe(self):
        return self.state

    def metadata(self):
        self.metadata_reads += 1
        return self.catalog

    def body(self, item):
        self.body_reads.append((item.record_id, item.revision))
        body = next((body for rid, rev, body in BODIES
                     if (rid, rev) == (item.record_id, item.revision)), None)
        if len(self.body_reads) == 1 and self.after_first_read is not None:
            self.state = self.after_first_read
        return body


def valid_version(item):
    if (type(item) is not Version or type(item.source) is not str
            or item.source != SOURCE
            or type(item.record_id) is not str
            or not 1 <= len(item.record_id) <= 128
            or not item.record_id.isascii()
            or type(item.kind) is not str or item.kind not in KINDS
            or type(item.revision) is not int
            or not 1 <= item.revision <= MAX_GENERATION
            or type(item.record_generation) is not int
            or not 1 <= item.record_generation <= MAX_GENERATION
            or type(item.commitment) is not str or len(item.commitment) != 64
            or any(c not in "0123456789abcdef" for c in item.commitment)
            or type(item.active) is not bool):
        refusal("INVALID_VERSION")


def resolve(requested, owner, *, max_bytes=MAX_ASSEMBLY_BYTES):
    """Select exact public revisions, read only after full metadata checks.

    The complete resolution carries exact versions separately from M7a
    snapshot generation. No insertion into the version-blind M7b cache.
    """
    if type(owner) is not FixtureOwner or type(requested) is not Selection:
        refusal("INVALID_FIXTURE")
    if (type(requested.route) is not HotRouteStamp
            or requested.route.context != CONTEXT
            or requested.source != SOURCE or requested.purpose != PURPOSE
            or requested.recipient != RECIPIENT
            or any(type(v) is not str for v in
                   (requested.source, requested.purpose, requested.recipient))):
        refusal("SCOPE_CHANGED")
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_ASSEMBLY_BYTES:
        refusal("INVALID_BUDGET")
    initial = owner.observe()
    if (type(initial) is not Observation
            or initial.selection != requested
            or type(initial.metadata_visible) is not bool
            or type(initial.use_versions) is not tuple
            or type(initial.revoked) is not tuple):
        refusal("CURRENTNESS_CHANGED")

    def recheck():
        current = owner.observe()
        if type(current) is not Observation or current != initial:
            refusal("CURRENTNESS_CHANGED")

    route = requested.route
    ids = route.user_record_ids + route.operational_record_ids
    versions = requested.versions
    if (type(versions) is not tuple or len(versions) != len(ids)
            or len(versions) > MAX_RECORDS):
        refusal("INVALID_SELECTION")
    for item in versions + initial.use_versions + initial.revoked:
        valid_version(item)
    if (len(initial.use_versions) > MAX_RECORDS or len(initial.revoked) > MAX_METADATA
            or len(set(initial.use_versions)) != len(initial.use_versions)
            or len(set(initial.revoked)) != len(initial.revoked)
            or tuple(v.record_id for v in versions) != ids):
        refusal("INVALID_SELECTION")
    # Empty selection still checks independently held currentness; no scan.
    if not versions:
        recheck()
        result = assemble_hot_context(route, current=route, max_bytes=max_bytes)
        recheck()
        return Resolution(requested, result)
    if not initial.metadata_visible:
        refusal("METADATA_NOT_ELIGIBLE")
    recheck()
    catalog = owner.metadata()
    if type(catalog) is not tuple or len(catalog) > MAX_METADATA:
        refusal("INVALID_METADATA")
    for item in catalog:
        valid_version(item)
    keys = [(v.record_id, v.revision) for v in catalog]
    if len(set(keys)) != len(keys):
        refusal("AMBIGUOUS_VERSION")

    # Validate every selected revision and its separate current-use fixture
    # reference before the first body access, not one record at a time.
    for i, chosen in enumerate(versions):
        operational = i >= len(route.user_record_ids)
        ceiling = route.operational_generation if operational else route.user_context_generation
        if ((chosen.kind == "operational-learning") != operational
                or chosen.record_generation > ceiling or not chosen.active
                or chosen in initial.revoked):
            refusal("VERSION_NOT_ELIGIBLE")
        candidates = [v for v in catalog if v.record_id == chosen.record_id]
        if any(v.kind != chosen.kind for v in candidates):
            refusal("DOMAIN_CHANGED")
        visible = [v for v in candidates if v.record_generation <= ceiling]
        if not visible:
            refusal("VERSION_MISSING")
        # Distinct revisions at one generation are not assumed ordered.
        if len({v.record_generation for v in visible}) != len(visible):
            refusal("AMBIGUOUS_VERSION")
        ordered = sorted(visible, key=lambda v: v.record_generation)
        if any(a.revision >= b.revision for a, b in zip(ordered, ordered[1:])):
            refusal("AMBIGUOUS_VERSION")
        if ordered[-1] != chosen:
            refusal("VERSION_CHANGED")
        if chosen not in initial.use_versions:
            refusal("USE_NOT_ELIGIBLE")
    recheck()
    records = []
    for i, chosen in enumerate(versions):
        recheck()
        body = owner.body(chosen)
        recheck()
        if type(body) is not str or len(body.encode("utf-8")) > MAX_RECORD_BYTES:
            refusal("INVALID_BODY")
        if digest(body) != chosen.commitment:
            refusal("COMMITMENT_CHANGED")
        ceiling = (route.user_context_generation if i < len(route.user_record_ids)
                   else route.operational_generation)
        records.append(SelectedHotRecord(
            route.context.principal_key, route.context.tree_key, chosen.record_id,
            chosen.kind, ceiling, True, body))
    recheck()
    split = len(route.user_record_ids)
    result = assemble_hot_context(route, current=route,
                                  user_records=tuple(records[:split]),
                                  operational_records=tuple(records[split:]),
                                  max_bytes=max_bytes)
    recheck()
    return Resolution(requested, result)


class VersionResolutionTests(unittest.TestCase):
    def setUp(self):
        self.route = HotRouteStamp(CONTEXT, 1, 2, 3, 2, ("preference",), ("lesson",))
        self.plan = Selection(self.route, SOURCE, PURPOSE, RECIPIENT,
                              (CATALOG[1], CATALOG[2]))
        self.state = Observation(self.plan, True, self.plan.versions)

    def owner(self, plan=None, **kwargs):
        plan = self.plan if plan is None else plan
        return FixtureOwner(Observation(plan, True, plan.versions), **kwargs)

    def refuse(self, owner, plan=None, code=None, reads=()):
        with self.assertRaises(ContextRefusal) as caught:
            resolve(self.plan if plan is None else plan, owner)
        if code:
            self.assertEqual(str(caught.exception), "M7D_" + code)
        self.assertEqual(owner.body_reads, list(reads))

    def test_exact_revision_not_snapshot_generation_and_unselected_never_read(self):
        owner = self.owner()
        result = resolve(self.plan, owner)
        self.assertEqual(owner.body_reads, [("preference", 2), ("lesson", 1)])
        self.assertEqual(result.selection.versions, self.plan.versions)
        self.assertEqual(result.assembly.record_ids, ("preference", "lesson"))
        self.assertIn("revised preference", result.assembly.reference_text)
        self.assertNotIn("original preference", result.assembly.reference_text)
        self.assertNotIn("not selected", result.assembly.reference_text)
        self.assertEqual(result.assembly.byte_count,
                         len(result.assembly.reference_text.encode("utf-8")))

    def test_old_revision_not_fallback_but_visible_at_old_pinned_snapshot(self):
        old = replace(self.plan, versions=(CATALOG[0], CATALOG[2]))
        self.refuse(self.owner(old), old, "VERSION_CHANGED")
        historical = replace(old, route=replace(self.route, user_context_generation=1))
        # Only a separately current historical fixture selection can resolve.
        owner = self.owner(historical)
        self.assertIn("original preference", resolve(historical, owner).assembly.reference_text)
        self.assertEqual(owner.body_reads[0], ("preference", 1))
        self.refuse(self.owner(), historical, "CURRENTNESS_CHANGED")

    def test_future_revision_and_wrong_domain(self):
        future = replace(self.plan, route=replace(self.route, user_context_generation=2))
        self.refuse(self.owner(future), future, "VERSION_NOT_ELIGIBLE")
        bad = replace(self.plan, versions=(replace(CATALOG[1], kind="operational-learning"),
                                          CATALOG[2]))
        self.refuse(self.owner(bad), bad, "VERSION_NOT_ELIGIBLE")

    def test_wrong_context_and_recipient_source_purpose(self):
        for ctx in (replace(CONTEXT, task_id="task-b"), replace(CONTEXT, clone_key="clone-a"),
                    replace(CONTEXT, tree_key="maple"), replace(CONTEXT, principal_key="other"),
                    replace(CONTEXT, execution_context_id="ctx-b"), replace(CONTEXT, generation=2)):
            bad = replace(self.plan, route=replace(self.route, context=ctx))
            self.refuse(self.owner(bad), bad, "SCOPE_CHANGED")
        for field in ("source", "recipient", "purpose"):
            bad = replace(self.plan, **{field: "other"})
            self.refuse(self.owner(bad), bad, "SCOPE_CHANGED")

    def test_wrong_policy_or_input_even_empty_selection(self):
        for field in ("policy_generation", "input_generation", "operational_generation"):
            stale = replace(self.plan, route=replace(self.route, **{field: 9}))
            self.refuse(self.owner(), stale, "CURRENTNESS_CHANGED")
        empty = replace(self.plan, route=replace(self.route, user_record_ids=(),
                                               operational_record_ids=()), versions=())
        self.refuse(self.owner(), empty, "CURRENTNESS_CHANGED")
        owner = self.owner(empty)
        self.assertEqual(resolve(empty, owner).assembly.reference_text, "")
        self.assertEqual((owner.metadata_reads, owner.body_reads), (0, []))

    def test_duplicate_missing_and_ambiguous_versions(self):
        self.refuse(self.owner(catalog=CATALOG + (CATALOG[1],)), code="AMBIGUOUS_VERSION")
        ambiguous = replace(CATALOG[0], revision=3, record_generation=3)
        self.refuse(self.owner(catalog=CATALOG + (ambiguous,)), code="AMBIGUOUS_VERSION")
        self.refuse(self.owner(catalog=tuple(v for v in CATALOG if v.record_id != "lesson")),
                    code="VERSION_MISSING")
        self.refuse(self.owner(catalog=CATALOG[:1] + CATALOG[2:]), code="VERSION_CHANGED")
        bad = replace(self.plan, versions=(CATALOG[1], CATALOG[1]))
        self.refuse(self.owner(bad), bad, "INVALID_SELECTION")

    def test_metadata_visibility_is_not_read_use(self):
        owner = FixtureOwner(replace(self.state, metadata_visible=False))
        self.refuse(owner, code="METADATA_NOT_ELIGIBLE")
        self.assertEqual(owner.metadata_reads, 0)
        # Missing permission for the SECOND selected record prevents ALL reads.
        owner = FixtureOwner(replace(self.state, use_versions=(CATALOG[1],)))
        self.refuse(owner, code="USE_NOT_ELIGIBLE")
        self.assertEqual(owner.metadata_reads, 1)

    def test_revoked_and_inactive_no_fallback(self):
        self.refuse(FixtureOwner(replace(self.state, revoked=(CATALOG[2],))),
                    code="VERSION_NOT_ELIGIBLE")
        inactive = replace(CATALOG[2], active=False)
        bad = replace(self.plan, versions=(CATALOG[1], inactive))
        self.refuse(self.owner(bad, catalog=CATALOG[:2] + (inactive,) + CATALOG[3:]),
                    bad, "VERSION_NOT_ELIGIBLE")

    def test_commitment_mismatch_metadata_and_actual_fixture_body(self):
        altered = replace(CATALOG[2], commitment="0"*64)
        bad = replace(self.plan, versions=(CATALOG[1], altered))
        self.refuse(self.owner(bad), bad, "VERSION_CHANGED")
        owner = self.owner(bad, catalog=CATALOG[:2] + (altered,) + CATALOG[3:])
        self.refuse(owner, bad, "COMMITMENT_CHANGED",
                    reads=(("preference", 2), ("lesson", 1)))

    def test_currentness_changes_during_body_read_discard_result(self):
        changed = replace(self.state, use_versions=())
        self.refuse(self.owner(after_first_read=changed), code="CURRENTNESS_CHANGED",
                    reads=(("preference", 2),))
        changed = replace(self.state, selection=replace(self.plan, recipient="other"))
        self.refuse(self.owner(after_first_read=changed), code="CURRENTNESS_CHANGED",
                    reads=(("preference", 2),))

    def test_body_and_assembly_limits_no_partial_result(self):
        oversize = CATALOG[-1]
        bad = replace(self.plan, route=replace(self.route, user_record_ids=("oversize",),
                                              operational_record_ids=()), versions=(oversize,))
        self.refuse(self.owner(bad), bad, "INVALID_BODY", reads=(("oversize", 1),))
        large = CATALOG[4:8]
        bad = replace(self.plan, route=replace(self.route,
            user_record_ids=tuple(v.record_id for v in large), operational_record_ids=()),
            versions=large)
        owner = self.owner(bad)
        with self.assertRaisesRegex(ContextRefusal, "HOT_BUDGET_EXCEEDED"):
            resolve(bad, owner)
        self.assertEqual(len(owner.body_reads), 4)
        good = resolve(self.plan, self.owner())
        with self.assertRaisesRegex(ContextRefusal, "HOT_BUDGET_EXCEEDED"):
            resolve(self.plan, self.owner(), max_bytes=good.assembly.byte_count-1)
        self.assertEqual(resolve(self.plan, self.owner(),
                                 max_bytes=good.assembly.byte_count), good)

    def test_no_cache_admission_on_success_or_refusal(self):
        cache = TaskStickyContext(CONTEXT)
        deps = HotDependencies.from_route(self.route)
        cache.install_route(self.route, current=self.route, dependencies=deps)
        cache.remember(self.route, current=self.route, dependencies=deps,
                       user_records=(SelectedHotRecord("fixture-owner", "cherry",
                           "preference", "user-preference", 3, True, "Existing fixture"),))
        before = cache.lookup(self.route, current=self.route, dependencies=deps)
        resolve(self.plan, self.owner())
        self.refuse(FixtureOwner(replace(self.state, use_versions=())), code="USE_NOT_ELIGIBLE")
        self.assertEqual(cache.lookup(self.route, current=self.route, dependencies=deps), before)
        self.assertEqual(cache.counts(), (1, 0))



# M7i-b: a separate fixed-public metadata-only witness. No real producer,
# decoder, permission, body reader, store, cache or downstream invocation.
WARM_MAX_SIGNALS = 32
WARM_MAX_SIGNAL_BYTES = 4096
WARM_MAX_FIELD = 128
WARM_MAX_PROVENANCE = 256
WARM_MAX_ROWS = 128
WARM_MAX_ASSOCIATIONS = 512
WARM_MAX_COMPARISONS = 16384
WARM_MAX_PROJECTION_BYTES = 65536
WARM_USER_KINDS = KINDS - {"operational-learning"}


@dataclass(frozen=True, slots=True)
class WarmBinding:
    context: TaskContext
    input_generation: int
    input_commitment: str
    policy_generation: int
    revocation_generation: int
    domain_generation: int
    source: str
    domain: str
    purpose: str
    recipient: str
    signals: tuple


@dataclass(frozen=True, slots=True)
class WarmObservation:
    binding: WarmBinding
    current: bool
    canonical: bool
    enumeration_allowed: bool
    tags_allowed: bool
    ids_allowed: bool
    types_allowed: bool
    strength_allowed: bool
    provenance_allowed: bool
    completeness_allowed: bool
    mode_allowed: bool
    relevant_complete: bool
    mandatory_known: bool
    mandatory_match: bool


@dataclass(frozen=True, slots=True)
class WarmRow:
    record_id: str
    kind: str
    strength: str
    provenance: str
    generation: int
    tags: tuple


@dataclass(frozen=True, slots=True)
class WarmProjection:
    binding: WarmBinding
    rows: tuple


@dataclass(frozen=True, slots=True)
class WarmResult:
    mode: str
    matched: tuple = ()
    unmatched: tuple = ()
    mandatory: tuple = ()
    record_ids: tuple = ()


WARM_HOLD = WarmResult("HOLD")


class WarmFixtureOwner:
    """Two independent supplied observations; no callbacks or hidden scan."""
    def __init__(self, initial, final, projection):
        self.initial = initial
        self.final = final
        self.projection = projection
        self.initial_reads = 0
        self.final_reads = 0
        self.projection_reads = 0

    def observe_initial(self):
        self.initial_reads += 1
        return self.initial

    def observe_final(self):
        self.final_reads += 1
        return self.final

    def enumerate_public_projection(self):
        self.projection_reads += 1
        return self.projection


def warm_text_bytes(value, limit):
    # Fixture canonical tokens: no whitespace, controls, surrogate or bidi
    # controls. No trimming, case folding, normalization or synonym expansion.
    # Bound character count before scanning or encoding. Not a wire decoder.
    if type(value) is not str or not 1 <= len(value) <= limit:
        return None
    if any(c.isspace() or ord(c) < 32 or 0x7f <= ord(c) <= 0x9f
           or 0xd800 <= ord(c) <= 0xdfff or 0x202a <= ord(c) <= 0x202e
           or 0x2066 <= ord(c) <= 0x2069 for c in value):
        return None
    size = len(value.encode("utf-8"))
    return size if size <= limit else None


def warm_generation(value, minimum=0):
    return type(value) is int and minimum <= value <= MAX_GENERATION


def warm_binding_bytes(binding):
    """Logical test framing: four-byte lengths/counts, eight-byte clocks,
    one-byte optional-clone marker; every occurrence counts. No serialization.
    """
    if type(binding) is not WarmBinding or type(binding.context) is not TaskContext:
        return None
    ctx = binding.context
    if not warm_generation(ctx.generation, 1):
        return None
    if any(not warm_generation(v) for v in (
            binding.input_generation, binding.policy_generation,
            binding.revocation_generation, binding.domain_generation)):
        return None
    size = 5 * 8 + 1
    for value in (ctx.principal_key, ctx.tree_key, ctx.task_id,
                  ctx.execution_context_id, ctx.origin, binding.input_commitment,
                  binding.source, binding.domain, binding.purpose, binding.recipient):
        n = warm_text_bytes(value, WARM_MAX_PROVENANCE)
        if n is None:
            return None
        size += 4 + n
    if ctx.clone_key is not None:
        n = warm_text_bytes(ctx.clone_key, WARM_MAX_PROVENANCE)
        if n is None:
            return None
        size += 4 + n
    if (ctx.origin not in ("INTERACTIVE", "BACKGROUND")
            or len(binding.input_commitment) != 64
            or any(c not in "0123456789abcdef" for c in binding.input_commitment)
            or binding.source != SOURCE or binding.domain != "user-context"
            or binding.purpose != "fixture-warm-route" or binding.recipient != RECIPIENT):
        return None
    signals = binding.signals
    if type(signals) is not tuple or len(signals) > WARM_MAX_SIGNALS:
        return None
    raw = 0
    for signal in signals:
        n = warm_text_bytes(signal, WARM_MAX_FIELD)
        if n is None:
            return None
        raw += n
    if raw > WARM_MAX_SIGNAL_BYTES:
        return None
    return size + 4 + 4 * len(signals) + raw


def warm_observation_matches(observation, binding):
    if (type(observation) is not WarmObservation
            or warm_binding_bytes(observation.binding) is None
            or observation.binding != binding):
        return False
    # A complete visible subset or a caller claim cannot substitute for
    # independent relevance and mandatory applicability observations.
    return (all(flag is True for flag in (
        observation.current, observation.canonical,
        observation.enumeration_allowed, observation.tags_allowed,
        observation.ids_allowed, observation.types_allowed,
        observation.strength_allowed, observation.provenance_allowed,
        observation.completeness_allowed, observation.mode_allowed,
        observation.relevant_complete, observation.mandatory_known))
        and type(observation.mandatory_match) is bool)


def warm_match(binding, owner):
    """Bound and select candidate references only, or return one neutral HOLD."""
    binding_size = warm_binding_bytes(binding)
    if binding_size is None or type(owner) is not WarmFixtureOwner:
        return WARM_HOLD
    initial = owner.observe_initial()
    if not warm_observation_matches(initial, binding):
        return WARM_HOLD
    # Authorization and currentness precede even simulated enumeration.
    projection = owner.enumerate_public_projection()
    if (type(projection) is not WarmProjection
            or warm_binding_bytes(projection.binding) is None
            or projection.binding != binding or type(projection.rows) is not tuple
            or len(projection.rows) > WARM_MAX_ROWS):
        return WARM_HOLD
    size = binding_size + 4  # projection's row count framing
    associations = 0
    # Validate raw inputs BEFORE deduplication or matching. Repeated bytes,
    # rows and associations are all charged. No arbitrary iterable access.
    for row in projection.rows:
        if (type(row) is not WarmRow
                or type(row.tags) is not tuple
                or not warm_generation(row.generation)
                or row.generation > binding.domain_generation):
            return WARM_HOLD
        associations += len(row.tags)
        if (associations > WARM_MAX_ASSOCIATIONS
                or len(binding.signals) * associations > WARM_MAX_COMPARISONS):
            return WARM_HOLD
        size += 8 + 4  # record generation and tag count
        for value, limit in ((row.record_id, WARM_MAX_FIELD),
                             (row.kind, WARM_MAX_FIELD),
                             (row.strength, WARM_MAX_PROVENANCE),
                             (row.provenance, WARM_MAX_PROVENANCE)):
            n = warm_text_bytes(value, limit)
            if n is None:
                return WARM_HOLD
            size += 4 + n
        if row.kind not in WARM_USER_KINDS or row.strength not in ("soft", "hard"):
            return WARM_HOLD
        for tag in row.tags:
            n = warm_text_bytes(tag, WARM_MAX_FIELD)
            if n is None:
                return WARM_HOLD
            size += 4 + n
        if size > WARM_MAX_PROJECTION_BYTES:
            return WARM_HOLD
    if size > WARM_MAX_PROJECTION_BYTES:
        return WARM_HOLD
    by_id = {}
    for row in projection.rows:
        if row.record_id in by_id and by_id[row.record_id] != row:
            return WARM_HOLD
        by_id[row.record_id] = row
    matched, unmatched, mandatory = [], [], []
    selected = set()
    for signal in dict.fromkeys(binding.signals):
        found = hard = False
        for row in by_id.values():
            if signal not in row.tags:
                continue
            found = True
            if row.record_id not in selected:
                if len(selected) == MAX_RECORDS:
                    return WARM_HOLD
                selected.add(row.record_id)
            hard |= row.kind == "user-constraint" and row.strength == "hard"
        (matched if found else unmatched).append(signal)
        if hard:
            mandatory.append(signal)
    # Contradictory independent mandatory evidence cannot become CHECK/NONE.
    if bool(mandatory) != initial.mandatory_match:
        return WARM_HOLD
    final = owner.observe_final()
    if (not warm_observation_matches(final, binding)
            or final.mandatory_match != initial.mandatory_match):
        return WARM_HOLD
    return WarmResult("must-check" if mandatory else "check" if matched else "none",
                      tuple(matched), tuple(unmatched), tuple(mandatory),
                      tuple(sorted(selected)))


class WarmMatcherWitnessTests(unittest.TestCase):
    def setUp(self):
        self.binding = WarmBinding(CONTEXT, 4, digest("public fixture input"),
                                   2, 1, 3, SOURCE, "user-context",
                                   "fixture-warm-route", RECIPIENT,
                                   ("food", "shopping", "food", "other"))
        self.preference = WarmRow("z-pref", "user-preference", "soft",
                                  "public-origin", 2, ("food", "shopping"))
        self.constraint = WarmRow("a-hard", "user-constraint", "hard",
                                  "public-origin", 3, ("shopping",))
        self.rows = (self.preference, self.constraint)

    def observation(self, binding, mandatory):
        # Explicit independent fixture claims; never derived by the matcher.
        return WarmObservation(binding, True, True, True, True, True, True,
                               True, True, True, True, True, True, mandatory)

    def trial(self, binding=None, rows=None, *, mandatory=False,
              initial=None, final=None, projection=None):
        binding = self.binding if binding is None else binding
        rows = self.rows if rows is None else rows
        owner = WarmFixtureOwner(
            self.observation(binding, mandatory) if initial is None else initial,
            self.observation(binding, mandatory) if final is None else final,
            WarmProjection(binding, rows) if projection is None else projection)
        return warm_match(binding, owner), owner

    def held(self, *args, reads=1, **kwargs):
        result, owner = self.trial(*args, **kwargs)
        self.assertIs(result, WARM_HOLD)
        self.assertEqual(owner.projection_reads, reads)
        return owner

    def test_exact_first_occurrence_union_and_mandatory(self):
        result, owner = self.trial(rows=self.rows + (self.preference,), mandatory=True)
        self.assertEqual(result, WarmResult("must-check", ("food", "shopping"),
                                           ("other",), ("shopping",),
                                           ("a-hard", "z-pref")))
        self.assertEqual((owner.initial_reads, owner.projection_reads,
                          owner.final_reads), (1, 1, 1))

    def test_optional_strength_type_and_exact_case_unicode(self):
        binding = replace(self.binding, signals=("Food", "food", "café", "cafe\u0301"))
        rows = (replace(self.preference, strength="hard", tags=("food", "café")),
                replace(self.constraint, strength="soft", tags=("food",)))
        result, _ = self.trial(binding, rows)
        self.assertEqual(result, WarmResult("check", ("food", "café"),
                                           ("Food", "cafe\u0301"), (),
                                           ("a-hard", "z-pref")))

    def test_complete_empty_and_no_match_require_final(self):
        for binding, rows in ((replace(self.binding, signals=()), self.rows),
                              (self.binding, ()),
                              (replace(self.binding, signals=("unmatched",)), self.rows)):
            with self.subTest(signals=binding.signals):
                result, owner = self.trial(binding, rows)
                self.assertEqual(result, WarmResult("none", unmatched=tuple(
                    dict.fromkeys(binding.signals))))
                self.assertEqual(owner.final_reads, 1)
                stale = replace(self.observation(binding, False), current=False)
                self.assertEqual(self.held(binding, rows, final=stale).final_reads, 1)

    def test_initial_denial_before_enumeration_and_neutral_hold(self):
        for field in ("current", "canonical", "enumeration_allowed", "tags_allowed",
                      "ids_allowed", "types_allowed", "strength_allowed",
                      "provenance_allowed", "completeness_allowed", "mode_allowed",
                      "relevant_complete", "mandatory_known"):
            for value in (False, None, 1):
                with self.subTest(field=field, value=value):
                    initial = replace(self.observation(self.binding, True), **{field: value})
                    for rows in (self.rows, (), (self.constraint,)):
                        owner = self.held(rows=rows, initial=initial, reads=0)
                        self.assertEqual((owner.initial_reads, owner.final_reads), (1, 0))
        self.held(initial=replace(self.observation(self.binding, True),
                                  mandatory_match=None), reads=0)

    def test_independent_final_denial_or_unknown_discards_entire_route(self):
        for field in ("current", "canonical", "enumeration_allowed", "tags_allowed",
                      "ids_allowed", "types_allowed", "strength_allowed",
                      "provenance_allowed", "completeness_allowed", "mode_allowed",
                      "relevant_complete", "mandatory_known", "mandatory_match"):
            for value in (False, None, 1):
                with self.subTest(field=field, value=value):
                    final = replace(self.observation(self.binding, True), **{field: value})
                    self.assertEqual(self.held(mandatory=True, final=final).final_reads, 1)
        self.held(mandatory=True, final=object())

    def test_independent_binding_changes_at_each_boundary(self):
        b = self.binding
        changes = [replace(b, **{field: value}) for field, value in (
            ("input_generation", 5), ("input_commitment", digest("different")),
            ("domain_generation", 4), ("policy_generation", 3),
            ("revocation_generation", 2), ("recipient", "other"),
            ("purpose", "other"), ("source", "other"), ("domain", "other"),
            ("signals", ("shopping",)))]
        changes += [replace(b, context=replace(b.context, **{field: value}))
                    for field, value in (("principal_key", "other"), ("tree_key", "maple"),
                    ("clone_key", "clone-a"), ("task_id", "task-b"),
                    ("execution_context_id", "ctx-b"), ("generation", 2),
                    ("origin", "BACKGROUND"))]
        for changed in changes:
            with self.subTest(binding=changed):
                obs = self.observation(changed, True)
                self.held(initial=obs, reads=0)
                self.assertEqual(self.held(mandatory=True, final=obs).final_reads, 1)
                self.held(projection=WarmProjection(changed, self.rows))

    def test_mandatory_coverage_contradiction_and_no_hidden_fallback(self):
        self.held(mandatory=False)  # visible hard contradicts independent absence
        self.held(rows=(self.preference,), mandatory=True)
        self.held(rows=(), mandatory=True)
        empty = replace(self.binding, signals=())
        self.held(empty, (), mandatory=True)
        self.held(empty, (), initial=replace(self.observation(empty, False),
                                            mandatory_known=False), reads=0)

    def test_raw_signal_limits_and_noncanonical_input(self):
        binding = replace(self.binding, signals=("s" * 128,) * 32)
        result, _ = self.trial(binding, ())
        self.assertEqual(result.mode, "none")
        for signals in (binding.signals + ("s",), ("s" * 129,),
                        ("é" * 65,), ("",), (" food",), ("food ",),
                        ("raw prompt",), ("\ud800",), ("a\u0000",),
                        ("a\u202e",), ["food"], "food", iter(("food",)), (1,)):
            self.held(replace(binding, signals=signals), (), reads=0)
        self.assertEqual(self.trial(replace(binding, signals=("é" * 64,)), ())[0].mode,
                         "none")

    def test_row_association_comparison_caps_and_duplicate_flood(self):
        binding = replace(self.binding, signals=("food",) * 32)
        row = replace(self.preference, tags=("food",) * 4)
        rows = (row,) * 128  # 512 raw associations; 16384 raw comparison ceiling
        self.assertEqual(self.trial(binding, rows)[0].record_ids, ("z-pref",))
        self.held(binding, rows + (row,))
        self.held(binding, rows[:-1] + (replace(row, tags=row.tags + ("food",)),))
        self.held(binding, (replace(row, tags=("food",) * 513),))
        self.held(binding, list(rows))
        self.held(binding, iter(rows))
        self.held(binding, (replace(row, tags=list(row.tags)),))

    def test_union_selected_limit_before_publication(self):
        rows = tuple(replace(self.preference, record_id="id-%02d" % i,
                             tags=("food",) if i % 2 else ("food", "shopping"))
                     for i in range(33))
        result, _ = self.trial(rows=rows[:32])
        self.assertEqual(result.record_ids, tuple(r.record_id for r in rows[:32]))
        self.held(rows=rows)
        # A different signal must not get its own separate allowance.
        self.held(rows=rows[:32] + (replace(rows[32], tags=("shopping",)),))

    def test_field_bytes_conflicts_and_malformed_projection(self):
        row = replace(self.preference, record_id="é" * 64,
                      provenance="é" * 128, tags=("é" * 64,))
        binding = replace(self.binding, signals=row.tags)
        self.assertEqual(self.trial(binding, (row,))[0].record_ids, (row.record_id,))
        for change in ({"record_id": "é" * 65}, {"provenance": "é" * 129},
                       {"tags": ("é" * 65,)}, {"kind": "x" * 129},
                       {"kind": "operational-learning"}, {"strength": "unknown"},
                       {"generation": True}, {"generation": 4},
                       {"record_id": "\ud800"}, {"tags": (" food",)}):
            self.held(binding, (replace(row, **change),))
        for field, value in (("strength", "hard"), ("provenance", "other"),
                             ("kind", "user-correction"), ("generation", 1),
                             ("tags", ("other",))):
            self.held(rows=(self.preference, replace(self.preference, **{field: value})))
        self.held(projection=object())
        self.held(rows=(object(),))

    def test_projection_aggregate_includes_framing_and_repeated_bytes(self):
        binding = replace(self.binding, signals=())
        # Independent arithmetic for the declared logical framing, not an
        # encoded object or real memory footprint. Construct exactly 65536.
        ctx = binding.context
        header = 5 * 8 + 1 + 4 + 4 + sum(4 + len(s.encode("utf-8")) for s in (
            ctx.principal_key, ctx.tree_key, ctx.task_id, ctx.execution_context_id,
            ctx.origin, binding.input_commitment, binding.source, binding.domain,
            binding.purpose, binding.recipient))
        row = WarmRow("id", "user-preference", "soft", "p", 1, ("t" * 128,) * 3)
        row_base = 8 + 4 + sum(4 + len(s.encode("utf-8")) for s in (
            row.record_id, row.kind, row.strength, *row.tags)) + 4
        remaining = WARM_MAX_PROJECTION_BYTES - header - 128 * row_base
        self.assertTrue(128 <= remaining < 128 * WARM_MAX_PROVENANCE)
        # Use unique four-byte IDs instead of the two-byte base ID.
        # Same ID with differing provenance would be a separate conflict.
        remaining -= 2 * 128
        quotient, extra = divmod(remaining, 128)
        rows = tuple(replace(row, record_id="%04d" % i,
                             provenance="p" * (quotient + (i < extra)))
                     for i in range(128))
        self.assertEqual(self.trial(binding, rows)[0], WarmResult("none"))
        self.held(binding, rows[:-1] + (replace(rows[-1],
                                               provenance=rows[-1].provenance + "p"),))
        # Repeated identical metadata remains chargeable before dedup.
        self.held(binding, (replace(row, provenance="p" * 256),) * 128)

    def test_generation_bounds_and_bool_not_integer(self):
        fields = ("input_generation", "policy_generation", "revocation_generation",
                  "domain_generation")
        for field in fields:
            for value in (MAX_GENERATION + 1, -1, True, 1.0):
                self.held(replace(self.binding, **{field: value}), (), reads=0)
            for value in (0, MAX_GENERATION):
                self.assertEqual(self.trial(replace(self.binding, **{field: value}), ())[0].mode,
                                 "none")
        b = replace(self.binding, domain_generation=MAX_GENERATION)
        self.assertEqual(self.trial(b, (replace(self.preference,
                                              generation=MAX_GENERATION),))[0].mode, "check")
        self.held(b, (replace(self.preference, generation=MAX_GENERATION + 1),))

    def test_warm_success_does_not_invoke_or_authorize_downstream(self):
        from unittest.mock import patch
        with patch(__name__ + ".resolve") as resolver, \
                patch(__name__ + ".assemble_hot_context") as assembler, \
                patch.object(FixtureOwner, "body") as body:
            self.assertEqual(self.trial(mandatory=True)[0].mode, "must-check")
            resolver.assert_not_called()
            assembler.assert_not_called()
            body.assert_not_called()
        route = HotRouteStamp(CONTEXT, 4, 2, 3, 2, ("preference",), ())
        plan = Selection(route, SOURCE, PURPOSE, RECIPIENT, (CATALOG[1],))
        owner = FixtureOwner(Observation(plan, True, ()))
        with self.assertRaisesRegex(ContextRefusal, "USE_NOT_ELIGIBLE"):
            resolve(plan, owner)
        self.assertEqual(owner.body_reads, [])
        empty = replace(plan, route=replace(route, user_record_ids=()), versions=())
        owner = FixtureOwner(Observation(plan, True, ()))
        with self.assertRaisesRegex(ContextRefusal, "CURRENTNESS_CHANGED"):
            resolve(empty, owner)
        self.assertEqual(owner.body_reads, [])

if __name__ == "__main__":
    unittest.main()
