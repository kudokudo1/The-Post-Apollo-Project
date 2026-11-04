#!/usr/bin/env python3
"""Opt-in, single-publisher ANGEL interpretation reference lookup.

Never runs automatically and never modifies the observation journal. It may
send an HTTPS request to Astrology.com (the publisher sees the user's IP).
No arbitrary URL, browser, cookie store, cache, credentials or shell process.
Only a short, verbatim reference excerpt is returned, labelled as a claim
from its publisher, not as established astronomy or a verified prediction.
"""
import html
from html.parser import HTMLParser
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = "https://www.astrology.com/numerology/angel-numbers/"
HOST = "www.astrology.com"
MAX_BYTES = 512000
TIMEOUT = 9
WORD_LIMIT = 20


def valid_digits(value):
    return isinstance(value, str) and 1 <= len(value) <= 4 and value.isascii() and value.isdecimal()


def source_url(digits):
    return ROOT + digits + "-meaning" if valid_digits(digits) else ""


def unavailable(digits, status):
    return {"status": status, "digits": digits, "provider": "Astrology.com"}


class SamePublisherRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url = urllib.parse.urlsplit(newurl)
        if url.scheme != "https" or url.hostname != HOST or url.port is not None:
            raise urllib.error.URLError("redirect not allowed")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class ShortSectionParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items = []
        self.kind = ""
        self.buffer = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "iframe"):
            self.skip += 1
        elif self.skip == 0 and self.kind == "" and tag in ("h1", "h2", "h3", "h4", "p"):
            self.kind = tag
            self.buffer = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "iframe") and self.skip:
            self.skip -= 1
        elif self.skip == 0 and self.kind == tag:
            value = " ".join("".join(self.buffer).split())
            if value:
                self.items.append((tag, html.unescape(value)))
            self.kind = ""
            self.buffer = []

    def handle_data(self, data):
        if self.skip == 0 and self.kind:
            self.buffer.append(data)


def extract_reference(page_html, digits):
    """Return a very short excerpt only from the exact number's numerology section."""
    if not valid_digits(digits) or not isinstance(page_html, str):
        return None
    reader = ShortSectionParser()
    reader.feed(page_html)
    heading = re.compile(r"^" + re.escape(digits) + r"\s+Angel\s+Number\s+meaning$", re.I)
    if not any(tag == "h1" and heading.match(value) for tag, value in reader.items):
        return None
    section_heading = re.compile(
        r"^Numerology\s+Meaning\s+of\s+Angel\s+Number\s+" + re.escape(digits) + r"$", re.I
    )
    found = False
    for tag, value in reader.items:
        if tag.startswith("h"):
            if section_heading.match(value):
                found = True
            elif found:
                return None
        elif tag == "p" and found:
            # Limit both content and word count. Do not reproduce articles,
            # or silently use an unrelated paragraph as a sourced claim.
            words = value.split()
            if len(words) < 3:
                continue
            excerpt = " ".join(words[:WORD_LIMIT])[:240].strip()
            return excerpt if len(excerpt) >= 10 else None
    return None


def lookup(digits, opener=None):
    if not valid_digits(digits):
        return unavailable(digits, "UNSUPPORTED_DIGITS")
    url = source_url(digits)
    if opener is None:
        opener = urllib.request.build_opener(SamePublisherRedirect())
    request = urllib.request.Request(
        url, headers={
            "User-Agent": "Post-Apollo-ANGEL/1.0 (explicit reference lookup)",
            "Accept": "text/html",
            "Accept-Language": "en",
        }, method="GET")
    try:
        with opener.open(request, timeout=TIMEOUT) as response:
            final = urllib.parse.urlsplit(response.geturl())
            if final.scheme != "https" or final.hostname != HOST or final.path != urllib.parse.urlsplit(url).path:
                return unavailable(digits, "SOURCE_REDIRECT_REJECTED")
            content_type = response.headers.get_content_type()
            if content_type != "text/html":
                return unavailable(digits, "SOURCE_TYPE_UNSUPPORTED")
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                return unavailable(digits, "SOURCE_TOO_LARGE")
            charset = response.headers.get_content_charset() or "utf-8"
            if charset.lower() not in ("utf-8", "iso-8859-1", "windows-1252"):
                return unavailable(digits, "SOURCE_ENCODING_UNSUPPORTED")
            page = raw.decode(charset, "replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError):
        return unavailable(digits, "SOURCE_UNAVAILABLE")

    excerpt = extract_reference(page, digits)
    if not excerpt:
        return unavailable(digits, "SOURCE_NOT_VERIFIED")
    return {
        "status": "ready", "digits": digits, "provider": "Astrology.com",
        "url": url, "section": "Numerology meaning", "excerpt": excerpt,
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    digits = args[0] if len(args) == 1 else ""
    print(json.dumps(lookup(digits), ensure_ascii=True))


if __name__ == "__main__":
    main()
