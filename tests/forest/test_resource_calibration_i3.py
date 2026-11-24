from dataclasses import replace, FrozenInstanceError
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "forest"))
from shared_context_b6r1 import TaskContext
from model_form_routing_i1 import TurnScope, ReasoningReference, RoutingInput, recommend
from model_binding_i2 import ModelIdentity, ModelBinding, BindingRegistry, BindingEvidence, resolve_reference
from resource_calibration_i3 import (
    CalibrationProfile, MemoryObservation, TrialReference, CalibrationRefusal,
    summarize, match_turn, public_summary,
)

def digest(c):
    return "sha256:" + c * 64


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.scope = TurnScope(TaskContext("owner", "bristlecone", None,
                              "task", "context", 1, "INTERACTIVE"), "turn")
        route = recommend(RoutingInput(self.scope, "big",
                                      ReasoningReference(self.scope, "deep", "explicit")))
        identity = ModelIdentity("fixture:big", digest("a"), "ollama",
                                 "runtime", "0.0.1", digest("b"))
        self.binding = ModelBinding("big-binding", "big", identity, digest("c"), 4096, 256)
        registry = BindingRegistry("owner", "bristlecone", 1, (self.binding,))
        evidence = BindingEvidence(self.scope, self.binding, "fixture", "obs",
                                   True, ("chat",), 8192)
        self.result = resolve_reference(route, registry, required_features=("chat",), evidence=evidence)
        self.profile = CalibrationProfile(self.binding, "machine", "boot", digest("d"),
                         "scope", "device-a", digest("e"), digest("f"), "deep",
                         "warm", 1024, 4)
        self.trial = TrialReference(self.profile, "trial-a", "observer", "complete",
                          True, MemoryObservation(100, 301), MemoryObservation(50, 250),
                          10, 20, 30, 32)

    def test_incremental_is_not_peak(self):
        s = summarize(self.profile, (self.trial,))
        self.assertEqual((s.host_peak_bytes, s.host_incremental_bytes), (301, 201))
        self.assertEqual((s.accelerator_peak_bytes, s.accelerator_incremental_bytes), (250, 200))

    def test_max_of_per_trial_deltas_not_difference_of_maxima(self):
        second = replace(self.trial, trial_id="trial-b", host=MemoryObservation(1000, 1100))
        s = summarize(self.profile, (self.trial, second))
        self.assertEqual((s.host_peak_bytes, s.host_incremental_bytes), (1100, 201))

    def test_unknown_propagates_per_dimension(self):
        second = replace(self.trial, trial_id="trial-b", host=MemoryObservation(None, 900))
        s = summarize(self.profile, (self.trial, second))
        self.assertEqual(s.host_peak_bytes, 900)
        self.assertIsNone(s.host_incremental_bytes)
        self.assertEqual(s.accelerator_incremental_bytes, 200)

    def test_missing_peak_not_partial_maximum(self):
        second = replace(self.trial, trial_id="trial-b", host=MemoryObservation(100, None))
        s = summarize(self.profile, (self.trial, second))
        self.assertIsNone(s.host_peak_bytes)
        self.assertIsNone(s.host_incremental_bytes)

    def test_zero_observed_delta_distinct_from_unknown(self):
        self.assertEqual(MemoryObservation(10, 10).incremental_bytes, 0)
        self.assertIsNone(MemoryObservation(10, None).incremental_bytes)

    def test_no_device_target_does_not_prove_zero_vram(self):
        p = replace(self.profile, accelerator_id=None)
        t = replace(self.trial, profile=p, accelerator=None)
        self.assertIsNone(summarize(p, (t,)).accelerator_incremental_bytes)

    def test_unbound_accelerator_refused(self):
        with self.assertRaises(CalibrationRefusal):
            replace(self.trial, profile=replace(self.profile, accelerator_id=None))

    def test_mixed_profiles_refused(self):
        for changes in ({"machine_id": "other"}, {"boot_id": "other"},
                        {"hardware_digest": digest("1")}, {"measurement_scope_id": "other"},
                        {"accelerator_id": "other"}, {"workload_digest": digest("1")},
                        {"baseline_state_digest": digest("1")}, {"reasoning_mode": "light"},
                        {"residency": "cold"}, {"prompt_tokens": 2048},
                        {"cpu_thread_limit": 8},
                        {"binding": replace(self.binding, config_digest=digest("1"))}):
            with self.subTest(changes=changes), self.assertRaisesRegex(CalibrationRefusal, "PROFILE_MISMATCH"):
                summarize(self.profile, (replace(self.trial, profile=replace(self.profile, **changes)),))

    def test_duplicate_trial_refused(self):
        with self.assertRaisesRegex(CalibrationRefusal, "DUPLICATE_TRIAL"):
            summarize(self.profile, (self.trial, self.trial))

    def test_cold_and_warm_counts(self):
        p = replace(self.profile, residency="cold")
        t = replace(self.trial, profile=p)
        self.assertEqual(summarize(p, (t,)).reason, "OBSERVED_REFERENCE_ONLY")
        with self.assertRaisesRegex(CalibrationRefusal, "COLD_TRIAL_COUNT"):
            summarize(p, (t, replace(t, trial_id="trial-b")))
        with self.assertRaisesRegex(CalibrationRefusal, "WARM_TRIAL_COUNT"):
            summarize(self.profile, tuple(replace(self.trial, trial_id="trial-"+str(i)) for i in range(4)))

    def test_incomplete_campaign_not_cherry_picked(self):
        second = replace(self.trial, trial_id="trial-b", outcome="incomplete",
                         completion_ns=None)
        s = summarize(self.profile, (self.trial, second))
        self.assertEqual(s.reason, "INCOMPLETE_CAMPAIGN")
        self.assertIsNone(s.host_peak_bytes)

    def test_incomplete_coverage_invalidates_summary(self):
        s = summarize(self.profile, (replace(self.trial, coverage_complete=False),))
        self.assertEqual(s.reason, "INCOMPLETE_CAMPAIGN")

    def test_invalid_measurements_refused(self):
        for baseline, peak in ((20, 10), (-1, 10), (True, 10), (0, 2**63), (1.5, 2)):
            with self.assertRaises(CalibrationRefusal):
                MemoryObservation(baseline, peak)

    def test_invalid_timing_and_output_refused(self):
        for changes in ({"first_content_ns": 31}, {"load_ns": 31},
                        {"completion_ns": -1}, {"generated_tokens": 257},
                        {"outcome": "refused"}, {"coverage_complete": 1}):
            with self.assertRaises(CalibrationRefusal):
                replace(self.trial, **changes)

    def test_context_bounds(self):
        with self.assertRaises(CalibrationRefusal):
            replace(self.profile, prompt_tokens=4000)
        with self.assertRaises(CalibrationRefusal):
            replace(self.profile, cpu_thread_limit=True)

    def test_exact_turn_match_and_reasoning(self):
        self.assertTrue(match_turn(self.result, self.profile))
        self.assertFalse(match_turn(self.result, replace(self.profile, reasoning_mode="normal")))
        self.assertFalse(match_turn(self.result, replace(self.profile,
                       binding=replace(self.binding, config_digest=digest("1")))))

    def test_unresolved_or_forged_binding_refused(self):
        missing = resolve_reference(self.result.recommendation, self.result.registry,
                                    required_features=("chat",))
        self.assertFalse(match_turn(missing, self.profile))
        with self.assertRaises(CalibrationRefusal):
            match_turn(replace(missing, binding=self.binding), self.profile)

    def test_public_summary_rounds_up_not_down(self):
        t = replace(self.trial, host=MemoryObservation(0, 1048577))
        p = public_summary(summarize(self.profile, (t,)))
        self.assertEqual(p["hostObservedPeakMiB"], 2)
        self.assertEqual(p["hostObservedIncrementalMiB"], 2)
        self.assertIsNone(p["hostRequirementMiB"])

    def test_no_authority_or_inferred_requirement(self):
        s = summarize(self.profile, (self.trial,))
        p = public_summary(s)
        self.assertEqual(p["status"], "UNKNOWN_HOLD")
        for field in ("requirementsEstablished", "availabilityEstablished", "resourceReserved",
                      "sourceAuthenticated", "permissionGranted", "productionAuthority",
                      "modelExecutionPermitted"):
            self.assertFalse(p[field])
        self.assertIsNone(p["cpuRequirementThreads"])
        self.assertIsNone(p["acceleratorRequirementMiB"])
        self.assertNotIn("machine", str(p))
        self.assertNotIn("fixture:big", str(p))
        self.assertEqual(p["safeActions"], [])

    def test_forged_summary_refused_and_immutable(self):
        s = summarize(self.profile, (self.trial,))
        with self.assertRaises(CalibrationRefusal):
            public_summary(replace(s, host_peak_bytes=1))
        with self.assertRaises(FrozenInstanceError):
            s.host_peak_bytes = 1


if __name__ == "__main__":
    unittest.main()
