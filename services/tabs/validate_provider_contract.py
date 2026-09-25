#!/usr/bin/env python3
"""Static contract guard for Team 5's standalone tab/surface provider.

Run from the repository root:
    python3 services/tabs/validate_provider_contract.py

This does not replace runtime discovery testing. It prevents obvious ownership
regressions while Team 5 remains on the parallel floor.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / "services" / "tabs" / "TabSurfaceProvider.qml"

text = PROVIDER.read_text(encoding="utf-8")
errors: list[str] = []

required_functions = {
    "appTabBridgeScript",
    "appTabScanScript",
    "appTabActivateScript",
    "tabLifecycleScript",
    "refresh",
    "warmRefresh",
    "activate",
    "activateControl",
    "hasNativeLifecycleControl",
    "providerRecordKey",
    "identityEvidence",
    "normalizedProcessPids",
    "tabObservationSignature",
    "setLifecycleFrozen",
}

required_properties = {
    "active",
    "tabs",
    "controls",
    "loading",
    "errorText",
    "diagnostics",
    "bridgeReady",
    "bridgeError",
    "lifecycleFrozenKeys",
    "lifecycleError",
}

# These names indicate that the provider has started reaching back into host
# presentation/navigation or into another team's physiology.
forbidden_tokens = {
    "appControlWindow": "AppControl host coupling",
    "menuOpen": "host menu lifetime",
    "selectedModeIndex": "host mode/navigation state",
    "windowListMode": "WINDOWS/TABS selector state",
    "searchInput": "host search presentation",
    "selectedResult": "host result selection",
    "favoriteStore": "Team 2 Favorites ownership",
    "DesktopEntries": "Team 7/8 desktop identity/catalog ownership",
    "scheduleTabAudioProbe": "Team 6 audio coupling",
    "tabAudio": "Team 6 audio ownership",
    "appAudio": "Team 6 audio ownership",
    "windowAudio": "Team 6 audio ownership",
    "selectedResourceScope": "Team 1 resource-control coupling",
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

# Preserve current provider-native record namespaces. These are temporary
# provider identities/evidence, not canonical application identity.
for prefix in ("libatspi:", "atspi-cache:", "devtools:", "kitty:"):
    if prefix not in text:
        errors.append(f"missing provider record namespace: {prefix}")

# Team 5 may discover/process PID hints, but must not own stream mutation or
# Linux process/resource mutation.
for mutation_token in (
    "pactl",
    "wpctl",
    "kill -",
    "/usr/bin/kill",
    "systemctl",
    "ProcessLimits",
):
    if mutation_token in text:
        errors.append(f"foreign mutation mechanism present: {mutation_token}")

# The provider boundary is consumer-controlled through one neutral activity
# input rather than AppControl-specific mode knowledge.
for evidence_field in (
    "busName",
    "objectPath",
    "processPids",
    "debugPort",
    "targetId",
    "kittyAddress",
    "kittyTabId",
):
    if evidence_field not in text:
        errors.append(
            f"missing Team 7 requested provider evidence field: {evidence_field}"
        )

signature_start = text.find("function tabObservationSignature")
signature_end = text.find("function tabRowsSignature", signature_start)
signature_text = (
    text[signature_start:signature_end]
    if signature_start >= 0 and signature_end > signature_start
    else ""
)

for evidence_field in (
    "processPids",
    "busName",
    "objectPath",
    "debugPort",
    "targetId",
    "kittyAddress",
    "kittyTabId",
    "appName",
    "windowName",
):
    if evidence_field not in signature_text:
        errors.append(
            f"stable snapshot signature ignores evidence field: {evidence_field}"
        )

if "running: tabSurfaceProvider.active" not in text:
    errors.append("persistent discovery bridge is not governed by neutral active input")

if errors:
    print("TEAM 5 TAB PROVIDER CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("TEAM 5 TAB PROVIDER CONTRACT: PASS")
print(" provider:", PROVIDER.relative_to(ROOT))
print(" functions:", len(functions))
print(" properties:", len(properties))
print(" provider namespaces: LIBATSPI / AT-SPI-CACHE / DEVTOOLS / KITTY")
print(" foreign ownership references: none")
