"""Opt-in requirement-strength helpers. No source rewriting or host operations.

This module is deliberately small: a source match is not a native behavior
witness. Tests must call the appropriate level and supply real evidence.
"""
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence


LEVELS = ("EXACT", "STRUCTURAL", "BEHAVIOR", "NATIVE")


@dataclass(frozen=True)
class Contract:
    requirement_id: str
    owner: str
    rationale: str
    level: str

    def __post_init__(self):
        if (not self.requirement_id.strip() or not self.owner.strip()
                or not self.rationale.strip() or self.level not in LEVELS):
            raise ValueError("INVALID_CONTRACT_DECLARATION")


def _level(contract: Contract, expected: str) -> None:
    if not isinstance(contract, Contract) or contract.level != expected:
        raise AssertionError("CONTRACT_LEVEL_MISMATCH")


def exact_source(contract: Contract, source: str, literal: str) -> None:
    """Pin operator-approved source spelling, even if behavior still works."""
    _level(contract, "EXACT")
    if not literal or literal not in source:
        raise AssertionError(f"{contract.requirement_id}: EXACT_SOURCE_MISSING")


def structural_invariants(
    contract: Contract, checks: Sequence[tuple[str, bool]]
) -> None:
    """Check ownership/layout constraints independent of incidental spelling.

    The caller should derive boolean witnesses from actual source analysis,
    preferably a parser, imports or component bindings. A plain contains()
    is still a source-text check and must not be presented as native evidence.
    """
    _level(contract, "STRUCTURAL")
    if not checks:
        raise AssertionError(f"{contract.requirement_id}: NO_STRUCTURE_CHECKS")
    for name, passed in checks:
        if not name or type(passed) is not bool or not passed:
            raise AssertionError(
                f"{contract.requirement_id}: STRUCTURE_FAILED: {name}"
            )


def behavior_cases(
    contract: Contract,
    actual: Callable,
    cases: Iterable[tuple[tuple, object]],
) -> None:
    """Run real pure-function inputs; mismatches and missing cases fail."""
    _level(contract, "BEHAVIOR")
    count = 0
    for args, expected in cases:
        count += 1
        observed = actual(*args)
        if observed != expected:
            raise AssertionError(
                f"{contract.requirement_id}: BEHAVIOR_MISMATCH_CASE_{count}"
            )
    if count == 0:
        raise AssertionError(f"{contract.requirement_id}: NO_BEHAVIOR_CASES")


def native_fixture_required(contract: Contract, evidence: bool) -> None:
    """Assert a caller-supplied native-runner result, never simulate one.

    This helper cannot launch QML or verify pixels. Use only with a real
    disposable native fixture's result, never a hardcoded True.
    """
    _level(contract, "NATIVE")
    if evidence is not True:
        raise AssertionError(f"{contract.requirement_id}: NATIVE_NOT_VERIFIED")
