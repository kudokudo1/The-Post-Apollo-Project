#!/usr/bin/env python3
"""Static ownership guard for Team 8's isolated APPS core.

Run from the repository root:
    python3 services/apps/validate_app_core_contract.py

This is a parallel-floor contract check. It does not validate AppControl host
integration and does not replace runtime behavior certification.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_DIR = ROOT / "services" / "apps"

FILES = {
    "core": APP_DIR / "AppCoreProvider.qml",
    "launch": APP_DIR / "AppLaunchPlanner.qml",
    "bottles": APP_DIR / "AppBottleProvider.qml",
    "actions": APP_DIR / "AppActionCatalog.qml",
    "actionPlanner": APP_DIR / "AppActionPlanner.qml",
    "catalog": APP_DIR / "AppCatalogPolicy.qml",
}

errors: list[str] = []
texts: dict[str, str] = {}

for key, path in FILES.items():
    if not path.exists():
        errors.append(f"missing Team 8 file: {path.relative_to(ROOT)}")
        continue
    texts[key] = path.read_text(encoding="utf-8")

required_functions = {
    "core": {
        "desktopEntries",
        "sourceEntries",
        "entryIsFlatpak",
        "sourceLabel",
        "entryHasLaunchCommand",
        "entryMatchesSource",
        "entryLaunchableForSource",
        "actionsAvailableForSource",
        "displayName",
        "displayDescription",
        "longDescription",
        "displayIcon",
        "iconSource",
    },
    "launch": {
        "cleanedCommandTokens",
        "launchExecutableName",
        "bottleNamesFromPayload",
        "bottleProgramName",
        "normalPlan",
        "toolboxPlan",
        "bottlePlan",
        "plan",
        "withSuppliedAugmentation",
    },
    "bottles": {
        "collectNames",
        "namesFromPayload",
        "namesFromText",
        "parseNames",
        "refresh",
    },
    "actions": {
        "browserKind",
        "desktopActions",
        "shortcutSequence",
        "launchArguments",
    },
    "actionPlanner": {
        "stableActionId",
        "desktopActionPlan",
        "browserBuiltinPlan",
        "plan",
    },
    "catalog": {
        "entryKey",
        "searchHaystack",
        "matchesSearch",
        "hiddenMatchesSearch",
        "compareEntries",
        "desktopRows",
        "hiddenRows",
        "rows",
    },
}

for key, required in required_functions.items():
    text = texts.get(key, "")
    functions = set(
        re.findall(
            r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            text,
            re.M,
        )
    )
    missing = sorted(required - functions)
    if missing:
        errors.append(
            f"{key}: missing required functions: {', '.join(missing)}"
        )

# Foreign physiology/host ownership must stay out of all isolated APPS-core
# implementation files. Comments are intentionally included: an ownership
# regression should be explicit enough to make this validator fail loudly.
forbidden = {
    "appControlWindow": "AppControl host coupling",
    "selectedResult": "host selection/detail coupling",
    "searchInput": "host search/navigation coupling",
    "menuOpen": "host menu lifetime",
    "swayWindows": "Sway/window provider ownership",
    "windowMatchesApp": "Team 7 identity join",
    "appEntryForWindow": "Team 7 identity join",
    "appEntryForTab": "Team 7 identity join",
    "appTabs": "Team 5 tab/surface ownership",
    "TabSurfaceProvider": "Team 5 provider implementation coupling",
    "appAudio": "Team 6 application audio ownership",
    "windowAudio": "Team 6 window audio ownership",
    "tabAudio": "Team 6 tab audio ownership",
    "selectedResourceScope": "Team 1 process/resource ownership",
    "ProcessControl": "Team 1 process control ownership",
    "ProcessLimits": "Team 1 resource-limit ownership",
    "FavoritesStore": "Team 2 Favorites persistence ownership",
    "favoriteStore": "Team 2 Favorites persistence ownership",
}

for key, text in texts.items():
    for token, owner in forbidden.items():
        if token in text:
            errors.append(f"{key}: forbidden token {token!r}: {owner}")

# Planning/catalog files must remain pure. They describe intent; they do not
# launch processes, create workers/timers, or mutate the desktop. Bottles is a
# discovery provider and therefore may own its bottles-cli Process.
for key in ("launch", "actions", "actionPlanner", "catalog"):
    text = texts.get(key, "")
    for token in (
        "Quickshell.execDetached",
        "Process {",
        "Timer {",
        "StdioCollector",
        "SplitParser",
    ):
        if token in text:
            errors.append(
                f"{key}: execution/lifecycle token present: {token!r}"
            )

# Team 8 may consume DesktopEntries in its catalog provider, but must not turn
# its local behavior classification into a canonical identity service.
for key, text in texts.items():
    for token in (
        "semanticKey",
        "canonicalIdentity",
        "ApplicationEntity",
        "resolvedIdentity",
    ):
        if token in text:
            errors.append(
                f"{key}: canonical identity token present: {token!r}"
            )

# SurfaceLaunch ownership is resolved, but provider-specific requirement
# construction remains T5-domain-owned. Team 8 may carry/apply a supplied
# augmentation; it must not recreate Kitty/AT-SPI/DevTools requirement policy
# inside APPS core.
for token in (
    "force-renderer-accessibility",
    "remote-debugging-port",
    "KITTY_LISTEN_ON",
    "allow_remote_control=socket-only",
    "NO_AT_BRIDGE",
):
    for key, text in texts.items():
        if token in text:
            errors.append(
                f"{key}: T5-domain SurfaceLaunch detail leaked into APPS core: "
                f"{token!r}"
            )

if errors:
    print("TEAM 8 APPS CORE CONTRACT: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("TEAM 8 APPS CORE CONTRACT: PASS")
for key, path in FILES.items():
    print(" -", key, path.relative_to(ROOT))
print(" host coupling: none")
print(" Team 1/5/6/7 physiology: none")
print(" SurfaceLaunch requirement policy: external / T5-domain-owned")
print(" supplied augmentation carriage: Team 8 launch-plan responsibility")
print(" Bottles discovery: isolated Team 8 provider")
print(" browser/desktop action policy: pure Team 8 planner")
print(" APPS catalog/search/ranking: pure Team 8 policy")
