#!/usr/bin/env python3
"""FinanceW SEC M2 official EDGAR submissions, read-only and opt-in."""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
finance = (root/"widgets/FinanceW.qml").read_text()
sec = (root/"widgets/FinanceSecFilingsPane.qml").read_text()
service = (root/"services/finance/FinanceSecReadService.qml").read_text()
reader = (root/"scripts/finance/read_sec_filings.mjs").read_text()
crawl = (root/"widgets/FinanceResearchCrawlPane.qml").read_text()
market = (root/"widgets/FinanceMarketPane.qml").read_text()

assert finance.count("PanelWindow {") == 1
assert finance.count("FinanceToolHost {") == 1
assert "embeddedComponent: marketPaneComponent" in finance
assert 'property string researchTool: "crawl"' in finance
assert 'root.researchTool = "crawl"' in finance
assert 'root.researchTool = "sec"' in finance
assert 'label: "SEC EDGAR"' in finance
assert 'FinanceSecFilingsPane {' in finance
assert 'secFeed: secService' in finance
assert 'visible: root.researchTool === "sec"' in finance
assert 'visible: root.researchTool === "crawl"' in finance
assert 'crawlFeed: crawlService' in finance
assert 'FinanceServices.FinanceSecReadService {' in finance
assert 'secService.state === "ready" ? "SNAPSHOT"' in finance
assert 'FinanceResearchCrawlPane {' in finance
assert 'onLeftClicked: crawlFeed.refresh()' in crawl
assert 'POLYMARKET' in market and 'OSIRIS' in market

assert 'onLeftClicked: secFeed.refresh()' in sec
assert 'secFeed.selectIssuer("0000320193")' in sec
assert 'secFeed.selectIssuer("0000789019")' in sec
assert 'secFeed.selectIssuer("0001045810")' in sec
assert 'readonly property bool wide: width >= 650' in sec
assert 'TapHandler {' in sec
assert 'index only' in sec.lower()
assert 'SEC DATA.SEC.GOV // PUBLIC SNAPSHOT // NOT LIVE' in sec
assert 'Text.PlainText' in sec

assert 'if (!monitoring) return false;' in service
assert 'if (reader.running)' in service
assert 'selectedCik !== inFlightCik' in service
assert 'Quickshell.shellPath("scripts/finance/read_sec_filings.mjs")' in service
assert 'FINANCE_SEC_ERROR ' in service
assert 'FINANCE_SEC_SNAPSHOT ' in service
assert 'onExited: function(exitCode, exitStatus)' in service
assert 'catch (error)' in service

assert 'https://data.sec.gov/submissions/CIK' in reader
assert 'https://www.sec.gov/Archives/edgar/data/' in reader
assert 'method:"GET"' in reader
assert 'AbortSignal.timeout(12000)' in reader
assert 'const agent = await agentLoader();' in reader
assert '"User-Agent":agent' in reader
assert 'st.isSymbolicLink()' not in reader # different local security proof
assert 'stat.isSymbolicLink()' in reader
assert '(stat.mode & 0o077) !== 0' in reader
assert 'identity-required' in reader
assert 'redirect:"error"' in reader
assert 'MAX_RETURN = 30' in reader

for forbidden in ('Qt.openUrlExternally','Process {','writeFile(',
                  'financeWrite.submit(', 'fetch(', 'openUrl('):
    assert forbidden not in sec + finance[finance.index('// Research tools share'):], forbidden
print("FinanceW SEC EDGAR M2 isolated read-only source contracts: PASS")
