#!/usr/bin/env python3
"""Static ownership guard for the shared SurfaceLaunch contract."""

from pathlib import Path
import ast
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "services" / "surface" / "SurfaceLaunchRequirements.qml"
COORD = ROOT / "services" / "surface" / "SurfaceLaunchCoordinator.qml"
RECOVERY = ROOT / "services" / "surface" / "SurfaceInstrumentationRecovery.qml"
QMLDIR = ROOT / "services" / "surface" / "qmldir"

requirements = REQ.read_text(encoding="utf-8")
coordinator = COORD.read_text(encoding="utf-8")
recovery = RECOVERY.read_text(encoding="utf-8")
qmldir = QMLDIR.read_text(encoding="utf-8")
authority_combined = requirements + "\n" + coordinator
combined = authority_combined + "\n" + recovery

# Comments may name forbidden couplings in order to document their absence.
# Ownership checks apply to executable QML, not comments.
authority_executable = re.sub(
    r"/\*.*?\*/", "", authority_combined, flags=re.S
)
authority_executable = re.sub(
    r"//.*?$", "", authority_executable, flags=re.M
)
recovery_executable = re.sub(
    r"/\*.*?\*/", "", recovery, flags=re.S
)
recovery_executable = re.sub(
    r"//.*?$", "", recovery_executable, flags=re.M
)

errors: list[str] = []

if not requirements.lstrip().startswith("pragma Singleton"):
    errors.append("SurfaceLaunchRequirements is not a singleton")

if not coordinator.lstrip().startswith("pragma Singleton"):
    errors.append("SurfaceLaunchCoordinator is not the shared singleton authority")

if not recovery.lstrip().startswith("pragma Singleton"):
    errors.append("SurfaceInstrumentationRecovery is not a shared singleton")

for declaration in (
    "module qs.services.surface",
    "singleton SurfaceLaunchRequirements 1.0 SurfaceLaunchRequirements.qml",
    "singleton SurfaceLaunchCoordinator 1.0 SurfaceLaunchCoordinator.qml",
    "singleton SurfaceInstrumentationRecovery 1.0 SurfaceInstrumentationRecovery.qml",
):
    if declaration not in qmldir:
        errors.append(f"missing qmldir singleton declaration: {declaration}")

if re.search(r"\brequired\s+property\s+var\s+requirements\b", coordinator):
    errors.append("coordinator still permits per-instance requirements injection")

for declaration in (
    "property var _leaseState:",
    "property var _correlationState:",
    "property int _correlationSerial:",
    "property string _sessionNonce:",
    "readonly property var leases: copyMap(_leaseState)",
    "readonly property var correlationState: copyMap(_correlationState)",
):
    if declaration not in coordinator:
        errors.append(
            f"missing protected authority state declaration: {declaration}"
        )

for public_name in (
    "leases",
    "correlationState",
    "correlationSerial",
):
    pattern = re.compile(
        rf"(?<!_)\b{re.escape(public_name)}\s*(?:=|\+=)"
    )
    if pattern.search(coordinator):
        errors.append(
            "public SurfaceLaunch authority state remains writable internally: "
            + public_name
        )

if "SurfaceBackend.SurfaceLaunchRequirements." not in coordinator:
    errors.append("coordinator is not bound to the shared requirements singleton")

required_capabilities = (
    "KITTY_REMOTE",
    "ACCESSIBILITY",
    "DEVTOOLS",
)

for capability in required_capabilities:
    if capability not in requirements:
        errors.append(f"missing capability: {capability}")

required_requirement_functions = (
    "primaryExecutableName",
    "suggestedCapabilities",
    "requirementFor",
    "describe",
    "preferredDebugPort",
)

for name in required_requirement_functions:
    if not re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", requirements):
        errors.append(f"missing requirements function: {name}")

required_recovery_functions = (
    "probeScript",
    "normalizedSnapshot",
    "applySnapshot",
    "reconcileSharedAuthority",
    "refresh",
)

