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


if __name__ == "__main__":
    unittest.main()
