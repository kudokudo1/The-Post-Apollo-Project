#!/usr/bin/env python3
"""Static contract guard for Team 6's standalone application-audio service.

Run from the repository root:
    python3 services/audio/validate_audio_contract.py

This does not replace live PipeWire testing. It guards ownership, public service
shape, and the donor invariants Team 6 is expected to preserve while host wiring
remains serialized.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
SERVICE = ROOT / "services" / "audio" / "ApplicationAudioService.qml"
TEST_SUITE = ROOT / "tests" / "audio" / "tst_ApplicationAudioContracts.qml"

text = SERVICE.read_text(encoding="utf-8")
test_text = TEST_SUITE.read_text(encoding="utf-8")
errors: list[str] = []

required_functions = {
    "normalizeToken",
    "tokensMatch",
    "streamPropertyTokens",
    "copyDescriptor",
    "policyStorageKey",
    "descriptorMatchEvidence",
    "matchesDescriptor",
    "sinkInputVolumePercent",
    "averagedSinkVolume",
    "resolve",
    "streamEvidence",
    "evidenceSnapshot",
    "streamObservation",
    "observationSnapshot",
    "parseSinkInputs",
    "refresh",
    "requestPolicyRefresh",
    "setSinkInputMute",
    "setSinkInputVolumes",
    "setMutePolicy",
    "mutePolicyActive",
    "queueMuteState",
    "mutePolicyKeysWithPid",
    "policyKeysOutsideLiveSet",
    "clearMutePoliciesWithPid",
    "retainPolicyKeys",
    "volumePolicyKey",
    "setVolumePolicy",
    "clearVolumePolicy",
    "volumePolicyPercentFor",
    "mutePolicyTargets",
    "pendingMuteTargets",
    "volumePolicyTargets",
    "applyMutePolicies",
    "applyPendingMuteStates",
    "applyVolumePolicies",
    "applyPolicies",
}

required_properties = {
    "volumeMaxPercent",
    "sinkInputs",
    "observationGeneration",
    "loading",
    "errorText",
    "mutePolicies",
    "pendingMuteStates",
    "volumePolicies",
    "volumePolicySerial",
}

forbidden_tokens = {
    "appControlWindow": "AppControl host coupling",
    "AppControlW": "AppControl host coupling",
    "menuOpen": "host menu lifetime",
    "selectedModeIndex": "host mode/navigation state",
    "selectedResult": "host result selection",
    "favoriteStore": "Team 2 Favorites ownership",
    "favoriteSourceItem": "Team 2/host reconstruction coupling",
    "DesktopEntries": "Team 7/8 desktop identity/catalog ownership",
    "appEntryKey": "host/APPS identity authority",
    "windowKey": "host/WINDOW identity authority",
    "windowsForApp": "host cross-provider identity join",
    "TabSurfaceProvider": "Team 5 provider ownership",
    "ProcessControl": "Team 1 process-control ownership",
    "ProcessLimits": "Team 1 resource-limit ownership",
}

functions = set(
    re.findall(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", text, re.M)
)
properties = set(
    re.findall(
        r"^\s*(?:readonly\s+)?property\s+\S+\s+([A-Za-z_][A-Za-z0-9_]*)",
        text,
        re.M,
    )
)

missing_functions = sorted(required_functions - functions)
if missing_functions:
    errors.append("missing required functions: " + ", ".join(missing_functions))

missing_properties = sorted(required_properties - properties)
if missing_properties:
    errors.append("missing required properties: " + ", ".join(missing_properties))

for token, owner in forbidden_tokens.items():
    if token in text:
        errors.append(f"forbidden token {token!r}: {owner}")

for raw_property in (
    'application.process.id',
    'application.process.binary',
    'application.id',
    'application.name',
    'media.name',
):
    if raw_property not in text:
        errors.append(f"missing raw PipeWire evidence field: {raw_property}")

for mutation in (
    '"set-sink-input-mute"',
    '"set-sink-input-volume"',
):
    if mutation not in text:
        errors.append(f"missing owned audio mutation backend: {mutation}")

if 'readonly property real volumeMaxPercent: 100' not in text:
    errors.append("unity-gain 100% volume cap is not explicit")

if 'return policyStorageKey(scope, key);' not in text:
    errors.append("volume policy keys do not share normalized scoped storage")

for stream_fact in ("hasStreams", "streamsMuted", "observedVolumePercent"):
    if stream_fact not in text:
        errors.append(f"missing stream-physiology result field: {stream_fact}")

if re.search(r"\bavailable\s*:", text):
    errors.append("generic host-style availability leaked into service result")

for evidence_field in (
    "matched",
    "pidMatch",
    "processId",
    "streamIndex",
    "strictTokens",
    "tokenMatches",
):
    if evidence_field not in text:
        errors.append(f"missing separate match-evidence field: {evidence_field}")


for observation_token in (
    'provider: "PIPEWIRE"',
    '"sink-input:"',
    'lifetimeClass: "ephemeral"',
    "generation: observationGeneration",
    "aliases: aliases",
    "relationships: []",
):
    if observation_token not in text:
        errors.append(f"missing Team 7 observation adapter token: {observation_token}")

if "Math.floor(index) !== index" not in text:
    errors.append("sink-input mutation indexes are not constrained to integers")


required_test_cases = {
    "test_normalizeTokenPreservesDonorShape",
    "test_tokenMatchingRiskModes",
    "test_descriptorCopySanitizesEvidence",
    "test_exactPidEvidenceIsSeparateFromTokenEvidence",
    "test_strictAppMatchingRejectsSuffixOnlyAlias",
    "test_fuzzyWindowTabMatchingAllowsSuffixEvidence",
    "test_strictPropertyTokensBlockGenericAliases",
    "test_resolveReportsPhysiologyNotHostAvailability",
    "test_resolveNoStreamUsesUnknownObservedVolume",
    "test_volumeMathNeverAmplifiesAboveUnity",
    "test_rawEvidencePreservesPipeWireFields",
    "test_team7ObservationAdapterKeepsProvenance",
    "test_team7ObservationOmitsInvalidPidRelationship",
    "test_parseSinkInputsAcceptsPactlArray",
    "test_parseSinkInputsRejectsInvalidPayloads",
    "test_sinkInputVolumeSupportsRawPulseValue",
    "test_policyLifetimePlannerPrunesOnlyRequestedScope",
    "test_pidPolicyPlannerPreservesOtherScopes",
    "test_pidPolicyPlannerRejectsInvalidPid",
    "test_futureStreamMutePolicyPlanning",
    "test_pendingMutePlannerSupportsOneShotUnmute",
    "test_latestVolumePolicySerialWinsOverlap",
    "test_volumePolicyPlannerClampsTarget",
    "test_policyNamespacesNormalizeScopeOnly",
}

test_cases = set(
    re.findall(
        r"^\s*function\s+(test_[A-Za-z_][A-Za-z0-9_]*)\s*\(",
        test_text,
        re.M,
    )
)

missing_test_cases = sorted(required_test_cases - test_cases)
if missing_test_cases:
    errors.append(
        "missing isolated audio test cases: " + ", ".join(missing_test_cases)
    )

# The QtTest suite is intentionally physiology-only. It must never become a
# convenient way to mutate the operator's live PipeWire session.
for mutator in (
    "setSinkInputMute(",
    "setSinkInputVolumes(",
    "setMutePolicy(",
    "setVolumePolicy(",
):
    if mutator in test_text:
        errors.append(f"isolated test suite calls live mutator: {mutator}")

if errors:
    print("TEAM 6 APPLICATION AUDIO CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("TEAM 6 APPLICATION AUDIO CONTRACT: PASS")
print(" service:", SERVICE.relative_to(ROOT))
print(" functions:", len(functions))
print(" properties:", len(properties))
print(" isolated QtTest cases:", len(test_cases))
print(" raw PipeWire evidence: preserved")
print(" semantic identity authority: external / Team 7")
print(" foreign ownership references: none")
