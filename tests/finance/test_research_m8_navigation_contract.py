#!/usr/bin/env python3
"""Research M8: actual FinanceW Research tab integration without new writers."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
finance = (root / "widgets/FinanceW.qml").read_text()
picker = (root / "widgets/FinanceResearchEvidenceCandidatePicker.qml").read_text()
host = (root / "widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").read_text()
bridge = (root / "scripts/finance/research_candidate_preview_bridge.mjs").read_text()

# One existing mapped FinanceW window; source service instances remain unique.
assert finance.count("PanelWindow {") == 1
for owner in (
    "FinanceServices.FinanceCrawlReadService {",
    "FinanceServices.FinanceSecReadService {",
    "FinanceServices.FinanceSecDocumentReadService {",
    "FinanceServices.FinanceSecPriceReadService {",
):
    assert finance.count(owner) == 1, owner

# Preserve the original controls and intentionally add one read-only route.
for marker in (
    'property string researchTool: "crawl"',
    'label: "SOURCE CRAWL"',
    'label: "SEC EDGAR"',
    'label: "CANDIDATES"',
    'selected: root.researchTool === "candidates"',
    'onLeftClicked: root.researchTool = "candidates"',
    'FinanceResearchCrawlPane {',
    'FinanceSecFilingsPane {',
    'FinanceResearchEvidenceCandidatePreviewHost {',
    'id: candidateHost',
    'visible: root.researchTool === "candidates"',
    'active: root.menuOpen',
    '&& root.selectedMainMode === "research"',
    '&& root.researchTool === "candidates"',
    'secFeed: secService',
    'crawlFeed: crawlService',
):
    assert marker in finance, marker
assert finance.count('FinanceResearchEvidenceCandidatePreviewHost {') == 1
assert finance.count('label: "CANDIDATES"') == 1
assert finance.count('id: researchToolStrip') == 1
# Compact 9:16 FinanceW gives Research much less than full frame width.
# The three tab controls must all fit, while their original maxima remain.
for marker in (
    "width: parent.width",
    "readonly property real tabAvailableWidth:",
    "Math.max(0, width - spacing * 2)",
    "researchToolStrip.tabAvailableWidth * 0.37",
    "researchToolStrip.tabAvailableWidth * 0.28",
    "researchToolStrip.tabAvailableWidth * 0.34",
):
    assert marker in finance, marker
for compact_content_width in (220, 260, 280, 300, 432):
    available = max(0, compact_content_width - 12)
    widths = (
        min(120, int(available * 0.37)),
        min(92, int(available * 0.28)),
        min(109, int(available * 0.34)),
    )
    assert sum(widths) + 12 <= compact_content_width, (
        compact_content_width, widths
    )
assert 'anchors.top: researchToolStrip.bottom' in finance

# The Finance header reports the candidate preview's own status, not a fake
# live feed; its reload stays restricted to explicit SEC/Crawl modes.
for marker in (
    'selectedMainMode === "research" && researchTool === "candidates"',
    'candidateHost.previewState === "loading" ? "READING"',
    'candidateHost.previewState === "failed" ? "ERROR"',
    'candidateHost.previewState === "ready"',
    'candidateHost.previewResult.secPresent',
    'candidateHost.previewResult.demoPresent',
    '&& (researchTool === "sec" || researchTool === "crawl")',
):
    assert marker in finance, marker
reload_section = finance[
    finance.index("readonly property bool headerReloadAvailable:"):
    finance.index("function selectBudgetSection(")
]
assert 'researchTool === "candidates"' not in reload_section
assert 'return researchTool === "sec"' in reload_section

# No second provider or new writer is instantiated from the M8 route.
for forbidden in (
    'FinanceServices.FinanceResearchCandidateWriteService {',
    'FinanceServices.FinanceResearchInvestigationWriteService {',
    'FinanceResearchWriteAttempt {',
    'FinanceResearchInvestigationStore {',
    'writeEnabled: true',
    'Qt.openUrlExternally',
):
    assert forbidden not in finance, forbidden
for marker in (
    'property bool active: false', 'property var secFeed: null',
    'property var crawlFeed: null',
    'FinanceServices.FinanceResearchCandidatePreviewService {',
    'secFeed: host.secFeed', 'crawlFeed: host.crawlFeed',
    'onPreviewRequested: previewService.refresh()',
):
    assert marker in host, marker
assert 'Process {' not in host
assert 'onAttachRequested:' not in host
assert 'onCreateRequested:' not in host
assert 'onRemoveRequested:' not in host
assert 'import fs' not in bridge and 'import { run ' not in bridge
assert 'previewEvidenceCandidates' in bridge
assert 'PREVIEW ONLY // SOURCE CONTENT NOT AUTHENTICATED // NO WRITES' in picker

# Correct explicit directory imports. Neither folder has a qmldir to register
# (which was a separate Diagnostics startup problem on the components module).
assert (root/"widgets/FinanceResearchEvidenceCandidatePreviewHost.qml").is_file()
assert (root/"widgets/FinanceResearchEvidenceCandidatePicker.qml").is_file()
assert (root/"services/finance/FinanceResearchCandidatePreviewService.qml").is_file()
assert not (root/"widgets/qmldir").exists()
assert not (root/"services/finance/qmldir").exists()

print("Finance Research M8 live-menu read-only integration contract: PASS")
