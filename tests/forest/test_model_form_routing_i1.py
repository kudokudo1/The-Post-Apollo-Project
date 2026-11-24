from dataclasses import FrozenInstanceError, replace
from itertools import product
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from model_form_routing_i1 import (
    TurnScope, ReasoningReference, SemanticEvidence, RoutingInput,
    ModelFormRecommendation, RoutingRefusal, recommend,
    preserve_recommendation, presentation_reference,
)


class ModelFormRoutingTests(unittest.TestCase):
    def setUp(self):
        self.scope = TurnScope(TaskContext("owner-a", "bristlecone", None,
                                "task-a", "context-a", 1, "INTERACTIVE"), "turn-a")
        self.reasoning = ReasoningReference(self.scope, "normal", "explicit")

    def input(self, form="auto", facts=(), reasoning=None, scope=None):
        scope = self.scope if scope is None else scope
        return RoutingInput(scope, form,
                            self.reasoning if reasoning is None else reasoning,
                            tuple(SemanticEvidence(scope, signal, value, "fixture-producer")
                                  for signal, value in facts))

    def test_complete_auto_truth_table_all_reasoning_modes(self):
        for complexity, failure, suitability, effort in product(
                (None, "low", "normal", "high"), (None, "absent", "present"),
                (None, "sufficient", "insufficient", "unknown"),
                ("light", "normal", "deep")):
            facts = tuple((k, v) for k, v in (
                ("task_complexity", complexity), ("known_small_failure", failure),
                ("small_capability_suitability", suitability)) if v is not None)
            expected = "big" if (complexity == "high" or failure == "present"
                                 or suitability == "insufficient") else "small"
            with self.subTest(facts=facts, effort=effort):
                r = recommend(self.input(facts=facts, reasoning=replace(self.reasoning, mode=effort)))
                self.assertEqual(r.form, expected)
                self.assertFalse(r.model_execution_permitted)

    def test_reason_order_preserved(self):
        r = recommend(self.input(facts=(("known_small_failure", "present"),
                  ("small_capability_suitability", "insufficient"),
                  ("task_complexity", "high"))))
        self.assertEqual(r.reasons, ("high_task_complexity", "known_small_failure",
                                    "small_capability_insufficient"))

    def test_explicit_small_wins_over_all_escalations(self):
        r = recommend(self.input("small", (("task_complexity", "high"),
                                           ("known_small_failure", "present"))))
        self.assertEqual((r.form, r.reasons), ("small", ("explicit_form",)))

    def test_explicit_big_never_downgrades(self):
        self.assertEqual(recommend(self.input("BIG")).form, "big")

    def test_unknown_signals_are_not_escalation(self):
        self.assertEqual(recommend(self.input(facts=(("reasoning", "deep"),
                         ("resource_pressure", "high")))).form, "small")

    def test_missing_evidence_does_not_prove_sufficiency(self):
        r = recommend(self.input())
        self.assertEqual(r.reasons, ("no_big_escalation_evidence",))
        self.assertIsNone(r.resolved_binding)
        self.assertFalse(r.permission_granted)

    def test_invalid_recognized_values_refused_even_explicit(self):
        for form in ("auto", "small", "big"):
            with self.assertRaisesRegex(RoutingRefusal, "INVALID_RECOGNIZED_EVIDENCE"):
                recommend(self.input(form, (("task_complexity", "extreme"),)))

    def test_contradiction_refused(self):
        with self.assertRaisesRegex(RoutingRefusal, "CONTRADICTORY_EVIDENCE"):
            recommend(self.input(facts=(("task_complexity", "high"),
                                        ("task_complexity", "low"))))

    def test_identical_duplicate_fact_allowed(self):
        r = recommend(self.input(facts=(("task_complexity", "high"),
                                        ("task_complexity", "high"))))
        self.assertEqual(r.reasons, ("high_task_complexity",))

    def test_reasoning_aliases(self):
        for alias, canonical in (("Quick", "light"), ("Standard", "normal"), ("Deep", "deep")):
            r = replace(self.reasoning, mode=alias)
            self.assertEqual(r.mode, canonical)
            self.assertEqual(recommend(self.input(reasoning=r)).form, "small")

    def test_invalid_inputs_and_provenance(self):
        for form in (None, "", "qwen", True):
            with self.assertRaises(RoutingRefusal):
                self.input(form)
        for producer in ("", "x"*129, "line\nbreak", False):
            with self.assertRaises(RoutingRefusal):
                SemanticEvidence(self.scope, "task_complexity", "high", producer)
        with self.assertRaises(RoutingRefusal):
            replace(self.reasoning, mode="auto")

    def test_evidence_count_bound(self):
        with self.assertRaises(RoutingRefusal):
            self.input(facts=(("task_complexity", "high"),)*33)

    def test_cross_context_and_turn_evidence_refused(self):
        for other in (replace(self.scope, turn_id="turn-b"),
                      replace(self.scope, context=replace(self.scope.context, generation=2)),
                      replace(self.scope, context=replace(self.scope.context, clone_key="clone-a"))):
            with self.assertRaisesRegex(RoutingRefusal, "EVIDENCE_SCOPE_MISMATCH"):
                RoutingInput(self.scope, "auto", self.reasoning,
                             (SemanticEvidence(other, "task_complexity", "high", "producer"),))
            with self.assertRaisesRegex(RoutingRefusal, "REASONING_SCOPE_MISMATCH"):
                self.input(reasoning=replace(self.reasoning, scope=other))

    def test_two_contexts_independent(self):
        other = replace(self.scope, context=replace(self.scope.context, execution_context_id="context-b"))
        a = recommend(self.input("big"))
        b = recommend(self.input("small", scope=other, reasoning=replace(self.reasoning, scope=other)))
        self.assertEqual((a.form, b.form), ("big", "small"))

    def test_retry_reference_preserves_original_identity(self):
        original = self.input(facts=(("task_complexity", "high"),))
        decision = recommend(original)
        self.assertIs(preserve_recommendation(decision, original), decision)

    def test_changed_input_cannot_reroute_retry(self):
        original = self.input("big")
        decision = recommend(original)
        for changed in (self.input("small"),
                        self.input("big", facts=(("task_complexity", "high"),)),
                        self.input("big", reasoning=replace(self.reasoning, mode="deep"))):
            with self.assertRaisesRegex(RoutingRefusal, "ROUTING_INPUT_CHANGED"):
                preserve_recommendation(decision, changed)

    def test_new_turn_cannot_reuse_previous(self):
        other = replace(self.scope, turn_id="turn-b")
        changed = self.input(scope=other, reasoning=replace(self.reasoning, scope=other))
        with self.assertRaises(RoutingRefusal):
            preserve_recommendation(recommend(self.input()), changed)

    def test_forged_recommendation_does_not_pass_reference_check(self):
        original = self.input("big")
        fake = ModelFormRecommendation(original, "small", ("explicit_form",))
        with self.assertRaises(RoutingRefusal):
            preserve_recommendation(fake, original)
        with self.assertRaises(RoutingRefusal):
            presentation_reference(fake)

    def test_projection_is_non_authoritative(self):
        r = recommend(self.input(facts=(("task_complexity", "high"),)))
        p = presentation_reference(r)
        self.assertEqual(p["recommendedForm"], "big")
        self.assertIsNone(p["resolvedForm"])
        self.assertIsNone(p["resolvedBinding"])
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        for key in ("sourceAuthenticated", "permissionGranted",
                    "productionAuthority", "modelExecutionPermitted"):
            self.assertFalse(p[key])
        self.assertEqual(p["safeActions"], [])
        self.assertNotIn("fixture-producer", str(p))
        self.assertNotIn("owner-a", str(p))

    def test_frozen_recommendation_and_reasoning(self):
        r = recommend(self.input())
        with self.assertRaises(FrozenInstanceError):
            r.form = "big"
        with self.assertRaises(FrozenInstanceError):
            self.reasoning.mode = "deep"


if __name__ == "__main__":
    unittest.main()
