#!/usr/bin/env python3
"""B6 installed-application index contracts, without launch privileges."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
bridge = (ROOT / "services/hub/ApolloHubLiveBridge.qml").read_text(encoding="utf-8")
policy = (ROOT / "services/hub/ApolloHubAppsPolicy.js").read_text(encoding="utf-8")
layout = (ROOT / "services/hub/ApolloHubLayout.js").read_text(encoding="utf-8")
shell = (ROOT / "shell.qml").read_text(encoding="utf-8")
workflow = (ROOT / ".github/workflows/apollo-hub-live-bridge.yml").read_text(encoding="utf-8")

for needle in (
    'import "ApolloHubAppsPolicy.js" as AppsPolicy',
    'property string appsQuery: ""',
    "readonly property var desktopApplicationEntries:",
    "DesktopEntries.applications ? DesktopEntries.applications.values : null",
    "readonly property var appsSnapshot:",
    "AppsPolicy.snapshot(desktopApplicationEntries, appsQuery)",
):
    assert needle in bridge, f"Missing desktop entry observation seam: {needle}"

for needle in (
    ".pragma library", "function normalize(", "function snapshot(",
    "function collectionLength(", "applicationCount = collectionLength(applications)",
    "for (var i = 0; i < applicationCount; ++i)",
    "function byName(", "MAX_ITEMS = 24", "MAX_QUERY_LENGTH = 80",
    "genericName:", "icon:", "installedCount:", "matchCount:",
    "shownCount:", "truncated:", "source: \"desktop-entries\"",
    'state: "unavailable"', '"empty"', '"ready"',
):
    assert needle in policy, f"Missing safe native catalog projection: {needle}"

assert '{ module: "apps", size: "wide" }' in layout
assert shell.count("ApolloHubLiveBridge {") == 1
assert bridge.count("DesktopEntries.applications") == 2
assert "DesktopEntries.byId(" not in bridge
assert "DesktopEntries.heuristicLookup(" not in bridge
# Application actions and command lines stay outside this projection.
for forbidden in (
    "Process {", "FileView {", "DesktopEntries {",
    "Quickshell.execDetached(", "DesktopEntries.byId(",
    "DesktopEntries.heuristicLookup(", ".execute(", ".launch(",
    ".command", ".workingDirectory", ".execString",
    "onClicked:", "onPressed:",
):
    assert forbidden not in bridge + policy, f"Hub catalog must not launch: {forbidden}"
assert "source: \"desktop-entries\"" in policy
for needle in (
    '"services/hub/ApolloHubAppsPolicy.js"',
    '"tests/hub/test_apollo_hub_apps_policy.cjs"',
    '"tests/hub/test_apollo_hub_apps_bridge.py"',
    "python3 tests/hub/test_apollo_hub_apps_bridge.py",
    "node tests/hub/test_apollo_hub_apps_policy.cjs",
):
    assert needle in workflow, f"Missing B6 CI path/step: {needle}"
print("ApolloHub B6 native desktop-entry catalog static contracts passed")
