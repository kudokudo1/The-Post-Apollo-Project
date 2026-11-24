from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from capability_registry_b6r2 import (
    Capability, Workshop, Registry, TreeProfile, CapabilityRefusal,
    BRISTLECONE_REGISTRY, BRISTLECONE_GENERAL, BRISTLECONE_WORKSHOPS,
    bristlecone_reference_profile, plan_selection,
)


class CapabilityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.ctx = TaskContext("fixture-owner", "bristlecone", None,
                               "task-a", "context-a", 1, "INTERACTIVE")
        self.profile = bristlecone_reference_profile(self.ctx)

    def plan(self, workshop="code-debug", **kwargs):
        result = plan_selection(self.profile, self.ctx, workshop, **kwargs)
        self.assertEqual(result.status, "UNKNOWN_HOLD")
        self.assertFalse(result.permission_granted)
        self.assertFalse(result.production_authority)
        self.assertFalse(result.model_execution_permitted)
        self.assertEqual(result.safe_actions, ())
        return result

    def test_historical_registry_and_workshops(self):
        self.assertEqual(len(BRISTLECONE_REGISTRY.definitions), 18)
        self.assertEqual(BRISTLECONE_GENERAL, ("todo", "clarify", "session", "memory", "leaf"))
        self.assertEqual([w.key for w in BRISTLECONE_WORKSHOPS],
                         ["research", "design", "code-debug", "model"])
        self.assertEqual(BRISTLECONE_REGISTRY.find("session").historical_target, "session_search")
        self.assertEqual(BRISTLECONE_REGISTRY.find("debugging").historical_target,
                         "systematic-debugging")

    def test_historical_core_sets(self):
        for name, expected in (("research", ("web",)), ("design", ("memory", "clarify")),
                               ("code-debug", ("file", "terminal")),
                               ("model", ("file", "terminal"))):
            self.assertEqual(self.plan(name).selected, expected)

    def test_individual_general_selection(self):
        p = self.plan(general=("todo",))
        self.assertEqual(p.selected, ("file", "terminal", "todo"))
        self.assertIn("leaf", p.dormant)
        self.assertIn("session", p.dormant)

    def test_individual_workshop_selection(self):
        p = self.plan(ready=("testing",))
        self.assertEqual(p.selected, ("file", "terminal", "testing"))
        self.assertIn("debugging", p.dormant)
        self.assertIn("code-execution", p.dormant)

    def test_combined_layers(self):
        self.assertEqual(self.plan(general=("leaf",), ready=("debugging",)).selected,
                         ("file", "terminal", "leaf", "debugging"))

    def test_general_promoted_to_core_not_duplicated(self):
        p = self.plan("design", general=("memory", "clarify"))
        self.assertEqual(p.selected, ("memory", "clarify"))

    def test_unresolved_historical_targets_remain_explicit(self):
        p = self.plan("model", general=("leaf",), ready=("training",))
        self.assertEqual(p.unresolved, ("leaf", "training"))
        self.assertFalse(p.model_execution_permitted)

    def test_unselected_capabilities_dormant(self):
        p = self.plan()
        self.assertEqual(set(p.dormant) | set(p.selected), set(self.profile.owned))
        self.assertFalse(set(p.dormant) & set(p.selected))

    def test_unknown_and_cross_workshop_selection_refused(self):
        for args in ({"general": ("file",)}, {"ready": ("training",)},
                     {"ready": ("unknown",)}, {"general": ("unknown",)}):
            with self.subTest(args=args), self.assertRaises(CapabilityRefusal):
                self.plan(**args)
        with self.assertRaises(CapabilityRefusal):
            self.plan("unknown")

    def test_duplicate_malformed_selection_refused(self):
        for value in (["todo"], ("todo", "todo"), ("../todo",), (None,), (True,)):
            with self.assertRaises(CapabilityRefusal):
                self.plan(general=value)

    def test_sticky_explicit_same_context(self):
        first = self.plan(ready=("debugging",), general=("todo",))
        second = self.plan(sticky=("debugging",), prior=first)
        self.assertEqual(second.selected, ("file", "terminal", "debugging"))
        self.assertEqual(second.sticky, ("debugging",))
        self.assertIn("todo", second.dormant)

    def test_no_implicit_sticky(self):
        self.plan(general=("todo",))
        self.assertEqual(self.plan().selected, ("file", "terminal"))

    def test_sticky_cannot_activate_previously_dormant(self):
        first = self.plan()
        with self.assertRaises(CapabilityRefusal):
            self.plan(sticky=("todo",), prior=first)

    def test_nonsticky_core_cannot_be_retained_as_sticky(self):
        first = self.plan()
        with self.assertRaises(CapabilityRefusal):
            self.plan(sticky=("file",), prior=first)

    def test_sticky_cannot_cross_workshop(self):
        first = self.plan(ready=("debugging",))
        with self.assertRaises(CapabilityRefusal):
            self.plan("design", sticky=("debugging",), prior=first)

    def test_sticky_cannot_cross_context_or_generation(self):
        first = self.plan(general=("todo",))
        for other in (replace(self.ctx, clone_key="clone-a"),
                      replace(self.ctx, generation=2),
                      replace(self.ctx, task_id="other-task")):
            with self.assertRaises(CapabilityRefusal):
                plan_selection(bristlecone_reference_profile(other), other,
                               "code-debug", sticky=("todo",), prior=first)

    def test_sticky_rechecks_current_profile(self):
        first = self.plan(general=("todo",))
        restricted = replace(self.profile, general_ready=("memory", "clarify"))
        with self.assertRaises(CapabilityRefusal):
            plan_selection(restricted, self.ctx, "code-debug",
                           sticky=("todo",), prior=first)

    def test_profile_context_exact_binding(self):
        for other in (replace(self.ctx, principal_key="other"),
                      replace(self.ctx, clone_key="clone-a"),
                      replace(self.ctx, execution_context_id="other"),
                      replace(self.ctx, generation=2)):
            with self.assertRaises(CapabilityRefusal):
                plan_selection(self.profile, other, "code-debug")

    def test_other_tree_cannot_claim_bristlecone_profile(self):
        with self.assertRaises(CapabilityRefusal):
            bristlecone_reference_profile(replace(self.ctx, tree_key="maple"))

    def test_micro_workshop_reuses_definition_without_other_tree_tools(self):
        maple = replace(self.ctx, tree_key="maple", origin="BACKGROUND")
        profile = TreeProfile(maple, BRISTLECONE_REGISTRY, ("file",), (),
                              (Workshop("organize", ("file",)),))
        p = plan_selection(profile, maple, "organize")
        self.assertEqual(p.selected, ("file",))
        self.assertEqual(p.dormant, ())
        self.assertIs(profile.registry.find("file"), self.profile.registry.find("file"))
        with self.assertRaises(CapabilityRefusal):
            plan_selection(profile, maple, "organize", general=("todo",))

    def test_invalid_registry_and_workshop_references(self):
        with self.assertRaises(CapabilityRefusal):
            Registry((Capability("file", "toolset"), Capability("file", "toolset")))
        with self.assertRaises(CapabilityRefusal):
            replace(self.profile, owned=("file",))
        with self.assertRaises(CapabilityRefusal):
            replace(self.profile, general_ready=("unknown",))
        with self.assertRaises(CapabilityRefusal):
            Workshop("bad", ("file",), ("file",))
        with self.assertRaises(CapabilityRefusal):
            replace(self.profile, workshops=(Workshop("bad", ("unknown",)),))

    def test_independent_clones_no_shared_active_selection(self):
        a = replace(self.ctx, clone_key="a", execution_context_id="ctx-a")
        b = replace(self.ctx, clone_key="b", execution_context_id="ctx-b")
        pa = plan_selection(bristlecone_reference_profile(a), a, "research", general=("leaf",))
        pb = plan_selection(bristlecone_reference_profile(b), b, "code-debug", ready=("testing",))
        self.assertEqual(pa.selected, ("web", "leaf"))
        self.assertEqual(pb.selected, ("file", "terminal", "testing"))
        self.assertNotEqual(pa.context, pb.context)

    def test_plan_and_registry_are_immutable(self):
        p = self.plan()
        with self.assertRaises(FrozenInstanceError):
            p.selected = ("training",)
        with self.assertRaises(FrozenInstanceError):
            BRISTLECONE_REGISTRY.definitions = ()


if __name__ == "__main__":
    unittest.main()
