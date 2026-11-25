"""M7c explicit derived shedding; no actual lifecycle or protected records."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import ContextRefusal
from layered_hot_context_m7a import HotRouteStamp, SelectedHotRecord, MAX_GENERATION
from task_sticky_context_m7b import HotDependencies, TaskStickyContext


class SheddingTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TaskContext("owner", "cherry", None, "task-a", "context-a",
                               1, "INTERACTIVE")
        self.route = HotRouteStamp(self.ctx, 1, 1, 1, 1, ("u",), ("o",))
        self.cache = TaskStickyContext(self.ctx)
        self.u = SelectedHotRecord("owner", "cherry", "u", "user-preference", 1, True, "Public user")
        self.o = SelectedHotRecord("owner", "cherry", "o", "operational-learning", 1, True, "Public lesson")
        self.install(self.route)
        self.cache.remember(self.route, **self.args(self.route),
                            user_records=(self.u,), operational_records=(self.o,))

    def args(self, route):
        return dict(current=route, dependencies=HotDependencies.from_route(route))

    def install(self, route):
        self.cache.install_route(route, **self.args(route))

    def shed(self, **flags):
        self.cache.shed(self.route, **self.args(self.route), **flags)

    def fresh(self):
        return replace(self.route, input_generation=2)

    def test_user_only_and_explicit_rehydration(self):
        self.shed(drop_user=True)
        self.assertEqual(self.cache.counts(), (0, 1))
        fresh = self.fresh()
        self.install(fresh)
        found = self.cache.lookup(fresh, **self.args(fresh))
        self.assertEqual(found.missing_user_ids, ("u",))
        self.assertEqual(found.operational_records, (self.o,))
        with self.assertRaisesRegex(ContextRefusal, "STICKY_RECORDS_MISSING"):
            self.cache.assemble(fresh, **self.args(fresh))
        self.cache.remember(fresh, **self.args(fresh), user_records=(self.u,))
        self.assertEqual(self.cache.assemble(fresh, **self.args(fresh)).record_ids, ("u", "o"))

    def test_operational_only(self):
        self.shed(drop_operational=True)
        fresh = self.fresh()
        self.install(fresh)
        found = self.cache.lookup(fresh, **self.args(fresh))
        self.assertEqual(found.user_records, (self.u,))
        self.assertEqual(found.missing_operational_ids, ("o",))

    def test_both_and_old_route_refused(self):
        self.shed(drop_user=True, drop_operational=True)
        self.assertEqual(self.cache.counts(), (0, 0))
        for op in (self.cache.lookup, self.cache.remember, self.cache.assemble,
                   self.cache.install_route):
            with self.assertRaises(ContextRefusal):
                op(self.route, **self.args(self.route))
        fresh = self.fresh()
        self.install(fresh)
        self.assertFalse(self.cache.lookup(fresh, **self.args(fresh)).complete)

    def test_invalid_flags_and_wrong_scope(self):
        for flags in ({}, {"drop_user": 1}, {"drop_operational": "yes"}):
            with self.assertRaises(ContextRefusal):
                self.shed(**flags)
        other = replace(self.route, context=replace(self.ctx, task_id="other"))
        with self.assertRaises(ContextRefusal):
            self.cache.shed(other, **self.args(other), drop_user=True)
        self.assertEqual(self.cache.counts(), (1, 1))
        self.assertTrue(self.cache.lookup(self.route, **self.args(self.route)).complete)

    def test_policy_change_does_not_bypass_floor(self):
        self.shed(drop_user=True)
        changed = replace(self.route, policy_generation=2)
        with self.assertRaisesRegex(ContextRefusal, "STICKY_SHED_RESELECTION_REQUIRED"):
            self.install(changed)
        self.assertEqual(self.cache.counts(), (0, 0))
        fresh = replace(changed, input_generation=2)
        self.install(fresh)
        self.assertFalse(self.cache.lookup(fresh, **self.args(fresh)).complete)

    def test_stale_shed_cannot_clear_replacement(self):
        fresh = self.fresh()
        self.install(fresh)
        with self.assertRaises(ContextRefusal):
            self.shed(drop_user=True)
        self.assertEqual(self.cache.counts(), (1, 1))

    def test_closed_and_generation_exhaustion_fail_closed(self):
        last = replace(self.route, input_generation=MAX_GENERATION)
        self.install(last)
        self.cache.shed(last, **self.args(last), drop_user=True)
        with self.assertRaises(ContextRefusal):
            self.install(last)
        self.cache.close()
        with self.assertRaisesRegex(ContextRefusal, "STICKY_CLOSED"):
            self.cache.shed(last, **self.args(last), drop_operational=True)


if __name__ == "__main__":
    unittest.main()
