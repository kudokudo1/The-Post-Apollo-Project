# FinanceW // Research Source Crawl M1

This is a **read-only local snapshot bridge** between the operator's existing
Scrapy installation in `fedora-toolbox-44` and **Finance → Research** in
Quickshell. It never starts a spider on shell startup, polls in the background,
visits arbitrary sites, or changes Budget data.

## Produce the first demo crawl

From **Kitty** (host), enter the existing Toolbox:

```bash
toolbox enter fedora-toolbox-44
```

Inside Toolbox, use the previously verified Python environment:

```bash
source "$HOME/.local/share/post-apollo/finance-crawler/.venv/bin/activate"
mkdir -p "$HOME/.local/share/post-apollo/finance-crawler"
cd "$HOME/.config/quickshell"

scrapy runspider scripts/finance/crawler/finance_demo_source_spider.py \
  -O "$HOME/.local/share/post-apollo/finance-crawler/crawl-records.json"
```

This **overwrites only** the demo export `crawl-records.json`. It crawls
at most three pages of `quotes.toscrape.com`, follows only NEXT pagination,
respects robots.txt, and has a 1-second delay between requests.

The data directory is on the shared user home, visible to Toolbox and host
Quickshell. Scrapy logs may show warnings when websites deny requests.

Optional read-only check before returning to FinanceW:

```bash
node "$HOME/.config/quickshell/scripts/finance/read_scrapy_crawl.mjs"
```

Expected output is one line beginning `FINANCE_CRAWL_SNAPSHOT`. For a missing
file it prints `FINANCE_CRAWL_ERROR missing-export`. Never hand-edit that file
to spoof a successful crawl.

## See data in FinanceW

Open **Finance → Research** and press **REFRESH** if the pane already showed
NO SAVED CRAWL. Choose a page to see its title, URL, extraction time, text
snippet and observed hyperlinks. Compact/Expanded/Fullscreen share the
same stateful component.

The header intentionally says **SNAPSHOT**, not LIVE. This initial demo has
**no investment intelligence or finance signal**, and observed links do not
imply factual or financial relationships. The Constellation graph, real
investment sources, scheduling and crawl-job management are separate
future scopes.

## Safety and rollback

Nothing is installed via rpm-ostree or activated at boot. Stop the process
with Ctrl-C if a crawl is still running. FinanceW only reads a bounded local
file and has no write/execute action for spiders. To disable the data, leave
the file untouched and navigate away from Research; no process is left
running. Reverting this feature PR restores the old Research placeholder.

## Verify in the repo

```bash
node tests/finance/test_scrapy_crawl_bridge.mjs
python3 tests/finance/test_finance_research_crawl_contracts.py
```

CI uses fictional records, never live financial sources or the operator's
private data. Live Quickshell rendering remains an operator acceptance step.
