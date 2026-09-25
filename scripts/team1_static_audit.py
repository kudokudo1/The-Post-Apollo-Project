#!/usr/bin/env python3
"""
Static architecture audit for Team 1 Process/System prepared organs.

This script intentionally does not launch Quickshell or perform destructive
runtime actions. It catches contract drift before serialized host integration.

Usage:
    python3 scripts/team1_static_audit.py
    python3 scripts/team1_static_audit.py --base <sha>
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

CONTRACT_TEST = ROOT / "tests/system/tst_Team1ProcessSystemContracts.qml"

QML_FILES = {
    "process_identity": ROOT / "services/system/ProcessIdentity.qml",
    "process_scope": ROOT / "services/system/ProcessScope.qml",
    "process_safety": ROOT / "services/system/ProcessSafety.qml",
    "process_control": ROOT / "services/system/ProcessControl.qml",
    "process_limit_mutation": ROOT / "services/system/ProcessLimitMutation.qml",
    "process_limits": ROOT / "services/system/ProcessLimits.qml",
    "process_action": ROOT / "services/system/ProcessActionController.qml",
    "resource_scope": ROOT / "services/system/ProcessResourceScope.qml",
    "resource_state": ROOT / "services/system/ProcessResourceState.qml",
    "resource_controller": ROOT / "services/system/ProcessResourceController.qml",
    "process_presentation": ROOT / "widgets/system/ProcessPresentation.qml",
    "system_control": ROOT / "services/system/SystemControl.qml",
    "system_presentation": ROOT / "widgets/system/SystemPresentation.qml",
    "system_monitor_controller": ROOT / "widgets/system/SystemMonitorController.qml",
}

ALLOWED_TEAM1_DIFF_PREFIXES = (
    "services/system/",
    "widgets/system/",
    "docs/team1/",
    "tests/system/",
    "scripts/team1_static_audit.py",
)

failures: list[str] = []
passes: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def ok(message: str) -> None:
    passes.append(message)


def read(name: str) -> str:
    path = QML_FILES[name]
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        fail(f"{label}: missing {needle!r}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        fail(f"{label}: forbidden dependency {needle!r}")


def require_functions(text: str, names: tuple[str, ...], label: str) -> None:
    for name in names:
        require(text, f"function {name}(", label)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        fail(
            "git command failed: git "
            + " ".join(args)
            + "\n"
            + result.stderr.strip()
        )
        return ""
    return result.stdout


def audit_architecture() -> None:
    identity = read("process_identity")
    scope = read("process_scope")
    safety = read("process_safety")
    control = read("process_control")
    limit_mutation = read("process_limit_mutation")
    limits = read("process_limits")
    action = read("process_action")
    resource_scope = read("resource_scope")
    resource_state = read("resource_state")
    resource_controller = read("resource_controller")
    presentation = read("process_presentation")
    system_control = read("system_control")
    system_presentation = read("system_presentation")
    system_monitor = read("system_monitor_controller")

    if not CONTRACT_TEST.exists():
        fail(
            "missing Team 1 behavioral contract suite: "
            + str(CONTRACT_TEST.relative_to(ROOT))
        )
        contract_test = ""
    else:
        contract_test = CONTRACT_TEST.read_text(encoding="utf-8")

    require_functions(
        identity,
        (
            "sourceEntry",
            "persistentIdentity",
            "pidPolicyKey",
            "capturedIdentity",
            "matchesCaptured",
        ),
        "ProcessIdentity",
    )
    require_functions(
        scope,
        (
            "uniquePositivePids",
            "rowForPid",
            "treeRowsForRoots",
            "pidsForRoots",
        ),
        "ProcessScope",
    )
    require_functions(
        safety,
        (
            "protectedFromBulkTermination",
            "protectedFromKillAll",
            "dangerReason",
            "requiresDangerUnlock",
            "dangerActionUnlocked",
            "relockDangerAction",
        ),
        "ProcessSafety",
    )

    # ProcessControl is the signal/restart primitive. RLIMIT mutation must not
    # reappear here.
    require_functions(
        control,
        ("sendSignal", "sendSignalMany", "restart"),
        "ProcessControl",
    )
    forbid(control, "resource.prlimit", "ProcessControl")
    forbid(control, '"prlimit"', "ProcessControl")
    forbid(control, "setAddressSpaceLimitBytes", "ProcessControl")

    # There is one prepared shared verified RLIMIT_AS mutation authority.
    require_functions(
        limit_mutation,
        ("requestLimit", "requestLimitMany", "startNext", "finishActive"),
        "ProcessLimitMutation",
    )
    require(limit_mutation, "signal batchFinished", "ProcessLimitMutation")
    require(limit_mutation, "resource.prlimit", "ProcessLimitMutation")

    # Current single-process donor keeps its compatibility fallback until T3
    # wires shared lifetime.
    require(limits, "property var mutationService: null", "ProcessLimits")
    require(limits, "resource.prlimit", "ProcessLimits")
    require(limits, "consumer: \"process-limits\"", "ProcessLimits")

    # Shared destructive action policy must normalize favorite wrappers and
    # preserve execution + cancel semantics.
    require(action, "required property var processIdentity", "ProcessActionController")
    require(action, "sourceEntry(entry)", "ProcessActionController")
    require(action, "processIdentity.matchesCaptured", "ProcessActionController")
    require_functions(
        action,
        (
            "requestRestart",
            "requestTerminate",
            "requestToggleFreeze",
            "cancelConfirmed",
            "executeConfirmed",
        ),
        "ProcessActionController",
    )
    for kind in (
        "protected-restart",
        "task-restart",
        "protected-term",
        "task-term",
        "protected-freeze",
        "task-freeze",
    ):
        require(action, kind, "ProcessActionController")

    # Provider-neutral resource layer: callers supply semantic scope keys and
    # roots; Team 1 must not rediscover APP/WINDOW/TAB identity.
    require_functions(
        resource_scope,
        (
            "rows",
            "parentRows",
            "containsProtected",
            "limitAvailable",
            "limitMinimumMiB",
            "allFrozen",
            "processText",
        ),
        "ProcessResourceScope",
    )
    require_functions(
        resource_state,
        (
            "rootLimitState",
            "limitMiB",
            "rememberScopeLimit",
            "rememberLimit",
            "verifiedMiBFromResult",
            "noteMutationResults",
            "reconciliationTargetMiB",
            "isFrozen",
            "markFrozen",
        ),
        "ProcessResourceState",
    )
    require(
        resource_state,
        "property var frozenScopes: ({})",
        "ProcessResourceState",
    )
    require(
        resource_state,
        "!!frozenScopes[key]",
        "ProcessResourceState",
    )
    require(
        resource_controller,
        "required property var limitMutation",
        "ProcessResourceController",
    )
    require(
        resource_controller,
        "resourceState.noteMutationResults",
        "ProcessResourceController",
    )
    require(
        resource_controller,
        "resourceState.rememberScopeLimit",
        "ProcessResourceController",
    )
    if "resourceState.rememberLimit(" in resource_controller:
        fail(
            "ProcessResourceController: batch completion must not overwrite "
            "verified per-PID state with uniform requested policy"
        )
    require_functions(
        resource_controller,
        (
            "setMemoryLimitMiB",
            "setMemoryLimitPercent",
            "reconcileMemoryLimit",
            "freezeAvailable",
            "toggleFreeze",
        ),
        "ProcessResourceController",
    )

    provider_forbidden = (
        "appControlWindow",
        "selectedResult",
        "selectedModeIndex",
        "appEntryKey",
        "windowKey(",
        "swayWindows",
        "debugPort",
        "tabLifecycle",
        "DesktopEntry",
    )
    for label, text in (
        ("ProcessResourceScope", resource_scope),
        ("ProcessResourceState", resource_state),
        ("ProcessResourceController", resource_controller),
    ):
        for needle in provider_forbidden:
            forbid(text, needle, label)

    require_functions(
        presentation,
        ("formatMemory", "metricIsCritical", "scopeProcessText"),
        "ProcessPresentation",
    )

    require(system_control, "required property var processControl", "SystemControl")
    require(system_control, "signal rebootRequested", "SystemControl")
    require_functions(
        system_control,
        ("runComponentAction", "executeReboot", "terminateContributor"),
        "SystemControl",
    )

    require_functions(
        system_presentation,
        (
            "systemAccent",
            "systemIconAccent",
            "systemRateMetricParts",
            "systemIconFor",
            "systemComponentWarning",
            "contributorRows",
        ),
        "SystemPresentation",
    )

    require(system_monitor, "required property var selectionAdapter", "SystemMonitorController")
    require(system_monitor, "required property var presentation", "SystemMonitorController")
    require(system_monitor, "required property var control", "SystemMonitorController")
    require(
        system_monitor,
        "readonly property bool systemRebootArmed: false",
        "SystemMonitorController",
    )

    # The behavioral suite must lock the safety/accounting invariants that a
    # string-only architecture audit cannot prove by itself.
    for test_name in (
        "test_processIdentityRejectsPidReuseMismatch",
        "test_protectedActionUnlockRelocksAfterCancel",
        "test_confirmedActionRevalidatesCapturedTarget",
        "test_resourceScopeBlocksProtectedProcesses",
        "test_verifiedKernelResultsRemainPerPidAndMixed",
        "test_partialMutationKeepsSuccessfulKernelTruthOnly",
        "test_successfulBatchDoesNotOverwriteClampedPidTruth",
        "test_freezeOptimismLesionRemainsExplicitCompatibility",
        "test_rssCriticalMetricPreservesDonorMemBehavior",
    ):
        require(
            contract_test,
            "function " + test_name + "(",
            "Team1ProcessSystemContracts",
        )

    forbid(
        contract_test,
        "Quickshell.execDetached(",
        "Team1ProcessSystemContracts",
    )
    forbid(
        contract_test,
        "ProcessLimitMutation {",
        "Team1ProcessSystemContracts",
    )

    # Prepared shared organs must not treat AppControl itself as a backend.
    for label, text in (
        ("ProcessIdentity", identity),
        ("ProcessScope", scope),
        ("ProcessSafety", safety),
        ("ProcessControl", control),
        ("ProcessLimitMutation", limit_mutation),
        ("ProcessActionController", action),
        ("ProcessResourceScope", resource_scope),
        ("ProcessResourceState", resource_state),
        ("ProcessResourceController", resource_controller),
        ("ProcessPresentation", presentation),
        ("SystemControl", system_control),
        ("SystemPresentation", system_presentation),
        ("SystemMonitorController", system_monitor),
    ):
        forbid(text, "appControlWindow", label)
        forbid(text, "AppControlW", label)

    if not failures:
        ok("prepared Process/System architecture contracts are intact")


def audit_scope(base: str | None) -> None:
    if not base:
        return

    output = run_git("diff", "--name-only", base, "--")
    if failures and not output:
        return

    changed = [line.strip() for line in output.splitlines() if line.strip()]
    bad = [
        path
        for path in changed
        if not any(
            path == prefix or path.startswith(prefix)
            for prefix in ALLOWED_TEAM1_DIFF_PREFIXES
        )
    ]

    if bad:
        fail(
            "Team 1 branch touches files outside parallel-safe territory: "
            + ", ".join(bad)
        )
    else:
        ok(
            f"git scope from {base}: "
            f"{len(changed)} changed file(s), all inside Team 1 territory"
        )

    if "widgets/AppControlW.qml" in changed:
        fail("serialized host tissue touched: widgets/AppControlW.qml")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        help="optional git base SHA/ref for changed-file scope audit",
    )
    args = parser.parse_args()

    audit_architecture()
    audit_scope(args.base)

    print("=== TEAM 1 STATIC AUDIT ===")
    for message in passes:
        print("PASS:", message)
    for message in failures:
        print("FAIL:", message)

    if failures:
        print(f"RESULT: FAIL ({len(failures)} issue(s))")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
