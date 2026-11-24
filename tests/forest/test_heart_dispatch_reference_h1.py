from dataclasses import replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
import heart_dispatch_reference_h1 as H
import model_binding_i2 as B
import model_form_routing_i1 as R
from shared_context_b6r1 import TaskContext
from resource_governor_p1 import ResourceRequest, ResourceRequirement, ResourceBudget, ResourceAvailability


def fixture(*, form="small", clone=None, origin="INTERACTIVE", features=("chat",)):
    ctx = TaskContext("owner", "tree", clone, "task", "execution", 1, origin)
    scope = R.TurnScope(ctx, "turn")
    reasoning = R.ReasoningReference(scope, "normal", "explicit")
    recommendation = R.recommend(R.RoutingInput(scope, form, reasoning))
    settings = H.TransportSettings("example:latest", 2048, 128)
    identity = B.ModelIdentity(settings.model, "sha256:"+"a"*64, "ollama",
                               "runtime", "1.0", "sha256:"+"b"*64)
    binding = B.ModelBinding("binding", recommendation.form, identity,
                             settings.config_digest, 2048, 128)
    registry = B.BindingRegistry("owner", "tree", 1, (binding,))
    evidence = B.BindingEvidence(scope, binding, "producer", "observation", True,
                                 ("chat",), 2048)
    result = B.resolve_reference(recommendation, registry, required_features=features,
                                 evidence=evidence)
    req = ResourceRequest("task", "execution", recommendation.form, "normal",
                          "interactive", "heart")
    return H.DispatchSnapshot(result, settings, "operation", "attempt", "clock",
                              100, req, ResourceRequirement(req, "requirements", 512, 256, 2),
                              ResourceBudget("budget", 1024, 512, 4),
                              ResourceAvailability("available", 1024, 512, 4))


