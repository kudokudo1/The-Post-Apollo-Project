"""Self-test the distinctions; independent QML CI remains elsewhere."""
import unittest

from contract_levels import (
    Contract, behavior_cases, exact_source, native_fixture_required,
    structural_invariants,
)


def spec(level):
    return Contract(
        requirement_id="EXAMPLE-001",
        owner="TEST OWNER",
        rationale="Protect operator-approved requirement",
        level=level,
    )


class ContractStrengthTests(unittest.TestCase):
    def test_exact_must_preserve_operator_locked_spelling(self):
        contract = spec("EXACT")
        exact_source(contract, "readonly property bool writesReady: false",
                     "readonly property bool writesReady: false")
        with self.assertRaisesRegex(AssertionError, "EXACT_SOURCE_MISSING"):
            exact_source(contract, "property bool writesReady: false",
                         "readonly property bool writesReady: false")

    def test_structure_can_allow_refactoring_but_refuses_second_owner(self):
        contract = spec("STRUCTURAL")
        for implementation in (
            {"collector_owner": "KillStore", "collector_count": 1},
            {"collector_owner": "KillStore", "collector_count": 1,
             "read_only_consumers": 3},
        ):
            structural_invariants(contract, [
                ("shared collector owner",
                 implementation["collector_owner"] == "KillStore"),
                ("exactly one collector",
                 implementation["collector_count"] == 1),
            ])
        with self.assertRaisesRegex(AssertionError, "STRUCTURE_FAILED"):
            structural_invariants(contract, [
                ("exactly one collector", False),
            ])

    def test_behavior_survives_reimplementation_but_not_regression(self):
        contract = spec("BEHAVIOR")
        cases = [((2, 3), 5), ((-1, 1), 0), ((0, 0), 0)]
        behavior_cases(contract, lambda a, b: a + b, cases)
        behavior_cases(contract, lambda a, b: sum((a, b)), cases)
        with self.assertRaisesRegex(AssertionError, "BEHAVIOR_MISMATCH"):
            behavior_cases(contract, lambda a, b: a - b, cases)
        with self.assertRaisesRegex(AssertionError, "NO_BEHAVIOR_CASES"):
            behavior_cases(contract, lambda x: x, [])

    def test_native_without_actual_evidence_must_fail(self):
        with self.assertRaisesRegex(AssertionError, "NATIVE_NOT_VERIFIED"):
            native_fixture_required(spec("NATIVE"), False)

    def test_levels_cannot_be_silently_substituted(self):
        with self.assertRaisesRegex(AssertionError, "CONTRACT_LEVEL_MISMATCH"):
            exact_source(spec("BEHAVIOR"), "whatever", "whatever")

    def test_declarations_require_owner_reason_and_valid_level(self):
        with self.assertRaises(ValueError):
            Contract("EXAMPLE-002", "", "reason", "EXACT")
        with self.assertRaises(ValueError):
            Contract("EXAMPLE-002", "owner", "", "EXACT")
        with self.assertRaises(ValueError):
            Contract("EXAMPLE-002", "owner", "reason", "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
