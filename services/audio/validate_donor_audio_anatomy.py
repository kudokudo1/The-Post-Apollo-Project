#!/usr/bin/env python3
"""Pre-integration anatomy guard for Team 6's AppControl audio donor.

Run from the repository root:
    python3 services/audio/validate_donor_audio_anatomy.py

This is not a runtime test and it does not certify AppControl behavior. Its job is
narrow: while Team 6 remains on the parallel floor, record the donor anatomy the
shared audio service was extracted from. After Team 6 eventually re-anchors onto
an exact certified patient, rerun this guard before host wiring. A failure means
the donor changed and must be reread before transplantation.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT / "widgets" / "AppControlW.qml"

text = DONOR.read_text(encoding="utf-8")
errors: list[str] = []

required_properties = (
    "windowAudioSinkInputs",
    "windowAudioAvailable",
    "windowAudioMuted",
    "windowAudioVolumePercent",
    "windowAudioMutePolicies",
    "appAudioSinkInputs",
    "appAudioAvailable",
    "appAudioMuted",
    "appAudioVolumePercent",
    "appAudioMutePolicies",
    "appAudioPendingMuteStates",
    "tabAudioSinkInputs",
    "tabAudioAvailable",
    "tabAudioMuted",
    "tabAudioVolumePercent",
    "windowAudioVolumePolicies",
    "appAudioVolumePolicies",
    "tabAudioVolumePolicies",
    "audioVolumePolicySerial",
)

required_functions = (
    "windowAudioRawTokens",
    "windowAudioTokens",
    "audioPropertyTokens",
    "windowMatchesAudioSink",
    "windowMutePolicyKey",
    "windowMutePolicyActiveFor",
    "setWindowMutePolicy",
    "applyWindowMutePolicies",
    "appAudioIdentityTokens",
    "strictAudioPropertyTokens",
    "appIdentityMatchesAudioSink",
    "appMutePolicyKey",
    "appMutePolicyActiveFor",
    "setAppMutePolicy",
    "applyAppMutePolicies",
    "queueAppMuteState",
    "windowVolumePolicyPercentFor",
    "setWindowVolumePolicy",
    "appVolumePolicyPercentFor",
    "setAppVolumePolicy",
    "tabVolumePolicyKey",
    "tabVolumePolicyPercentFor",
    "setTabVolumePolicy",
    "applyAudioVolumePolicies",
    "setSinkInputVolumes",
    "setSelectedWindowVolume",
    "setSelectedApplicationVolume",
    "selectedTabAudioKey",
    "tabAudioTokens",
    "tabMatchesAudioSink",
    "setSelectedTabVolume",
    "toggleSelectedTabMute",
    "scheduleWindowAudioProbe",
    "toggleSelectedWindowMute",
    "selectedApplicationAudioKey",
    "appMatchesAudioSink",
    "scheduleAppAudioProbe",
    "toggleSelectedApplicationMute",
)

for name in required_properties:
    if not re.search(
        rf"\bproperty\s+\S+\s+{re.escape(name)}\b",
        text,
    ):
        errors.append(f"missing donor property: {name}")

for name in required_functions:
    if not re.search(
        rf"\bfunction\s+{re.escape(name)}\s*\(",
        text,
    ):
        errors.append(f"missing donor function: {name}")

# Donor volume policy is explicitly capped at unity. Team 6 must reread the
# donor if this changes rather than silently keeping an obsolete service rule.
if not re.search(
    r"\b(?:readonly\s+)?property\s+\S+\s+audioVolumeMaxPercent\s*:\s*100\b",
    text,
):
    errors.append("donor 100% audio volume cap changed or disappeared")

# These three host-facing availability flags have intentionally different
# semantics from shared stream physiology. Their continued presence matters
# until the serialized host adapter is actually designed.
for name in (
    "windowAudioAvailable",
    "appAudioAvailable",
    "tabAudioAvailable",
):
    if text.count(name) < 2:
        errors.append(
            f"donor host availability seam appears changed: {name}"
        )

# The extracted organ depends on three policy families remaining distinct.
for token in (
    "windowAudioMutePolicies",
    "appAudioMutePolicies",
    "windowAudioVolumePolicies",
    "appAudioVolumePolicies",
    "tabAudioVolumePolicies",
):
    if token not in text:
        errors.append(f"donor policy family missing: {token}")

if errors:
    print("TEAM 6 DONOR AUDIO ANATOMY: FAIL")
    for error in errors:
        print(" -", error)
    print("Reread the exact certified AppControl patient before any Team 6 host wiring.")
    sys.exit(1)

print("TEAM 6 DONOR AUDIO ANATOMY: PASS")
print(" donor:", DONOR.relative_to(ROOT))
print(" required properties:", len(required_properties))
print(" required functions:", len(required_functions))
print(" volume cap: 100%")
print(" host availability seams: WINDOW / APP / TAB present")
print(" NOTE: static anatomy pass only; not runtime certification")
