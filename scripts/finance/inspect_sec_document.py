#!/usr/bin/env python3
"""SEC M3: one opt-in, read-only filing document inspection.

Only fixed issuer CIKs and filings passed from the validated EDGAR index.
No arbitrary URLs, no redirects, no automatic crawling, no writes. The Form 4
parser reads *raw ownership XML*; an xslF345Xnn/ path is a rendered HTML view.
"""
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone
import json
import os
import re
import stat
import sys
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

ISSUERS = {"0000320193", "0000789019", "0001045810"}
ACC = re.compile(r"\d{10}-\d{2}-\d{6}\Z")
DOC = re.compile(r"(?:xslF345X\d{2}/)?[A-Za-z0-9][A-Za-z0-9_.-]{0,170}\Z")
ITEM = re.compile(r"[1-9]\.\d{2}\Z")
HEADING = re.compile(r"\bItem\s+([1-9]\.\d{2})\b", flags=re.I)
MAX_BYTES = 2_000_000
SEC_CONTACT = Path.home() / ".local/share/post-apollo/finance-sec/user-agent.txt"
GROUPS = {
    "1.01": "MATERIAL AGREEMENT", "1.02": "AGREEMENT TERMINATED",
    "1.03": "BANKRUPTCY", "1.05": "CYBERSECURITY INCIDENT",
    "2.01": "ACQUISITION OR DISPOSITION", "2.02": "EARNINGS / RESULTS",
    "2.03": "FINANCIAL OBLIGATION", "2.04": "FINANCIAL OBLIGATION EVENT",
    "2.05": "EXIT OR DISPOSAL COST", "2.06": "MATERIAL IMPAIRMENT",
    "3.01": "LISTING STATUS", "3.02": "UNREGISTERED EQUITY SALE",
    "3.03": "HOLDER RIGHTS", "4.01": "AUDITOR CHANGE",
    "4.02": "NON-RELIANCE / RESTATEMENT", "5.01": "CHANGE IN CONTROL",
    "5.02": "DIRECTORS / OFFICERS", "5.03": "CHARTER / BYLAWS",
    "5.07": "SHAREHOLDER VOTE", "7.01": "REG FD DISCLOSURE",
    "8.01": "OTHER EVENTS", "9.01": "FINANCIAL STATEMENTS / EXHIBITS",
}


def check_args(cik, accession, form, doc, codes=""):
    if cik not in ISSUERS or not ACC.fullmatch(accession):
        raise ValueError("invalid-selection")
    if form not in ("4", "4/A", "8-K", "8-K/A"):
        raise ValueError("unsupported-form")
    if not DOC.fullmatch(doc):
        raise ValueError("invalid-document")
    raw = doc.rsplit("/", 1)[-1]
    if form.startswith("4") and not raw.lower().endswith(".xml"):
        raise ValueError("unsupported-document")
    if form.startswith("8-K") and not raw.lower().endswith((".htm", ".html", ".txt")):
        raise ValueError("unsupported-document")
    parsed_codes = [x.strip() for x in codes.split(",") if x.strip()]
    if len(parsed_codes) > 12 or any(not ITEM.fullmatch(x) for x in parsed_codes):
        raise ValueError("invalid-selection")
    # A Form 4 render URL is HTML, not ownershipDocument XML. Strip only
    # the *known* XSL wrapper and retrieve the raw XML in the filing root.
    fetch_doc = raw if form.startswith("4") else doc
    url = ("https://www.sec.gov/Archives/edgar/data/"
           + str(int(cik)) + "/" + accession.replace("-", "") + "/" + fetch_doc)
    return url, list(dict.fromkeys(parsed_codes))


def load_contact(file=SEC_CONTACT):
    try:
        st = file.lstat()
    except OSError:
        raise ValueError("identity-required") from None
    if not stat.S_ISREG(st.st_mode) or st.st_mode & 0o077 or st.st_size > 180:
        raise ValueError("identity-permissions")
    try:
        raw = file.read_text(encoding="utf8").strip()
    except OSError:
        raise ValueError("identity-unreadable") from None
    if (len(raw) < 9 or re.search(r"[\x00-\x1f\x7f]", raw) or
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9 ._-]{3,80}\s+[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", raw)
            or re.search(r"@example\.(com|net|org)$", raw, re.I)):
        raise ValueError("identity-invalid")
    return raw


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch_document(url, agent, opener=None):
    opener = opener or build_opener(NoRedirect())
    request = Request(url, headers={"User-Agent": agent, "Accept": "application/xml,text/html,text/plain"})
    try:
        with opener.open(request, timeout=12) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("document-too-large")
            raw = response.read(MAX_BYTES + 1)
    except (HTTPError, URLError, OSError, TimeoutError) as error:
        raise ValueError("sec-document-unavailable") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("document-too-large")
    return raw.decode("utf-8-sig", errors="replace")


def child_text(elem, path):
    value = elem.findtext(path)
    return value.strip() if isinstance(value, str) else ""


def text(value, limit=140):
    return re.sub(r"\s+", " ", value or "").strip()[:limit]


