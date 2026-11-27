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
    FormControlReference, controlled_routing_input,
    ReasoningLeaseReference, ReasoningControlReference, controlled_reasoning_reference,
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



class FormControlReferenceTests(unittest.TestCase):
    def setUp(self):
        self.scope = TurnScope(TaskContext("owner-a", "bristlecone", None,
                                "task-a", "context-a", 1, "INTERACTIVE"), "turn-a")
        self.reasoning = ReasoningReference(self.scope, "normal", "explicit")
        self.base = FormControlReference(self.scope, 1, "COMPLETE", baseline="auto")
        self.high = (SemanticEvidence(self.scope, "task_complexity", "high", "fixture"),)

    def route(self, control, current=None):
        return controlled_routing_input(control, control if current is None else current,
                                       reasoning=self.reasoning, evidence=self.high)

    def test_original_form_precedence(self):
        task = replace(self.base, task_form="small", task_context=self.scope.context,
                       baseline="big", tree_default="big")
        exact = replace(task, exact_form="big")
        self.assertEqual(recommend(self.route(exact)).form, "big")
        self.assertEqual(recommend(self.route(task)).form, "small")
        self.assertEqual(recommend(self.route(replace(task, task_form=None,
                                                     task_context=None))).form, "big")
        self.assertEqual(recommend(self.route(self.base)).form, "big")

    def test_context_auto_does_not_inherit_tree_pin(self):
        control = replace(self.base, tree_default="small")
        self.assertEqual(self.route(control).requested_form, "auto")
        self.assertEqual(recommend(self.route(control)).form, "big")

    def test_authorized_absent_baseline_uses_tree_default_only(self):
        control = replace(self.base, baseline=None, tree_default="small")
        self.assertEqual(recommend(self.route(control)).form, "small")
        with self.assertRaisesRegex(RoutingRefusal, "CONTROL_COVERAGE_HOLD"):
            self.route(replace(control, tree_default=None))

    def test_unknown_coverage_never_falls_through_even_exact(self):
        for exact in (None, "big"):
            control = replace(self.base, coverage="UNKNOWN", exact_form=exact,
                              tree_default="small")
            with self.assertRaisesRegex(RoutingRefusal, "CONTROL_COVERAGE_HOLD"):
                self.route(control)
        with self.assertRaises(RoutingRefusal):
            controlled_routing_input(self.base, None, reasoning=self.reasoning)

    def test_changed_control_revision_or_content_refused(self):
        for changed in (replace(self.base, revision=2),
                        replace(self.base, baseline="small"),
                        replace(self.base, coverage="UNKNOWN")):
            with self.assertRaisesRegex(RoutingRefusal, "CONTROL_REFERENCE_CHANGED"):
                self.route(self.base, changed)

    def test_foreign_task_or_incarnation_not_treated_as_absence(self):
        for context in (replace(self.scope.context, task_id="task-b"),
                        replace(self.scope.context, generation=2),
                        replace(self.scope.context, clone_key="clone-a")):
            with self.assertRaisesRegex(RoutingRefusal, "CONTROL_SCOPE_MISMATCH"):
                replace(self.base, task_form="small", task_context=context)
        other = replace(self.scope, turn_id="turn-b")
        with self.assertRaises(RoutingRefusal):
            self.route(replace(self.base, scope=other))

    def test_malformed_lower_priority_controls_refused(self):
        for fields in ({"baseline": "BIG"}, {"tree_default": True},
                       {"task_form": "auto", "task_context": self.scope.context},
                       {"task_form": "big"}, {"revision": True},
                       {"revision": 2**53}, {"coverage": False}):
            with self.assertRaises(RoutingRefusal):
                replace(self.base, exact_form="small", **fields)

    def test_control_lineage_retained_even_when_selected_form_unchanged(self):
        original = self.route(replace(self.base, exact_form="small"))
        decision = recommend(original)
        self.assertIs(preserve_recommendation(decision, original), decision)
        changed = self.route(replace(original.control, revision=2))
        self.assertEqual(recommend(changed).form, decision.form)
        with self.assertRaisesRegex(RoutingRefusal, "ROUTING_INPUT_CHANGED"):
            preserve_recommendation(decision, changed)
        with self.assertRaisesRegex(RoutingRefusal, "ROUTING_INPUT_CHANGED"):
            preserve_recommendation(decision, replace(original, control=None))
        with self.assertRaisesRegex(RoutingRefusal, "CONTROL_FORM_MISMATCH"):
            replace(original, requested_form="big")

    def test_existing_evidence_validation_and_non_authority_preserved(self):
        bad = (SemanticEvidence(self.scope, "task_complexity", "extreme", "fixture"),)
        controlled = controlled_routing_input(
            replace(self.base, exact_form="small"),
            replace(self.base, exact_form="small"), reasoning=self.reasoning, evidence=bad)
        with self.assertRaisesRegex(RoutingRefusal, "INVALID_RECOGNIZED_EVIDENCE"):
            recommend(controlled)
        decision = recommend(self.route(self.base))
        view = presentation_reference(decision)
        self.assertEqual(view["status"], "UNKNOWN_HOLD")
        self.assertFalse(view["sourceAuthenticated"])
        self.assertFalse(view["permissionGranted"])
        self.assertFalse(view["modelExecutionPermitted"])
        self.assertIsNone(view["resolvedBinding"])
        self.assertNotIn("control", view)
        self.assertNotIn("owner-a", str(view))