for name in required_recovery_functions:
    if not re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", recovery):
        errors.append(f"missing recovery function: {name}")

probe_match = re.search(
    r'function\s+probeScript\s*\(\s*\)\s*\{\s*'
    r'return\s+("(?:\\.|[^"\\])*");\s*\}',
    recovery,
    re.S,
)

if not probe_match:
    errors.append("unable to extract recovery probe Python")
else:
    try:
        probe_python = json.loads(probe_match.group(1))
        ast.parse(probe_python)
    except Exception as exc:
        errors.append(f"recovery probe Python syntax invalid: {exc}")

for token in (
    "SURFACE RECOVERY SNAPSHOT UNUSABLE",
    "if (snapshot.ok)",
    "if (!snapshot.ok)",
    "ok: payload.ok !== false",
    "DEVTOOLS SOCKET",
    "namespace_has_tcp_listener(pid, port)",
    "state == '0A'",
    "('tcp', 'tcp6')",
    "def namespace_has_tcp_listener(pid, port)",
    "if owned is None:",
    "return (None, exc)",
    "socket_key in kitty_sockets",
    "def kitty_socket_key(address)",
    "def unix_socket_addresses()",
    "/proc/net/unix",
    "'partial': bool(errors)",
    "os.getuid()",
    "os.stat('/proc/%s' % pid).st_uid == uid",
    "KITTY_LISTEN_ON=",
    "--remote-debugging-port=",
    "completeKinds",
    "reconcileObservedInstrumentation",
):
    if token not in recovery:
        errors.append(f"missing recovery contract token: {token}")

required_coordinator_functions = (
    "copyValue",
    "copyMap",
    "correlationIdFor",
    "kittyListenAddress",
    "normalizedObservedLease",
    "reconcileObservedInstrumentation",
    "buildAugmentation",
    "releaseCorrelation",
    "markLaunchSucceeded",
    "markLaunchFailed",
    "existingDebugPort",
    "existingDebugAddress",
    "debugAddressIsLoopback",
    "existingKittyListenOn",
    "kittyRemoteControlMode",
    "kittyRemoteControlEnabled",
)

for name in required_coordinator_functions:
    if not re.search(rf"\bfunction\s+{re.escape(name)}\s*\(", coordinator):
        errors.append(f"missing coordinator function: {name}")

# SurfaceLaunch is shared domain logic, not an executor or host integration.
for token, reason in {
    "appControlWindow": "AppControl host coupling",
    "DesktopEntries": "DesktopEntry catalog ownership",
    "TabSurfaceProvider": "provider lifetime coupling",
    ".active": "provider activity/lifetime coupling",
    "Quickshell.execDetached": "process execution",
    "Process {": "process execution",
    "ShellCommand": "process execution",
    "pactl": "audio ownership",
    "wpctl": "audio ownership",
    "ProcessControl": "process/resource ownership",
    "ProcessLimits": "process/resource ownership",
    "canonicalId": "semantic identity ownership",
    "semanticKey": "semantic identity ownership",
    "augmentEverything": "forbidden global interception",
    "SurfaceLaunchCoordinator {": "competing coordinator instance",
    "AppControlW": "AppControl host coupling",
}.items():
    if token in authority_executable:
        errors.append(f"forbidden token {token!r}: {reason}")

# Recovery may execute its diagnostic probe, but it remains outside host,
# launcher, semantic-identity, audio, and process-control ownership.
for token, reason in {
    "appControlWindow": "AppControl host coupling",
    "AppControlW": "AppControl host coupling",
    "DesktopEntries": "DesktopEntry catalog ownership",
    "TabSurfaceProvider.active": "provider activity/lifetime coupling",
    "Quickshell.execDetached": "application/process launch ownership",
    "ShellCommand": "shell execution ownership",
    "pactl": "audio ownership",
    "wpctl": "audio ownership",
    "ProcessControl": "process/resource ownership",
    "ProcessLimits": "process/resource ownership",
    "canonicalId": "semantic identity ownership",
    "semanticKey": "semantic identity ownership",
    "augmentEverything": "forbidden global interception",
}.items():
    if token in recovery_executable:
        errors.append(f"forbidden recovery token {token!r}: {reason}")