def number(value):
    if not value or len(value) > 34:
        return None
    try:
        n = Decimal(value)
    except InvalidOperation:
        return None
    if not n.is_finite() or n < 0 or n > Decimal("1000000000000000"):
        return None
    return str(n)


def transaction_kind(code):
    return {"P": "PURCHASE CODE", "S": "SALE CODE",
            "A": "GRANT / AWARD CODE", "M": "EXERCISE / CONVERSION CODE"}.get(
                code, "OTHER / UNCLASSIFIED CODE")


def parse_form4(xml, url):
    # Reject DTD/entity declarations rather than resolving external entities.
    if re.search(r"<!\s*(DOCTYPE|ENTITY)\b", xml, flags=re.I):
        raise ValueError("invalid-ownership-xml")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        raise ValueError("invalid-ownership-xml") from None
    for element in root.iter():
        if isinstance(element.tag, str):
            element.tag = element.tag.rsplit("}", 1)[-1]
    if root.tag != "ownershipDocument":
        raise ValueError("invalid-ownership-xml")
    owners = []
    for owner in root.findall("./reportingOwner")[:8]:
        name = text(child_text(owner, "./reportingOwnerId/rptOwnerName"), 100)
        if name and name not in owners:
            owners.append(name)
    transactions = []
    all_rows = root.findall("./nonDerivativeTable/nonDerivativeTransaction")
    for row in all_rows[:20]:
        code = text(child_text(row, "./transactionCoding/transactionCode"), 8)
        if not re.fullmatch(r"[A-Z]", code):
            code = "?"
        trade_date = child_text(row, "./transactionDate/value")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", trade_date):
            trade_date = ""
        disposition = child_text(row, "./transactionAmounts/transactionAcquiredDisposedCode/value")
        if disposition not in ("A", "D"):
            disposition = "?"
        shares = number(child_text(row, "./transactionAmounts/transactionShares/value"))
        price = number(child_text(row, "./transactionAmounts/transactionPricePerShare/value"))
        # Estimate a notional amount only for explicit purchase/sale codes.
        notional = None
        if code in ("P", "S") and shares is not None and price is not None:
            notional = str(Decimal(shares) * Decimal(price))
        transactions.append({
            "security": text(child_text(row, "./securityTitle/value"), 85),
            "date": trade_date, "code": code, "kind": transaction_kind(code),
            "acquiredDisposed": disposition,
            "shares": shares, "pricePerShare": price, "estimatedNotional": notional
        })
    if not transactions:
        raise ValueError("no-supported-transactions")
    return {
        "kind": "form4", "owners": owners,
        "transactions": transactions, "totalNonDerivativeRows": len(all_rows),
        "disclaimer": "Only non-derivative rows. Codes classify reported transaction types; amounts are estimates, not investment signals."
    }


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if not self.skip and tag in ("p", "div", "br", "tr", "td", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        if not self.skip and tag in ("p", "div", "tr", "h1", "h2", "h3"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def parse_8k(html, items, url):
    parser = PlainText()
    parser.feed(html)
    plain = re.sub(r"\s+", " ", " ".join(parser.parts))
    matches = list(HEADING.finditer(plain))
    codes = list(items)
    for match in matches:
        code = match.group(1)
        if code not in codes and len(codes) < 12:
            codes.append(code)
    events = []
    for code in codes[:12]:
        match = next((m for m in matches if m.group(1) == code), None)
        excerpt = text(plain[match.end():match.end()+380], 320) if match else ""
        events.append({
            "item": code, "category": GROUPS.get(code, "OTHER REPORTED ITEM"),
            "excerpt": excerpt, "source": "FILING HEADING" if match else "SEC SUBMISSIONS METADATA"
        })
    return {
        "kind": "form8k", "events": events,
        "disclaimer": "Item numbers are filing classifications. Extracted excerpts may include a contents list, not a full event summary."
    }


def inspect(cik, accession, form, doc, codes="", fetcher=fetch_document, agent_loader=load_contact):
    url, item_codes = check_args(cik, accession, form, doc, codes)
    agent = agent_loader()  # No SEC request until contact is verified.
    body = fetcher(url, agent)
    detail = parse_form4(body, url) if form.startswith("4") else parse_8k(body, item_codes, url)
    return {
        "schemaVersion": 1, "source": "sec-edgar-document", "readOnly": True,
        "cik": cik, "accession": accession, "form": form, "documentUrl": url,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        **detail
    }


if __name__ == "__main__":
    try:
        if len(sys.argv) not in (5, 6):
            raise ValueError("invalid-selection")
        result = inspect(*(sys.argv[1:]))
        print("FINANCE_SEC_DETAIL " + json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    except ValueError as error:
        expected = {"invalid-selection", "unsupported-form", "invalid-document", "unsupported-document",
                    "identity-required", "identity-permissions", "identity-invalid", "identity-unreadable",
                    "document-too-large", "sec-document-unavailable", "invalid-ownership-xml",
                    "no-supported-transactions"}
        code = str(error) if str(error) in expected else "document-unavailable"
        print("FINANCE_SEC_DETAIL_ERROR " + code)
        sys.exit(1)
    except Exception:
        print("FINANCE_SEC_DETAIL_ERROR document-unavailable")
        sys.exit(1)
