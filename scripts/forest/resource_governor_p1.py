"""Forest Performance P1 // synthetic-only, pure resource decision contract.

Adapted from Forest's frozen historical Bristlecone resource governor.
No hardware probes, model calls, scheduling, queue, IO or authorization.
APPROVE means modeled resource fit, never consent or permission to execute.
"""
from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1
DIMENSIONS = ("memory_mib", "accelerator_memory_mib", "cpu_threads")
MODEL_FORMS = ("small", "big")
REASONING_MODES = ("light", "normal", "deep")
PRIORITIES = ("background", "standard", "interactive")
OUTCOMES = ("approve", "defer", "deny")
AUTHORITY_SCOPE = "SYNTHETIC_RESOURCE_FIT_ONLY"
MAX_MEASUREMENT = 2**63 - 1


class ResourcePolicyRefusal(ValueError):
    """Stable, non-sensitive validation failure; no original input echoed."""


def _text(value: object, label: str) -> str:
    if type(value) is not str or not 1 <= len(value.strip()) <= 256:
        raise ResourcePolicyRefusal("INVALID_" + label)
    return value.strip()


def _enum(value: object, label: str, choices: tuple[str, ...]) -> str:
    normalized = _text(value, label).lower()
    if normalized not in choices:
        raise ResourcePolicyRefusal("INVALID_" + label)
    return normalized