class DispatchTests(unittest.TestCase):
    def compare(self, original=None, current=None, now=300):
        original = fixture() if original is None else original
        current = replace(original, captured_ns=200) if current is None else current
        return H.compare_dispatch(original, current, now_ns=now)

    def test_matching_references_never_authorize(self):
        r = self.compare()
        self.assertEqual(r["reason"], "REFERENCE_MATCH_AUTHORITY_HOLD")
        self.assertEqual(r["modeled_outcome"], "approve")
        self.assertTrue(r["dispatch_reference_matched"])
        self.assertEqual(r["status"], "UNKNOWN_HOLD")
        for key in ("source_authenticated", "freshness_verified", "resource_reserved",
                    "safe_to_start_inference", "permission_granted", "production_authority"):
            self.assertIs(r[key], False)
        self.assertEqual(r["safe_actions"], [])
        for private in ("example:latest", "operation", "attempt", "owner", "sha256:"):
            self.assertNotIn(private, str(r))

    def test_time_limits(self):
        s = fixture()
        self.assertEqual(self.compare(s, now=s.captured_ns+H.MAX_AGE_NS)["reason"],
                         "REFERENCE_MATCH_AUTHORITY_HOLD")
        for current, now, reason in (
            (replace(s, captured_ns=200), s.captured_ns+H.MAX_AGE_NS+1, "REFERENCE_EXPIRED"),
            (replace(s, captured_ns=99), 300, "CLOCK_ORDER_INVALID"),
            (replace(s, captured_ns=100), 300, "CLOCK_ORDER_INVALID"),
            (replace(s, captured_ns=400), 300, "CLOCK_ORDER_INVALID"),
            (replace(s, captured_ns=200, clock_domain="other"), 300, "CLOCK_DOMAIN_CHANGED"),
            (replace(s, captured_ns=200), True, "INVALID_CLOCK_REFERENCE"),
        ):
            with self.subTest(reason=reason):
                self.assertEqual(self.compare(s, current, now)["reason"], reason)

    def test_original_operation_attempt_cannot_change(self):
        s = fixture()
        for changes in ({"operation_id": "different"}, {"attempt_id": "different"}):
            current = replace(s, captured_ns=200, **changes)
            self.assertEqual(self.compare(s, current)["reason"], "DISPATCH_REFERENCE_CHANGED")

    def test_settings_fingerprint_and_exact_binding(self):
        s = fixture()
        for settings in (replace(s.settings, model="other:latest"),
                         replace(s.settings, num_ctx=4096),
                         replace(s.settings, max_predict=256)):
            self.assertNotEqual(settings.config_digest, s.settings.config_digest)
            current = replace(s, captured_ns=200, settings=settings)
            self.assertEqual(self.compare(s, current)["reason"], "TRANSPORT_BINDING_MISMATCH")

    def test_unresolved_and_forged_binding(self):
        s = fixture()
        b = s.binding
        for result, reason in (
            (B.resolve_reference(b.recommendation, b.registry, required_features=("chat",)),
             "MODEL_BINDING_UNRESOLVED"),
            (replace(b, reason="FAKE"), "INVALID_BINDING_REFERENCE"),
        ):
            self.assertEqual(self.compare(replace(s, binding=result))["reason"], reason)

    def test_scope_mismatch(self):
        s = fixture()
        for field, value in (("task_id", "other"), ("execution_context_id", "other"),
                             ("model_form", "big"), ("reasoning_mode", "deep")):
            req = replace(s.request, **{field: value})
            changed = replace(s, request=req, requirement=replace(s.requirement, request=req))
            self.assertEqual(self.compare(changed)["reason"], "RESOURCE_SCOPE_MISMATCH")

    def test_first_tree_scope_and_explicit_model(self):
        for s, reason in (
            (fixture(clone="clone"), "FIRST_TREE_SCOPE_UNSUPPORTED"),
            (fixture(origin="BACKGROUND"), "FIRST_TREE_SCOPE_UNSUPPORTED"),
            (fixture(form="auto"), "EXPLICIT_FORM_REQUIRED"),
            (fixture(features=()), "CHAT_CAPABILITY_REQUIRED"),
        ):
            self.assertEqual(self.compare(s)["reason"], reason)

    def test_requirements_and_budget_unknown_zero(self):
        s = fixture()
        for field in H.DIMENSIONS:
            for field_value, reason in ((None, "MODELED_RESOURCE_NOT_FIT"),
                                        (0, "ZERO_DEMAND_UNESTABLISHED")):
                changed = replace(s, requirement=replace(s.requirement, **{field: field_value}))
                self.assertEqual(self.compare(changed)["reason"], reason)
            changed = replace(s, budget=replace(s.budget, **{field: None}))
            self.assertEqual(self.compare(changed)["reason"], "EXPLICIT_BUDGET_REQUIRED")

    def test_known_budget_excess_denied(self):
        s = fixture()
        changed = replace(s, budget=replace(s.budget, memory_mib=1))
        r = self.compare(changed)
        self.assertEqual(r["modeled_outcome"], "deny")
        self.assertFalse(r["dispatch_reference_matched"])

    def test_availability_changed_even_if_still_fits(self):
        s = fixture()
        for value, outcome in ((900, "approve"), (1, "defer"), (None, "defer")):
            current = replace(s, captured_ns=200,
                              availability=replace(s.availability, memory_mib=value))
            r = self.compare(s, current)
            self.assertEqual(r["reason"], "DISPATCH_REFERENCE_CHANGED")
            self.assertEqual(r["modeled_outcome"], outcome)
            self.assertFalse(r["dispatch_reference_matched"])

    def test_model_evidence_or_revision_changed(self):
        s = fixture()
        b = s.binding
        for registry, evidence in (
            (replace(b.registry, revision=2), b.evidence),
            (b.registry, replace(b.evidence, observation_id="new-observation")),
        ):
            changed = B.resolve_reference(b.recommendation, registry, required_features=b.required_features,
                                          evidence=evidence)
            current = replace(s, captured_ns=200, binding=changed)
            self.assertEqual(self.compare(s, current)["reason"], "DISPATCH_REFERENCE_CHANGED")

    def test_strict_types_and_request_identity(self):
        s = fixture()
        for kwargs in ({"num_ctx": True}, {"num_ctx": 511}, {"max_predict": 513}):
            with self.assertRaises(H.DispatchRefusal):
                replace(s.settings, **kwargs)
        with self.assertRaisesRegex(H.DispatchRefusal, "REQUIREMENT_REQUEST_MISMATCH"):
            replace(s, requirement=replace(s.requirement, request=replace(s.request)))
        self.assertEqual(H.compare_dispatch({}, s, now_ns=300)["reason"], "INVALID_SNAPSHOT")
