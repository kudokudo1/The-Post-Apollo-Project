"""FinanceW Source Crawl M1: three-page, permission-conscious Scrapy smoke spider.

This pilot is intentionally pinned to quotes.toscrape.com. It cannot be used
as an arbitrary URL fetcher or an unrestricted recursive spider.
"""
from datetime import datetime, timezone
from urllib.parse import urlparse

import scrapy


class FinanceDemoSourceSpider(scrapy.Spider):
    name = "finance_demo_source"
    allowed_domains = ["quotes.toscrape.com"]
    start_urls = ["https://quotes.toscrape.com/"]
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "DOWNLOAD_DELAY": 1,
        "DOWNLOAD_TIMEOUT": 12,
        "RETRY_TIMES": 1,
        "CLOSESPIDER_PAGECOUNT": 3,
        "COOKIES_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "REMOTE_CONTROL_ENABLED": False,
        "LOG_LEVEL": "WARNING",
    }

    def parse(self, response):
        links = []
        seen = set()
        for href in response.css("a[href]::attr(href)").getall():
            target = response.urljoin(href)
            parsed = urlparse(target)
            if (
                parsed.scheme != "https"
                or parsed.hostname != "quotes.toscrape.com"
                or parsed.username
                or parsed.password
            ):
                continue
            clean_target = parsed._replace(fragment="").geturl()
            if clean_target not in seen:
                seen.add(clean_target)
                links.append(clean_target[:400])
            if len(links) >= 32:
                break

        snippets = [
            text.strip()[:240]
            for text in response.css("div.quote span.text::text").getall()[:3]
            if text.strip()
        ]
        yield {
            "schemaVersion": 1,
            "source": "finance-demo-scrapy",
            "readOnly": True,
            "url": response.url,
            "title": (response.css("title::text").get() or "").strip()[:150],
            "observedAt": datetime.now(timezone.utc).isoformat(),
            "snippets": snippets,
            "links": links,
        }

        # Only the site's explicit NEXT pagination is followed.
        # CLOSESPIDER_PAGECOUNT caps all page processing at three pages.
        next_href = response.css("li.next a::attr(href)").get()
        if next_href:
            next_url = response.urljoin(next_href)
            parsed = urlparse(next_url)
            if parsed.scheme == "https" and parsed.hostname == "quotes.toscrape.com":
                yield response.follow(next_url, callback=self.parse)
