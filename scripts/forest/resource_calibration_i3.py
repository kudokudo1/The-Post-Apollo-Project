"""I3 workload-specific calibration reference; synthetic only.

Observed peaks are not guaranteed maxima or minimum requirements.
No probes, timers, provider requests, hardware allocation or live authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from model_binding_i2 import BindingResult, ModelBinding, preserve_binding, BindingRefusal

_MAX = 2**63 - 1
_MIB = 1024 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)


class CalibrationRefusal(ValueError):
    """Fixed refusal code."""


def _id(value):
    if type(value) is not str or not _ID.fullmatch(value):
        raise CalibrationRefusal("INVALID_IDENTIFIER")


def _digest(value):
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise CalibrationRefusal("INVALID_DIGEST")


def _quantity(value, maximum=_MAX, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise CalibrationRefusal("INVALID_QUANTITY")


def _optional_quantity(value, maximum=_MAX):
    if value is not None:
        _quantity(value, maximum)


def _choice(value, choices):
    if type(value) is not str or value not in choices:
        raise CalibrationRefusal("INVALID_CHOICE")


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """Portable experimental identity, not an attestation.

    Exact model/runtime/config plus machine, boot, hardware/driver and
    measurement boundary references. One accelerator at most. Cold and warm
    profiles are distinct; warm baseline identity must include resident/cache
    state. No cross-profile interpolation or automatic reuse.
    """
    binding: ModelBinding
    machine_id: str
    boot_id: str
    hardware_digest: str
    measurement_scope_id: str
    accelerator_id: str | None
    workload_digest: str
    baseline_state_digest: str
    reasoning_mode: str
    residency: str
    prompt_tokens: int
    cpu_thread_limit: int

    def __post_init__(self):
        if type(self.binding) is not ModelBinding:
            raise CalibrationRefusal("INVALID_MODEL_BINDING")
        for v in (self.machine_id, self.boot_id, self.measurement_scope_id):
            _id(v)
        for v in (self.hardware_digest, self.workload_digest, self.baseline_state_digest):
            _digest(v)
        if self.accelerator_id is not None:
            _id(self.accelerator_id)
        _choice(self.reasoning_mode, ("light", "normal", "deep"))
        _choice(self.residency, ("cold", "warm"))
        _quantity(self.prompt_tokens, self.binding.context_tokens, 1)
        if self.prompt_tokens + self.binding.output_tokens > self.binding.context_tokens:
            raise CalibrationRefusal("TOKEN_BUDGET_EXCEEDS_CONTEXT")
        _quantity(self.cpu_thread_limit, 65536, 1)


@dataclass(frozen=True, slots=True)
class MemoryObservation:
    """Same measurement domain and units for baseline and observed peak.

    Missing observations remain None. A peak below baseline is inconsistent
    because the observation window must include the initial baseline.
    """
    baseline_bytes: int | None
    peak_bytes: int | None

    def __post_init__(self):
        _optional_quantity(self.baseline_bytes)
        _optional_quantity(self.peak_bytes)
        if (self.baseline_bytes is not None and self.peak_bytes is not None
                and self.peak_bytes < self.baseline_bytes):
            raise CalibrationRefusal("PEAK_BELOW_BASELINE")

    @property
    def incremental_bytes(self):
        if self.baseline_bytes is None or self.peak_bytes is None:
            return None
        return self.peak_bytes - self.baseline_bytes


@dataclass(frozen=True, slots=True)
class TrialReference:
    """Synthetic completed/incomplete trial metadata, no raw content.

    coverage_complete is a supplied fixture label, not proof of adequate
    sampling, exclusivity, currentness or authentic hardware counters.
    """
    profile: CalibrationProfile
    trial_id: str
    producer_id: str
    outcome: str
    coverage_complete: bool
    host: MemoryObservation
    accelerator: MemoryObservation | None
    load_ns: int | None
    first_content_ns: int | None
    completion_ns: int | None
    generated_tokens: int | None

    def __post_init__(self):
        if type(self.profile) is not CalibrationProfile:
            raise CalibrationRefusal("INVALID_PROFILE")
        _id(self.trial_id)
        _id(self.producer_id)
        _choice(self.outcome, ("complete", "incomplete", "refused"))
        if type(self.coverage_complete) is not bool:
            raise CalibrationRefusal("INVALID_COVERAGE")
        if type(self.host) is not MemoryObservation:
            raise CalibrationRefusal("INVALID_HOST_OBSERVATION")
        if self.accelerator is not None and type(self.accelerator) is not MemoryObservation:
            raise CalibrationRefusal("INVALID_ACCELERATOR_OBSERVATION")
        if self.profile.accelerator_id is None and self.accelerator is not None:
            raise CalibrationRefusal("UNBOUND_ACCELERATOR_OBSERVATION")
        for v in (self.load_ns, self.first_content_ns, self.completion_ns):
            _optional_quantity(v)
        _optional_quantity(self.generated_tokens, self.profile.binding.output_tokens)
        if self.completion_ns is not None:
            if any(v is not None and v > self.completion_ns
                   for v in (self.load_ns, self.first_content_ns)):
                raise CalibrationRefusal("INVALID_TIMING_ORDER")
        if self.outcome != "complete" and self.completion_ns is not None:
            raise CalibrationRefusal("INCOMPLETE_TERMINAL_TIME")


@dataclass(frozen=True, slots=True)
class CalibrationSummary:
    profile: CalibrationProfile
    trials: tuple[TrialReference, ...]
    host_peak_bytes: int | None
    host_incremental_bytes: int | None
    accelerator_peak_bytes: int | None
    accelerator_incremental_bytes: int | None
    reason: str

    @property
    def production_authority(self):
        return False

    @property
    def requirements_established(self):
        return False

    @property
    def resource_reserved(self):
        return False


def summarize(profile, trials):
    """Summarize exact-profile observed maxima, never mix profiles.

    Refuse duplicate IDs; incomplete coverage/outcomes invalidate the
    campaign summary instead of dropping failed trials. Unknown observations
    propagate per dimension rather than becoming zero or a partial maximum.
    """
    if type(profile) is not CalibrationProfile:
        raise CalibrationRefusal("INVALID_PROFILE")
    if (type(trials) is not tuple or not 1 <= len(trials) <= 4
            or any(type(t) is not TrialReference for t in trials)):
        raise CalibrationRefusal("INVALID_TRIALS")
    if profile.residency == "cold" and len(trials) != 1:
        raise CalibrationRefusal("COLD_TRIAL_COUNT")
    if profile.residency == "warm" and len(trials) > 3:
        raise CalibrationRefusal("WARM_TRIAL_COUNT")
    if len({t.trial_id for t in trials}) != len(trials):
        raise CalibrationRefusal("DUPLICATE_TRIAL")
    if any(t.profile != profile for t in trials):
        raise CalibrationRefusal("PROFILE_MISMATCH")
    if any(t.outcome != "complete" or not t.coverage_complete for t in trials):
        return CalibrationSummary(profile, trials, None, None, None, None,
                                  "INCOMPLETE_CAMPAIGN")

    def maximum(values):
        return None if any(v is None for v in values) else max(values)

    host_peak = maximum(tuple(t.host.peak_bytes for t in trials))
    host_incremental = maximum(tuple(t.host.incremental_bytes for t in trials))
    # No accelerator target is NOT evidence of zero GPU demand.
    accelerator_peak = maximum(tuple(t.accelerator.peak_bytes if t.accelerator
                                     is not None else None for t in trials))
    accelerator_incremental = maximum(tuple(t.accelerator.incremental_bytes if
                                            t.accelerator is not None else None
                                            for t in trials))
    return CalibrationSummary(profile, trials, host_peak, host_incremental,
                              accelerator_peak, accelerator_incremental,
                              "OBSERVED_REFERENCE_ONLY")


def match_turn(binding_result, profile):
    """Verify exact I2 reference match, not real installed identity."""
    if type(binding_result) is not BindingResult or type(profile) is not CalibrationProfile:
        raise CalibrationRefusal("INVALID_BINDING_REFERENCE")
    try:
        preserve_binding(binding_result, binding_result.recommendation,
                         binding_result.registry, required_features=binding_result.required_features,
                         evidence=binding_result.evidence)
    except BindingRefusal:
        raise CalibrationRefusal("INVALID_BINDING_REFERENCE") from None
    if binding_result.binding is None:
        return False
    return (binding_result.binding == profile.binding
            and binding_result.recommendation.original.reasoning.mode == profile.reasoning_mode)


def public_summary(summary):
    """Bounded diagnostics, no machine, model, workload or producer IDs."""
    if type(summary) is not CalibrationSummary or summary != summarize(summary.profile, summary.trials):
        raise CalibrationRefusal("INVALID_SUMMARY")
    def mib(value):
        return None if value is None else (value + _MIB - 1) // _MIB
    return {
        "schema": "post-apollo.forest.calibration-reference.i3",
        "status": "UNKNOWN_HOLD",
        "reason": summary.reason,
        "residency": summary.profile.residency,
        "trialCount": len(summary.trials),
        "hostObservedPeakMiB": mib(summary.host_peak_bytes),
        "hostObservedIncrementalMiB": mib(summary.host_incremental_bytes),
        "acceleratorObservedPeakMiB": mib(summary.accelerator_peak_bytes),
        "acceleratorObservedIncrementalMiB": mib(summary.accelerator_incremental_bytes),
        "configuredCpuThreadLimit": summary.profile.cpu_thread_limit,
        "cpuRequirementThreads": None,
        "hostRequirementMiB": None,
        "acceleratorRequirementMiB": None,
        "availabilityEstablished": False,
        "requirementsEstablished": False,
        "resourceReserved": False,
        "sourceAuthenticated": False,
        "permissionGranted": False,
        "productionAuthority": False,
        "modelExecutionPermitted": False,
        "safeActions": [],
    }