class ReasoningControlReferenceTests(unittest.TestCase):
    def setUp(self):
        self.scope = TurnScope(TaskContext("owner-a", "bristlecone", None,
                                "task-a", "context-a", 1, "INTERACTIVE"), "turn-a")
        self.lease = ReasoningLeaseReference(self.scope.context, "lease-a", 1, "deep", 2)
        self.base = ReasoningControlReference(self.scope, 1, "COMPLETE", "auto",
                                              automatic_mode="normal")

    def select(self, control):
        return controlled_reasoning_reference(control, replace(control))

    def test_precedence_and_selected_lease(self):
        pinned = replace(self.base, baseline="light")
        temporary = replace(pinned, temporary=self.lease)
        explicit = replace(temporary, explicit_mode="normal")
        for control, mode, source, lease in (
                (explicit, "normal", "explicit", None),
                (temporary, "deep", "temporary", self.lease),
                (pinned, "light", "pinned", None),
                (self.base, "normal", "automatic", None)):
            with self.subTest(source=source):
                decision = self.select(control)
                self.assertEqual((decision.mode, decision.source), (mode, source))
                self.assertEqual(decision.selected_lease, lease)
                self.assertEqual(decision.control, control)
        self.assertEqual(self.lease.remaining, 2)

    def test_unknown_and_missing_auto_do_not_fall_back(self):
        for control in (replace(self.base, coverage="UNKNOWN"),
                        replace(self.base, coverage="UNKNOWN", explicit_mode="deep"),
                        replace(self.base, coverage="UNKNOWN", temporary=self.lease),
                        replace(self.base, automatic_mode=None)):
            with self.assertRaisesRegex(RoutingRefusal, "REASONING_COVERAGE_HOLD"):
                self.select(control)
        with self.assertRaises(RoutingRefusal):
            controlled_reasoning_reference(self.base, None)
        self.assertEqual(self.select(replace(self.base, automatic_mode=None,
                                            baseline="light")).mode, "light")

    def test_reference_changes_even_if_effective_mode_same(self):
        original = replace(self.base, temporary=self.lease, explicit_mode="deep")
        for current in (replace(original, revision=2),
                        replace(original, temporary=None),
                        replace(original, temporary=replace(self.lease, lease_id="lease-b")),
                        replace(original, temporary=replace(self.lease, revision=2)),
                        replace(original, temporary=replace(self.lease, remaining=1)),
                        replace(original, temporary=replace(self.lease, mode="normal")),
                        replace(original, scope=replace(self.scope, turn_id="turn-b"))):
            with self.assertRaisesRegex(RoutingRefusal, "REASONING_REFERENCE_CHANGED"):
                controlled_reasoning_reference(original, current)

    def test_foreign_execution_context_is_not_absence(self):
        for context in (replace(self.scope.context, task_id="task-b"),
                        replace(self.scope.context, generation=2),
                        replace(self.scope.context, clone_key="clone-a"),
                        replace(self.scope.context, principal_key="owner-b")):
            with self.assertRaisesRegex(RoutingRefusal, "REASONING_SCOPE_MISMATCH"):
                replace(self.base, temporary=replace(self.lease, context=context),
                        explicit_mode="deep")

    def test_malformed_controls_and_lease_bounds(self):
        for fields in ({"revision": True}, {"revision": 2**53},
                       {"coverage": "complete"}, {"baseline": None},
                       {"automatic_mode": "quick"}, {"explicit_mode": False},
                       {"temporary": "lease-a"}):
            with self.assertRaises(RoutingRefusal):
                replace(self.base, **fields)
        for fields in ({"lease_id": ""}, {"lease_id": "bad id"}, {"remaining": 0},
                       {"remaining": True}, {"remaining": 2**53},
                       {"revision": 0}, {"mode": "DEEP"}):
            with self.assertRaises(RoutingRefusal):
                replace(self.lease, **fields)

    def test_direct_mismatched_reasoning_reference_refused(self):
        decision = self.select(replace(self.base, temporary=self.lease))
        for fields in ({"mode": "normal"}, {"source": "explicit"},
                       {"source": "fallback"},
                       {"scope": replace(self.scope, turn_id="turn-b")}):
            with self.assertRaises(RoutingRefusal):
                replace(decision, **fields)

    def test_original_reasoning_lineage_retained_by_existing_i1(self):
        control = replace(self.base, temporary=self.lease)
        reasoning = self.select(control)
        form = FormControlReference(self.scope, 1, "COMPLETE", baseline="small")
        routing = controlled_routing_input(form, form, reasoning=reasoning)
        decision = recommend(routing)
        self.assertIs(preserve_recommendation(decision, routing), decision)
        for changed in (self.select(replace(control, revision=2)),
                        self.select(replace(control, temporary=replace(self.lease,
                                                                      lease_id="lease-b"))),
                        replace(reasoning, control=None)):
            with self.assertRaisesRegex(RoutingRefusal, "ROUTING_INPUT_CHANGED"):
                preserve_recommendation(decision, replace(routing, reasoning=changed))
        view = presentation_reference(decision)
        self.assertEqual(view["reasoningMode"], "deep")
        self.assertEqual(view["status"], "UNKNOWN_HOLD")
        self.assertFalse(view["sourceAuthenticated"])
        self.assertFalse(view["modelExecutionPermitted"])
        self.assertFalse(view["permissionGranted"])
        self.assertNotIn("lease-a", str(view))
        self.assertNotIn("control", view)

    def test_selection_is_pure_not_consumption_or_turn_reservation(self):
        control = replace(self.base, temporary=self.lease)
        a = self.select(control)
        b = self.select(control)
        self.assertEqual(a, b)
        self.assertEqual(a.selected_lease.remaining, 2)
        with self.assertRaises(FrozenInstanceError):
            a.selected_lease.remaining = 1
        next_scope = replace(self.scope, turn_id="turn-b")
        next_decision = self.select(replace(control, scope=next_scope))
        self.assertNotEqual(a, next_decision)
        self.assertEqual(next_decision.selected_lease.remaining, 2)
        # A second pure selection is not permission for another execution.
        self.assertFalse(recommend(RoutingInput(next_scope, "small",
                                                next_decision)).model_execution_permitted)


if __name__ == "__main__":
    unittest.main()
