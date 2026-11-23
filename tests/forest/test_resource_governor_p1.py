"""Forest P1 // synthetic-only resource policy negative and precedence matrix."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/forest"))
import resource_governor_p1 as p1


def request(**values):
    data = dict(task_id="turn-1", execution_context_id="tree-A",
                model_form="small", reasoning_mode="normal",
                priority="interactive", source="synthetic-test")
    data.update(values)
    return p1.ResourceRequest(**data)


def scenario(req=None, *, need=None, ceiling=None, available=None):
    req = request() if req is None else req
    need = dict(memory_mib=500, accelerator_memory_mib=120, cpu_threads=2) if need is None else need
    ceiling = dict(memory_mib=800, accelerator_memory_mib=256, cpu_threads=4) if ceiling is None else ceiling
    available = dict(memory_mib=600, accelerator_memory_mib=180, cpu_threads=3) if available is None else available
    return (
        req, p1.ResourceRequirement(request=req, source="synthetic", **need),
        p1.ResourceBudget(source="synthetic", **ceiling),
        p1.ResourceAvailability(source="synthetic", **available),
    )


class GovernorP1Tests(unittest.TestCase):
    def evaluate(self, *args):
        return p1.evaluate_resource_request(*args)

    def test_approve_exact_known_fit_is_not_runtime_permission(self):
        r = self.evaluate(*scenario())
        self.assertEqual(r.outcome, "approve")
        self.assertFalse(r.production_authority)
        self.assertFalse(r.permission_granted)
        self.assertFalse(r.safe_to_start_inference)
        self.assertEqual(r.authority_scope, p1.AUTHORITY_SCOPE)

    def test_budget_violation_denies_before_unknown_availability(self):
        args = scenario(
            need=dict(memory_mib=801, accelerator_memory_mib=120, cpu_threads=2),
            available=dict(memory_mib=None, accelerator_memory_mib=None, cpu_threads=None))
        r = self.evaluate(*args)
        self.assertEqual(r.outcome, "deny")
        self.assertEqual(r.reasons, ("memory_mib requirement exceeds explicit budget",))

    def test_multiple_budget_violations_have_deterministic_order(self):
        args = scenario(need=dict(memory_mib=900, accelerator_memory_mib=300,
                                  cpu_threads=9))
        r = self.evaluate(*args)
        self.assertEqual(r.outcome, "deny")
        self.assertEqual(len(r.reasons), 3)
        self.assertEqual(r.reasons[0].split()[0], "memory_mib")
        self.assertEqual(r.reasons[1].split()[0], "accelerator_memory_mib")
        self.assertEqual(r.reasons[2].split()[0], "cpu_threads")

    def test_budget_violation_denies_even_when_deferral_allowed(self):
        req = request(may_defer=True)
        r = self.evaluate(*scenario(req,
            ceiling=dict(memory_mib=100, accelerator_memory_mib=256, cpu_threads=4)))
        self.assertEqual(r.outcome, "deny")

    def test_unknown_requirement_defers_when_allowed(self):
        req = request(may_defer=True)
        r = self.evaluate(*scenario(req, need=dict(memory_mib=None,
            accelerator_memory_mib=0, cpu_threads=1)))
        self.assertEqual(r.outcome, "defer")
        self.assertIn("memory_mib", r.reasons[0])

    def test_unknown_requirement_denies_when_not_deferrable(self):
        req = request(may_defer=False)
        r = self.evaluate(*scenario(req, need=dict(memory_mib=None,
            accelerator_memory_mib=0, cpu_threads=1)))
        self.assertEqual(r.outcome, "deny")

    def test_unknown_requirement_precedes_insufficient_availability(self):
        r = self.evaluate(*scenario(
            need=dict(memory_mib=None, accelerator_memory_mib=0, cpu_threads=2),
            available=dict(memory_mib=0, accelerator_memory_mib=0, cpu_threads=0)))
        self.assertEqual(r.outcome, "defer")
        self.assertTrue(r.reasons[0].startswith("Unknown requirement"))

    def test_unknown_availability_defers(self):
        r = self.evaluate(*scenario(available=dict(
            memory_mib=None, accelerator_memory_mib=180, cpu_threads=3)))
        self.assertEqual(r.outcome, "defer")
        self.assertIn("memory_mib", r.reasons[0])

    def test_unknown_availability_denies_nondeferrable(self):
        req = request(may_defer=False)
        r = self.evaluate(*scenario(req, available=dict(
            memory_mib=None, accelerator_memory_mib=180, cpu_threads=3)))
        self.assertEqual(r.outcome, "deny")

    def test_insufficient_available_memory_defers(self):
        r = self.evaluate(*scenario(available=dict(
            memory_mib=499, accelerator_memory_mib=180, cpu_threads=3)))
        self.assertEqual(r.outcome, "defer")
        self.assertIn("memory_mib", r.reasons[0])

    def test_insufficient_available_cpu_denies_nondeferrable(self):
        req = request(may_defer=False)
        r = self.evaluate(*scenario(req, available=dict(
            memory_mib=600, accelerator_memory_mib=180, cpu_threads=1)))
        self.assertEqual(r.outcome, "deny")
        self.assertIn("cpu_threads", r.reasons[0])

    def test_mixed_unknown_and_insufficient_reasons_order(self):
        r = self.evaluate(*scenario(available=dict(
            memory_mib=None, accelerator_memory_mib=100, cpu_threads=1)))
        self.assertEqual(r.outcome, "defer")
        self.assertEqual(len(r.reasons), 2)
        self.assertIn("Unknown availability", r.reasons[0])
        self.assertIn("Insufficient availability", r.reasons[1])

    def test_zero_requirement_ignores_unknown_availability(self):
        r = self.evaluate(*scenario(
            need=dict(memory_mib=0, accelerator_memory_mib=0, cpu_threads=0),
            available=dict(memory_mib=None, accelerator_memory_mib=None,
                           cpu_threads=None)))
        self.assertEqual(r.outcome, "approve")

    def test_zero_requirement_is_not_null(self):
        r = self.evaluate(*scenario(
            need=dict(memory_mib=0, accelerator_memory_mib=None, cpu_threads=0)))
        self.assertEqual(r.outcome, "defer")

    def test_none_budget_is_not_zero_ceiling(self):
        r = self.evaluate(*scenario(
            ceiling=dict(memory_mib=None, accelerator_memory_mib=None,
                         cpu_threads=None)))
        self.assertEqual(r.outcome, "approve")

    def test_none_budget_still_respects_insufficient_availability(self):
        r = self.evaluate(*scenario(
            ceiling=dict(memory_mib=None, accelerator_memory_mib=None,
                         cpu_threads=None),
            available=dict(memory_mib=100, accelerator_memory_mib=180,
                           cpu_threads=3)))
        self.assertEqual(r.outcome, "defer")

    def test_exact_limits_allow_fit(self):
        r = self.evaluate(*scenario(
            available=dict(memory_mib=500, accelerator_memory_mib=120,
                           cpu_threads=2),
            ceiling=dict(memory_mib=500, accelerator_memory_mib=120,
                         cpu_threads=2)))
        self.assertEqual(r.outcome, "approve")

    def test_explicit_measured_zero_is_not_unknown(self):
        r = self.evaluate(*scenario(available=dict(
            memory_mib=0, accelerator_memory_mib=180, cpu_threads=3)))
        self.assertEqual(r.outcome, "defer")
        self.assertIn("Insufficient availability", r.reasons[0])

    def test_requirement_must_be_bound_to_same_object_not_equal_clone(self):
        original = request()
        clone = replace(original)
        self.assertEqual(original, clone)
        self.assertIsNot(original, clone)
        other = scenario(original)
        with self.assertRaisesRegex(p1.ResourcePolicyRefusal,
                                    "REQUIREMENT_REQUEST_MISMATCH"):
            self.evaluate(clone, other[1], other[2], other[3])

    def test_rejects_invalid_argument_objects(self):
        args = list(scenario())
        for i in range(4):
            modified = args.copy()
            modified[i] = object()
            with self.subTest(i=i):
                with self.assertRaisesRegex(p1.ResourcePolicyRefusal,
                                            "INVALID_GOVERNOR_ARGUMENTS"):
                    self.evaluate(*modified)

    def test_rejects_non_request_binding_at_construction(self):
        with self.assertRaisesRegex(p1.ResourcePolicyRefusal,
                                    "INVALID_REQUEST_BINDING"):
            p1.ResourceRequirement(request="turn-1", source="synthetic")

    def test_request_modes_are_frozen_and_not_downgraded(self):
        req = request(model_form=" Big ", reasoning_mode=" Deep ", priority=" Interactive ")
        r = self.evaluate(*scenario(req))
        self.assertIs(r.request, req)
        self.assertEqual(r.request.model_form, "big")
        self.assertEqual(r.request.reasoning_mode, "deep")
        self.assertEqual(r.request.priority, "interactive")

    def test_historical_reasoning_aliases(self):
        self.assertEqual(request(reasoning_mode="quick").reasoning_mode, "light")
        self.assertEqual(request(reasoning_mode="standard").reasoning_mode, "normal")

    def test_rejects_auto_or_vendor_model_form(self):
        for value in ("auto", "qwen3:1.7b", "", None, 3):
            with self.subTest(value=value):
                with self.assertRaises(p1.ResourcePolicyRefusal):
                    request(model_form=value)

    def test_rejects_invalid_reasoning_and_priority(self):
        for field, values in (("reasoning_mode", ("reasoning-too-high", "", None)),
                              ("priority", ("maximum", 2, None))):
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises(p1.ResourcePolicyRefusal):
                        request(**{field: value})

    def test_rejects_invalid_or_oversized_identifiers(self):
        for field in ("task_id", "execution_context_id", "source"):
            for value in ("", "  ", None, 42, "a" * 257):
                with self.subTest(field=field, value=str(value)[:8]):
                    with self.assertRaises(p1.ResourcePolicyRefusal):
                        request(**{field: value})

    def test_rejects_non_boolean_deferral(self):
        for value in (0, 1, None, "true"):
            with self.subTest(value=value):
                with self.assertRaises(p1.ResourcePolicyRefusal):
                    request(may_defer=value)

    def test_rejects_bad_measurements_in_every_dimension_and_contract(self):
        for cls in (p1.ResourceRequirement, p1.ResourceBudget,
                    p1.ResourceAvailability):
            for field in p1.DIMENSIONS:
                for value in (True, False, -1, 0.5, "128", 2**64):
                    kwargs = {"source": "synthetic", field: value}
                    if cls is p1.ResourceRequirement:
                        kwargs["request"] = request()
                    with self.subTest(cls=cls.__name__, field=field, value=value):
                        with self.assertRaises(p1.ResourcePolicyRefusal):
                            cls(**kwargs)

    def test_unknown_all_dimensions_still_defers(self):
        req = request()
        r = self.evaluate(req,
            p1.ResourceRequirement(req, "synthetic"),
            p1.ResourceBudget("synthetic"),
            p1.ResourceAvailability("synthetic"))
        self.assertEqual(r.outcome, "defer")

    def test_invalid_schema_versions_refused_in_every_dataclass(self):
        for cls, kwargs in (
            (p1.ResourceRequest, dict(task_id="t", execution_context_id="e",
                model_form="small", reasoning_mode="light", priority="standard",
                source="s")),
            (p1.ResourceRequirement, dict(request=request(), source="s")),
            (p1.ResourceBudget, dict(source="s")),
            (p1.ResourceAvailability, dict(source="s")),
            (p1.GovernorDecision, dict(request=request(),
                outcome="approve", source="s", reasons=("example",))),
        ):
            for schema in (True, 0, 2, "1"):
                with self.subTest(cls=cls.__name__, schema=schema):
                    with self.assertRaises(p1.ResourcePolicyRefusal):
                        cls(schema_version=schema, **kwargs)

    def test_results_are_frozen(self):
        r = self.evaluate(*scenario())
        with self.assertRaises(FrozenInstanceError):
            r.outcome = "deny"
        with self.assertRaises(FrozenInstanceError):
            r.production_authority = True
        with self.assertRaises(FrozenInstanceError):
            r.request.model_form = "big"

    def test_forbids_constructing_true_authorization_flags(self):
        r = self.evaluate(*scenario())
        for field in ("permission_granted", "production_authority",
                      "safe_to_start_inference", "authority_scope"):
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    p1.GovernorDecision(request=r.request, outcome="approve",
                        source="s", reasons=("resource fit",),
                        **{field: True})

    def test_reasons_are_tuple_not_raw_prompt(self):
        for reasons in (["message"], ("",), (42,), tuple("a" for _ in range(33))):
            with self.subTest(reasons=str(reasons)[:20]):
                with self.assertRaises(p1.ResourcePolicyRefusal):
                    request(reasons=reasons)

    def test_no_runtime_or_network_imports(self):
        source = (Path(__file__).resolve().parents[2] /
                  "scripts/forest/resource_governor_p1.py").read_text()
        for token in ("socket", "urllib", "http.client", "subprocess",
                      "requests", "os.system", "open(", "/api/chat",
                      "ollama", "psutil"):
            with self.subTest(token=token):
                self.assertNotIn(token, source.lower())
        self.assertFalse(hasattr(p1, "main"))


if __name__ == "__main__":
    unittest.main()
