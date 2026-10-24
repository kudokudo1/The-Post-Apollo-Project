#!/usr/bin/env python3
"""FinanceW Research M1 source contracts; offline and non-mutating."""
from pathlib import Path
import ast

base = Path(__file__).resolve().parents[2]
finance = (base/"widgets/FinanceW.qml").read_text()
pane = (base/"widgets/FinanceResearchCrawlPane.qml").read_text()
service = (base/"services/finance/FinanceCrawlReadService.qml").read_text()
bridge = (base/"scripts/finance/read_scrapy_crawl.mjs").read_text()
spider = (base/"scripts/finance/crawler/finance_demo_source_spider.py").read_text()
host = (base/"widgets/FinanceToolHost.qml").read_text()

# The existing single M0 tool host and Market/Osiris are not replaced.
assert finance.count("PanelWindow {") == 1
assert finance.count("FinanceToolHost {") == 1
assert 'embeddedComponent: marketPaneComponent' in finance
assert 'showEmbedded: root.selectedMainMode === "market"' in finance
assert 'FinanceResearchCrawlPane {' in finance
assert 'visible: root.selectedMainMode === "research"' in finance
assert 'crawlFeed: crawlService' in finance
assert 'FinanceServices.FinanceCrawlReadService {' in finance
assert 'monitoring: root.menuOpen && root.selectedMainMode === "research"' in finance
assert 'crawlService.state === "ready" ? "SNAPSHOT"' in finance
assert 'property Component embeddedComponent: null' in host

# No continuous crawler and no new process in FinanceW itself.
assert 'Process {' not in finance + pane
assert 'onLeftClicked: crawlFeed.refresh()' in pane
assert 'readonly property bool wide: width >= 650' in pane
assert 'TapHandler {' in pane
assert 'DISCOVERED HYPERLINKS' in pane
assert 'LOCAL SCRAPY JSON // READ ONLY // NOT LIVE' in pane
assert 'Text.PlainText' in pane

# Quickshell starts no crawler; this service launches a local read-only Node
# bridge on entry/Refresh and holds no credentials or write capabilities.
assert 'if (!monitoring || reader.running || loading)' in service
assert 'Quickshell.shellPath("scripts/finance/read_scrapy_crawl.mjs")' in service
assert 'FINANCE_CRAWL_SNAPSHOT ' in service
assert 'FINANCE_CRAWL_ERROR ' in service
assert 'catch (error)' in service
assert 'readOnly !== true' in service
assert 'lstat' in bridge and 'st.isSymbolicLink()' in bridge
assert 'st.size > MAX_BYTES' in bridge
assert '"finance-demo-scrapy"' in bridge
assert '"quotes.toscrape.com"' in bridge
assert 'normalizeCrawl(raw)' in bridge
assert 'readOnly: true' in bridge

# Spider is limited to a permitted test site, three pages and one connection.
ast.parse(spider)
assert 'allowed_domains = ["quotes.toscrape.com"]' in spider
assert 'start_urls = ["https://quotes.toscrape.com/"]' in spider
assert '"ROBOTSTXT_OBEY": True' in spider
assert '"CONCURRENT_REQUESTS": 1' in spider
assert '"CLOSESPIDER_PAGECOUNT": 3' in spider
assert '"DOWNLOAD_DELAY": 1' in spider
assert 'response.css("li.next a::attr(href)")' in spider

for forbidden in ("Qt.openUrlExternally", "financeWrite.submit(",
                  "financeFundingWrite.submit(", "setBudgetAmount(",
                  "writeFile(", "fetch(", "https://gamma-api.polymarket.com"):
    assert forbidden not in pane + service + bridge, forbidden
print("FinanceW Research Scrapy Source Crawl integration contracts: PASS")
