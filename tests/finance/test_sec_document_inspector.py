#!/usr/bin/env python3
"""Offline, fictional SEC documents; never hit the network or read operator files."""
from pathlib import Path
import importlib.util

root = Path(__file__).resolve().parents[2]
path = root / "scripts/finance/inspect_sec_document.py"
spec = importlib.util.spec_from_file_location("sec_document_detail", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

XML = """<?xml version="1.0"?>
<ownershipDocument>
<reportingOwner><reportingOwnerId><rptOwnerName>Fictional Officer</rptOwnerName>
</reportingOwnerId></reportingOwner>
<nonDerivativeTable>
 <nonDerivativeTransaction>
  <securityTitle><value>Imaginary Common Stock</value></securityTitle>
  <transactionDate><value>2026-10-21</value></transactionDate>
  <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
  <transactionAmounts><transactionShares><value>100</value></transactionShares>
  <transactionPricePerShare><value>12.50</value></transactionPricePerShare>
  <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
  </transactionAmounts>
 </nonDerivativeTransaction>
 <nonDerivativeTransaction>
  <transactionCoding><transactionCode>M</transactionCode></transactionCoding>
  <transactionAmounts><transactionShares><value>50</value></transactionShares>
  <transactionPricePerShare><value>0</value></transactionPricePerShare>
  <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode></transactionAmounts>
 </nonDerivativeTransaction>
</nonDerivativeTable>
<derivativeTable><derivativeTransaction>
 <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
</derivativeTransaction></derivativeTable>
</ownershipDocument>"""

def fails(fn, code):
    try:
        fn()
    except ValueError as error:
        assert str(error) == code, (error, code)
    else:
        raise AssertionError("expected " + code)

url, items = module.check_args("0000320193", "0000320193-26-000013",
                               "4", "xslF345X05/primarydocument.xml")
assert url == ("https://www.sec.gov/Archives/edgar/data/320193/"
               "000032019326000013/primarydocument.xml")
assert items == []
fails(lambda: module.check_args("0000320193", "0000320193-26-000013", "4", "../../outside.xml"),
      "invalid-document")
fails(lambda: module.check_args("0000320193", "0000320193-26-000013", "4", "form4.htm"),
      "unsupported-document")
fails(lambda: module.check_args("0000320193", "0000320193-26-000013", "10-Q", "q.html"),
      "unsupported-form")
fails(lambda: module.check_args("9999999999", "0000320193-26-000013", "4", "form4.xml"),
      "invalid-selection")
fails(lambda: module.parse_form4("<!DOCTYPE foo><ownershipDocument/>", url),
      "invalid-ownership-xml")
fails(lambda: module.parse_form4("<html>Wrong file</html>", url),
      "invalid-ownership-xml")

out = module.parse_form4(XML, url)
assert out["kind"] == "form4"
assert out["owners"] == ["Fictional Officer"]
assert len(out["transactions"]) == 2
assert out["totalNonDerivativeRows"] == 2
assert out["transactions"][0]["kind"] == "PURCHASE CODE"
assert out["transactions"][0]["shares"] == "100"
assert out["transactions"][0]["pricePerShare"] == "12.50"
assert out["transactions"][0]["estimatedNotional"] == "1250.00"
assert out["transactions"][1]["kind"] == "EXERCISE / CONVERSION CODE"
assert out["transactions"][1]["estimatedNotional"] is None
assert module.number("NaN") is None
assert module.number("-100") is None

HTML = """
<html><head><script>Item 3.01 script injection</script></head><body>
<h2>Item 5.02 Departure of Directors</h2>
<p>A fictional executive left on an invented date.</p>
<h2>Item 9.01 Exhibits</h2>
<p>Fictional exhibit filed.</p>
</body></html>
"""
eight = module.parse_8k(HTML, ["5.02", "7.01"], url)
assert eight["kind"] == "form8k"
assert [e["item"] for e in eight["events"]] == ["5.02","7.01","9.01"]
assert eight["events"][0]["source"] == "FILING HEADING"
assert "fictional executive" in eight["events"][0]["excerpt"].lower()
assert eight["events"][1]["source"] == "SEC SUBMISSIONS METADATA"
assert "3.01" not in [e["item"] for e in eight["events"]]

calls = []
def fake_fetch(filing_url, agent):
    calls.append((filing_url, agent))
    return XML

fails(lambda: module.inspect("0000320193", "0000320193-26-000013", "4",
                             "primarydocument.xml", fetcher=fake_fetch,
                             agent_loader=lambda: (_ for _ in ()).throw(
                                 ValueError("identity-required"))),
      "identity-required")
assert not calls, "contact required before SEC fetch"

result = module.inspect("0000320193", "0000320193-26-000013", "4",
                        "xslF345X05/primarydocument.xml",
                        fetcher=fake_fetch, agent_loader=lambda: "Unit Test analyst@testing.invalid")
assert result["source"] == "sec-edgar-document"
assert result["readOnly"] is True
assert result["kind"] == "form4"
assert result["accession"] == "0000320193-26-000013"
assert len(calls) == 1
assert calls[0][0].endswith("/primarydocument.xml")
assert calls[0][1] == "Unit Test analyst@testing.invalid"

result8 = module.inspect("0000320193", "0000320193-26-000014", "8-K",
                         "report.htm", "5.02",
                         fetcher=lambda u, a: HTML,
                         agent_loader=lambda: "Unit Test analyst@testing.invalid")
assert result8["kind"] == "form8k"
assert result8["events"][0]["item"] == "5.02"

print("Finance SEC M3 fictional XML/HTML document inspector: PASS")
