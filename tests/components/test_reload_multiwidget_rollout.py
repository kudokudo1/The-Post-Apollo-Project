#!/usr/bin/env python3
"""Multi-widget ReloadButton rollout; source-only, no desktop/data actions."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

GIT = read("widgets/GitW.qml")
HOSPITAL = read("widgets/HospitalW.qml")
COMPANY = read("widgets/CompanyNetworkW.qml")
COVERAGE = read("widgets/CompanyCoveragePane.qml")
FINANCE = read("widgets/FinanceW.qml")
TRASH = read("modules/Trash.qml")
CAMERA = read("widgets/CameraW.qml")
BUTTON = read("components/ReloadButton.qml")
QMLDIR = read("components/qmldir")

assert "ReloadButton 1.0 ReloadButton.qml" in QMLDIR
assert 'label: "⟳"' in BUTTON
assert "signal reloadRequested()" in BUTTON
assert "onLeftClicked: reloadButton.reloadRequested()" in BUTTON
assert "property color semanticColor: Colors.yellow" in BUTTON
assert "property color hoverSurfaceColor: Colors.orange" in BUTTON
for name, source in (
    ("Git", GIT), ("Hospital", HOSPITAL), ("Company", COMPANY),
    ("Finance", FINANCE), ("Trash", TRASH), ("Camera", CAMERA),
):
    assert source.count("ReloadButton {") == 1, f"{name}: expected one header reload"
    assert "onReloadRequested:" in source, name
    assert "CloseButton {" in source, name
    assert "semanticColor: Colors.yellow" in source, name
    assert "hoverSurfaceColor: Colors.orange" in source, name
    assert "Accessible.name:" in source, name

# Git: the existing REFRESH command is a view-sensitive read path,
# not a new remote FETCH/PULL/PUSH. Preserve both header resizing controls.
assert 'onReloadRequested: root.invokeGitHotkey("REFRESH")' in GIT
refresh_case = GIT.split('if (action === "REFRESH") {', 1)[1].split(
    'if (activePage !== "git")', 1)[0]
for needle in (
    'githubService.refresh();', 'githubProjectsService.refreshProjects();',
    'gitService.discoverRepos();', 'githubWorkItemsService.refreshIssues(',
    'githubWorkItemsService.refreshPulls(',
):
    assert needle in refresh_case, needle
assert "runSyncAction(" not in refresh_case
assert "id: gitHeaderActions" in GIT
assert "width: Math.max(0, parent.width - gitHeaderActions.width - 12)" in GIT

# Hospital: the reload only chooses observed local/remote sources. No
# certification, Room operation, merge, process activation or save.
hospital_refresh = HOSPITAL.split("function refreshHospitalView() {", 1)[1].split(
    "function refreshReceptionData()", 1)[0]
for needle in (
    'root.operationsSurface === "attention"',
    "root.refreshGithubAttention();",
    "roomReportCatalogService.refresh();",
    "roundsService.refresh();",
    "specialistRegistryService.refreshPresence();",
    "floorService.discover();",
):
    assert needle in hospital_refresh, needle
for forbidden in (
    "certificationCoordinator.", "roomService.run", "hospitalMergeQueueProvider.",
    "patientService.save", "openArchive(",
):
    assert forbidden not in hospital_refresh, forbidden
assert 'onReloadRequested: root.refreshHospitalView()' in HOSPITAL
assert 'root.operationsSurface !== "archive"' in HOSPITAL
assert "right: hospitalHeaderActions.left" in HOSPITAL

# Company: no resetting the map's Loader, center/zoom, current selection, or
# invoking online maps without existing explicit street consent.
company_refresh = COVERAGE.split("function refreshVisibleCoverage() {", 1)[1].split(
    "function openVectorChoice()", 1)[0]
for needle in (
    "hubEditorOpen", 'hubStore.state === "saving"',
    "if (streetMode)", "streetMap.active && streetMap.requestTiles();",
    "return hubStore.refresh();",
):
    assert needle in company_refresh, needle
for forbidden in (
    "regionKey =", "selectedCode =", "centerLon =", "centerLat =",
    "zoom =", "launchVector(", "openVectorChoice(", "hubStore.update(",
):
    assert forbidden not in company_refresh, forbidden
assert "!!coverageLoader.item" in COMPANY
assert 'coverageLoader.item.refreshVisibleCoverage();' in COMPANY
assert "anchors.right: companyHeaderReloadButton.left" in COMPANY

# Finance: only on explicit reader-equipped pages; no protected writers,
# transfers or draft reloads. Read-only public feed is not account syncing.
finance_refresh = FINANCE.split("function refreshFinanceVisibleSource() {", 1)[1].split(
    "function selectBudgetSection(", 1)[0]
for needle in (
    "marketService.refresh();", "secService.refresh()", "crawlService.refresh()",
    "financeBudget.refresh();", "return false;",
):
    assert needle in finance_refresh, needle
for forbidden in ("financeFundingWrite.", "financeWrite.", "financeAllocationWrite.",
                  "financeDrafts.refresh()", "transfer", "sendPayment"):
    assert forbidden not in finance_refresh, forbidden
assert 'selectedMainMode === "market"' in FINANCE
assert 'researchTool === "sec" || researchTool === "crawl"' in FINANCE
assert 'selectedBudgetSubMode === "budget"' in FINANCE
assert '!transactionDraftPane.open' in FINANCE
assert '!fundingReviewOpen' in FINANCE
assert "available: root.headerReloadAvailable" in FINANCE
assert "anchors.right: financeHeaderReloadButton.left" in FINANCE

# Trash: refresh mode is passive; never clear burn receipts, confirmation
# or invoke burn/restore from the new header.
trash_refresh = TRASH.split("function refreshVisibleInventory() {", 1)[1].split(
    "function refresh(clearReceipt, passive)", 1)[0]
assert 'confirmMode !== ""' in trash_refresh
assert 'burnUiStage !== ""' in trash_refresh
assert 'activeMode === "cleanup"' in trash_refresh
assert "return refreshArchive();" in trash_refresh
assert "return refresh(false, true);" in trash_refresh
assert "receipt = \"\"" not in trash_refresh
for forbidden in ("burn(", "burnAll(", "runBurn(", "moveToTrash(", "hospitalRestore."):
    assert forbidden not in trash_refresh
assert "id: trashHeaderRow" in TRASH
assert "trashHeaderReloadButton.width" in TRASH
assert "trashHeaderRow.spacing * 5" in TRASH

# Camera: read-only status and existing gallery inventory only. Never
# auto-take a screenshot, open Zoom or mutate cleanup/Trash marks.
camera_refresh = CAMERA.split("function refreshVisibleCamera() {", 1)[1].split(
    "function loadGallery(append, targetView)", 1)[0]
assert 'activeView === "gallery"' in camera_refresh
assert 'loadGallery(false, "gallery")' in camera_refresh
assert 'activeView === "capture"' in camera_refresh
assert 'run("status", ["status"]);' in camera_refresh
assert 'camera.activeView === "gallery"' in CAMERA
assert 'camera.activeView === "capture"' in CAMERA
assert "cameraHeaderReloadButton.width" in CAMERA
for forbidden in ("screenshot", "trash", "zoom-enter", "remove", "delete"):
    assert forbidden not in camera_refresh.lower(), forbidden

print("MULTI-WIDGET RELOAD: 6 header integrations and safe source dispatch PASS")
