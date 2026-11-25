"""Original task-sticky behavior under current scoped fixture constraints."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from context_first_tree_m2 import ContextRefusal
from layered_hot_context_m7a import HotRouteStamp, SelectedHotRecord, MAX_RECORDS
from task_sticky_context_m7b import HotDependencies, TaskStickyContext


class StickyTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TaskContext("owner", "cherry", None, "task-a", "context-a",
                               1, "INTERACTIVE")
        self.route = HotRouteStamp(self.ctx, 1, 1, 1, 1, ("u1", "u2"), ("o1",))
        self.cache = TaskStickyContext(self.ctx)
        self.u = (self.record("u1"), self.record("u2"))
        self.o = (self.record("o1", operational=True),)
        self.install(self.route)
        self.remember(user_records=self.u, operational_records=self.o)

    def record(self, key, operational=False, generation=1):
        return SelectedHotRecord("owner", "cherry", key,
            "operational-learning" if operational else "user-preference",
            generation, True, "Public " + key)

    def args(self, route=None):
        route = self.route if route is None else route
        return dict(current=route, dependencies=HotDependencies.from_route(route))

    def install(self, route):
        self.cache.install_route(route, **self.args(route))
        self.route = route

    def remember(self, **kwargs):
        self.cache.remember(self.route, **self.args(), **kwargs)

    def lookup(self):
        return self.cache.lookup(self.route, **self.args())

    def test_execution_steps_reuse_exact_route_and_assembly(self):
        first = self.cache.assemble(self.route, **self.args())
        for _ in range(10):
            self.assertEqual(self.cache.assemble(self.route, **self.args()), first)
        self.assertEqual(self.cache.counts(), (2,1))

    def test_new_input_requires_reselection_and_reuses_only_selected_records(self):
        old = self.route
        fresh = replace(old, input_generation=2, user_record_ids=("u2","u3"))
        self.cache.observe(current=HotDependencies.from_route(fresh))
        self.assertEqual(self.cache.counts(), (2,1))
        with self.assertRaises(ContextRefusal):
            self.cache.lookup(old, **self.args(fresh))
        self.install(fresh)
        found = self.lookup()
        self.assertEqual(found.user_records, (self.u[1],))
        self.assertEqual(found.missing_user_ids, ("u3",))
        self.assertEqual(found.operational_records, self.o)
        with self.assertRaisesRegex(ContextRefusal, "STICKY_RECORDS_MISSING"):
            self.cache.assemble(self.route, **self.args())
        self.remember(user_records=(self.record("u3"),))
        self.assertEqual(self.cache.assemble(self.route, **self.args()).record_ids,
                         ("u2","u3","o1"))

    def test_independent_domain_invalidation(self):
        self.install(replace(self.route, user_context_generation=2))
        self.assertEqual(self.cache.counts(), (0,1))
        self.assertEqual(self.lookup().operational_records, self.o)
        self.remember(user_records=(self.record("u1",generation=2),))
        self.install(replace(self.route, operational_generation=2))
        self.assertEqual(self.cache.counts(), (1,0))
        self.assertEqual(self.lookup().missing_operational_ids, ("o1",))

    def test_policy_change_drops_both_domains(self):
        self.install(replace(self.route, policy_generation=2))
        self.assertEqual(self.cache.counts(), (0,0))
        self.assertFalse(self.lookup().complete)

    def test_old_clocks_and_cross_task_refused(self):
        old = self.route
        self.install(replace(old,input_generation=2))
        for clock in (HotDependencies.from_route(old),
                      replace(HotDependencies.from_route(self.route),
                              context=replace(self.ctx,task_id="other")),
                      replace(HotDependencies.from_route(self.route),
                              context=replace(self.ctx,clone_key="clone-a"))):
            with self.assertRaises(ContextRefusal):
                self.cache.observe(current=clock)
        self.assertTrue(self.lookup().complete)
        with self.assertRaises(ContextRefusal):
            self.cache.lookup(old, **self.args())

    def test_atomic_conflict_and_unselected_refusals(self):
        self.install(replace(self.route,user_record_ids=("u1","u2","u3")))
        for records in ((self.record("u3"), replace(self.u[0],text="Changed")),
                        (self.record("u3"), self.record("not-selected")),
                        (self.record("u3"), replace(self.u[1],active=False))):
            with self.assertRaises(ContextRefusal):
                self.remember(user_records=records)
            self.assertEqual(self.cache.counts(), (2,1))
            self.assertEqual(self.lookup().missing_user_ids, ("u3",))

    def test_bounded_across_many_inputs(self):
        for index in range(1,101):
            key = "new"+str(index)
            self.install(replace(self.route,input_generation=index+1,
                                 user_record_ids=(key,)))
            self.remember(user_records=(self.record(key),))
            self.assertLessEqual(sum(self.cache.counts()),MAX_RECORDS)
            self.assertTrue(self.lookup().complete)
            self.assertEqual(self.lookup().operational_records,self.o)

    def test_closed_cache_cannot_revive(self):
        self.cache.close()
        self.cache.close()
        self.assertEqual(self.cache.counts(), (0,0))
        with self.assertRaisesRegex(ContextRefusal,"STICKY_CLOSED"):
            self.install(self.route)

    def test_route_requires_exact_independent_currentness(self):
        original = self.route
        changed = replace(original,user_record_ids=("u2",))
        with self.assertRaises(ContextRefusal):
            self.cache.install_route(changed,current=original,
                                     dependencies=HotDependencies.from_route(original))
        self.assertTrue(self.lookup().complete)


if __name__ == "__main__":
    unittest.main()