# Explicit opt-in: requested capabilities must be an input to augmentation.
if not re.search(
    r"function\s+buildAugmentation\s*\(\s*evidence\s*,\s*requestedCapabilities\s*\)",
    coordinator,
):
    errors.append("buildAugmentation is not explicitly capability-driven")

if (
    "SurfaceBackend.SurfaceLaunchRequirements.describe("
    "evidence, requestedCapabilities)"
    not in coordinator
):
    errors.append(
        "coordinator does not route explicit requests through shared requirements"
    )

if 'normalizedCommandTokens(evidence).join(" ")' in requirements:
    errors.append(
        "surface family recognition still depends on arbitrary trailing argv text"
    )

if "knownCapabilities.indexOf(value) === -1" in requirements:
    errors.append(
        "unknown capability requests are silently discarded before validation"
    )

for token in (
    "kittyListenAddress(correlationId)",
    "existingDebugPort",
    "existingDebugAddress",
    "existingKittyListenOn",
    "existingKittyRemoteControlMode",
    "ready: ready",
    "conflicts: conflictRows.slice()",
    "appliedCapabilities: ready ? applied.slice() : []",
    '"caller-supplied"',
    '"generated"',
    '"observed"',
    "options.complete === true",
    "options.completeKinds",
    "completeKinds.indexOf(lease.kind)",
    "description.requestedCapabilities.length === 0",
    "description.unsupportedCapabilities.length > 0",
    "releaseCorrelation(correlationId)",
    "ready ? env : {}",
    "ready ? argvAfterExecutable : []",
    "ready ? argvAppend : []",
    "removedLease || hadState",
    'lease.source === "observed"',
    "!_correlationState[id]",
    '"requires-socket-only"',
    '"requires-loopback"',
    "slice(0, 60)",
    "Math.random() * 0x100000000",
):
    if token not in coordinator:
        errors.append(f"missing augmentation readiness/lease contract token: {token}")

# Three-clock invariant: provider activity must not release coordinator leases.
if "releaseCorrelation" not in coordinator:
    errors.append("missing explicit instrumentation release hook")

if "markLaunchSucceeded" not in coordinator or "markLaunchFailed" not in coordinator:
    errors.append("missing launch transaction bookkeeping hooks")

# Donor-preservation checks.
for token in (
    "allow_remote_control=socket-only",
    "--force-renderer-accessibility=complete",
    "NO_AT_BRIDGE",
    "ACCESSIBILITY_ENABLED",
    "QT_ACCESSIBILITY",
    "QT_LINUX_ACCESSIBILITY_ALWAYS_ON",
    "--remote-debugging-address=",
    "127.0.0.1",
    "--remote-debugging-port=",
):
    if token not in combined:
        errors.append(f"missing donor instrumentation token: {token}")

for port in ("9222", "9223", "9224", "9225", "9226", "9300", "9499"):
    if port not in combined:
        errors.append(f"missing donor/fallback port policy token: {port}")

if errors:
    print("TEAM 5 SURFACE LAUNCH CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("TEAM 5 SURFACE LAUNCH CONTRACT: PASS")
print(" capabilities: KITTY_REMOTE / ACCESSIBILITY / DEVTOOLS")
print(" lease authority: one shared SurfaceLaunchCoordinator singleton")
print(" recovery probe: shared SurfaceInstrumentationRecovery singleton")
print(" execution ownership: external launcher")
print(" provider lifetime coupling: none")
print(" semantic identity ownership: none")