def _reasons(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or len(value) > 32:
        raise ResourcePolicyRefusal("INVALID_REASONS")
    return tuple(_text(v, "REASON") for v in value)


def _quantity(value: object, label: str) -> int | None:
    # Unknown is None, not 0; booleans are not measurements.
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= MAX_MEASUREMENT:
        raise ResourcePolicyRefusal("INVALID_" + label)
    return value


def _schema(value: object) -> None:
    if type(value) is not int or value != SCHEMA_VERSION:
        raise ResourcePolicyRefusal("INVALID_SCHEMA_VERSION")


@dataclass(frozen=True, slots=True)
class ResourceRequest:
    """One frozen semantic intent, not a runtime or signed consent claim."""

    task_id: str
    execution_context_id: str
    model_form: str
    reasoning_mode: str
    priority: str
    source: str
    reasons: tuple[str, ...] = ()
    may_defer: bool = True
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        for label in ("task_id", "execution_context_id", "source"):
            object.__setattr__(self, label, _text(getattr(self, label), label.upper()))
        object.__setattr__(
            self, "model_form", _enum(self.model_form, "MODEL_FORM", MODEL_FORMS)
        )
        # Historical Forest aliases: Quick -> Light, Standard -> Normal.
        raw_reasoning = _text(self.reasoning_mode, "REASONING_MODE").lower()
        raw_reasoning = {"quick": "light", "standard": "normal"}.get(
            raw_reasoning, raw_reasoning
        )
        object.__setattr__(
            self, "reasoning_mode",
            _enum(raw_reasoning, "REASONING_MODE", REASONING_MODES),
        )
        object.__setattr__(
            self, "priority", _enum(self.priority, "PRIORITY", PRIORITIES)
        )
        object.__setattr__(self, "reasons", _reasons(self.reasons))
        if type(self.may_defer) is not bool:
            raise ResourcePolicyRefusal("INVALID_MAY_DEFER")


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    """Minimum modeled resources for *this exact ResourceRequest*.

    None is unknown requirement. Zero means no additional resources
    of that kind are required beyond the existing baseline.
    """
    request: ResourceRequest
    source: str
    memory_mib: int | None = None
    accelerator_memory_mib: int | None = None
    cpu_threads: int | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        if type(self.request) is not ResourceRequest:
            raise ResourcePolicyRefusal("INVALID_REQUEST_BINDING")
        object.__setattr__(self, "source", _text(self.source, "SOURCE"))
        for label in DIMENSIONS:
            object.__setattr__(
                self, label, _quantity(getattr(self, label), label.upper())
            )


@dataclass(frozen=True, slots=True)
class ResourceBudget:
    """Explicit ceilings. None means *no ceiling set*, NOT known free capacity."""
    source: str
    memory_mib: int | None = None
    accelerator_memory_mib: int | None = None
    cpu_threads: int | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        object.__setattr__(self, "source", _text(self.source, "SOURCE"))
        for label in DIMENSIONS:
            object.__setattr__(
                self, label, _quantity(getattr(self, label), label.upper())
            )


@dataclass(frozen=True, slots=True)
class ResourceAvailability:
    """Observed available quantity; None unknown, zero measured empty."""
    source: str
    memory_mib: int | None = None
    accelerator_memory_mib: int | None = None
    cpu_threads: int | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        object.__setattr__(self, "source", _text(self.source, "SOURCE"))
        for label in DIMENSIONS:
            object.__setattr__(
                self, label, _quantity(getattr(self, label), label.upper())
            )


@dataclass(frozen=True, slots=True)
class GovernorDecision:
    """Resource-fit evaluation only, never runtime admission or consent."""
    request: ResourceRequest
    outcome: str
    source: str
    reasons: tuple[str, ...]
    schema_version: int = SCHEMA_VERSION
    authority_scope: str = field(default=AUTHORITY_SCOPE, init=False)
    production_authority: bool = field(default=False, init=False)
    permission_granted: bool = field(default=False, init=False)
    safe_to_start_inference: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        _schema(self.schema_version)
        if type(self.request) is not ResourceRequest:
            raise ResourcePolicyRefusal("INVALID_REQUEST_BINDING")
        object.__setattr__(
            self, "outcome", _enum(self.outcome, "OUTCOME", OUTCOMES)
        )
        object.__setattr__(self, "source", _text(self.source, "SOURCE"))
        object.__setattr__(self, "reasons", _reasons(self.reasons))


def evaluate_resource_request(
    request: ResourceRequest,
    requirement: ResourceRequirement,
    budget: ResourceBudget,
    availability: ResourceAvailability,
    *,
    source: str = "forest-synthetic-resource-governor-p1",
) -> GovernorDecision:
    """Pure historical policy-order adaptation for one exact request.

    1. Known requirement over explicit budget -> deny.
    2. Unknown requirement -> defer if allowed, else deny.
    3. Unknown/insufficient availability -> defer if allowed, else deny.
    4. Otherwise -> approve RESOURCE FIT ONLY.

    No automatic fallback, model choice, memory probing, process control,
    permission, C5 settlement, retries, changes to any runtime or filesystem.
    """
    if (type(request) is not ResourceRequest
            or type(requirement) is not ResourceRequirement
            or type(budget) is not ResourceBudget
            or type(availability) is not ResourceAvailability):
        raise ResourcePolicyRefusal("INVALID_GOVERNOR_ARGUMENTS")
    if requirement.request is not request:
        raise ResourcePolicyRefusal("REQUIREMENT_REQUEST_MISMATCH")
    source = _text(source, "SOURCE")

    def result(outcome: str, reasons: list[str]) -> GovernorDecision:
        return GovernorDecision(
            request=request, outcome=outcome, source=source,
            reasons=tuple(reasons),
        )

    violations: list[str] = []
    for label in DIMENSIONS:
        required = getattr(requirement, label)
        ceiling = getattr(budget, label)
        if required is not None and ceiling is not None and required > ceiling:
            violations.append(label + " requirement exceeds explicit budget")
    if violations:
        return result("deny", violations)

    unknown_requirements = [
        label for label in DIMENSIONS if getattr(requirement, label) is None
    ]
    if unknown_requirements:
        return result(
            "defer" if request.may_defer else "deny",
            ["Unknown requirement: " + ", ".join(unknown_requirements)],
        )

    unknown_availability: list[str] = []
    insufficient_availability: list[str] = []
    for label in DIMENSIONS:
        required = getattr(requirement, label)
        available = getattr(availability, label)
        if required == 0:
            continue
        if available is None:
            unknown_availability.append(label)
        elif available < required:
            insufficient_availability.append(label)

    if unknown_availability or insufficient_availability:
        reasons = []
        if unknown_availability:
            reasons.append("Unknown availability: " + ", ".join(
                unknown_availability
            ))
        if insufficient_availability:
            reasons.append("Insufficient availability: " + ", ".join(
                insufficient_availability
            ))
        return result("defer" if request.may_defer else "deny", reasons)
    return result("approve", ["Modeled resource requirement fits current inputs"])
