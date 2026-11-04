"""ANGEL M2 source reference parser and HTTPS transport tests.

Fully offline: fake opener/response never contacts external publishers.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / "services/time/AngelSourceLookup.py"
spec = importlib.util.spec_from_file_location("angel_source_lookup", MODULE)
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)


def fixture(digits):
    return (
        "<html><body><h1>" + digits + " Angel Number meaning</h1>"
        "<h3>Numerology Meaning of Angel Number " + digits + "</h3>"
        "<p>Traditionally this sequence is connected with themes of "
        "balance, direction, and private reflection in numerological "
        "interpretations, as described by the publisher.</p>"
        "<h3>Meaning of Seeing Angel Number " + digits + "</h3>"
        "<p>The next paragraph should never be returned in the first lens.</p>"
        "</body></html>"
    )


class FakeHeaders:
    def get_content_type(self):
        return "text/html"

    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    def __init__(self, text, url):
        self.text = text.encode("utf-8")
        self.url = url
        self.headers = FakeHeaders()

    def geturl(self):
        return self.url

    def read(self, n):
        return self.text[:n]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SourcePolicyTests(unittest.TestCase):
    def test_exact_publisher_and_number_path(self):
        for digits in ("101", "202", "222", "347", "0000", "0"):
            self.assertTrue(source.valid_digits(digits))
            self.assertEqual(source.source_url(digits),
                             source.ROOT + digits + "-meaning")
        for bad in ("", "12+3", "222222", "2:22", "٢٢٢", "../347",
                    "347\n", "347?test", " "):
            self.assertFalse(source.valid_digits(bad))
            self.assertEqual(source.source_url(bad), "")

    def test_verified_heading_and_only_first_20_words(self):
        result = source.extract_reference(fixture("347"), "347")
        self.assertIsNotNone(result)
        self.assertLessEqual(len(result.split()), source.WORD_LIMIT)
        self.assertNotIn("next paragraph", result)
        self.assertIsNone(source.extract_reference(fixture("101"), "222"))
        self.assertIsNone(source.extract_reference(
            "<h1>347 Angel Number meaning</h1><p>generic</p>", "347"))
        self.assertIsNone(source.extract_reference(
            "<h1>347 Angel Number meaning</h1>"
            "<h3>Meaning of Seeing Angel Number 347</h3>"
            "<p>wrong section should not be displayed as numerology</p>", "347"))

    def test_opt_in_fetch_response_retains_provenance(self):
        digits = "202"
        expected = source.source_url(digits)
        opener = Mock()
        opener.open.return_value = FakeResponse(fixture(digits), expected)
        result = source.lookup(digits, opener=opener)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["digits"], digits)
        self.assertEqual(result["provider"], "Astrology.com")
        self.assertEqual(result["section"], "Numerology meaning")
        self.assertEqual(result["url"], expected)
        self.assertTrue(result["excerpt"])
        opener.open.assert_called_once()
        self.assertEqual(opener.open.call_args.kwargs["timeout"], source.TIMEOUT)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, expected)
        self.assertEqual(request.get_method(), "GET")

    def test_bad_redirect_and_missing_page_do_not_create_meaning(self):
        for url in ("http://www.astrology.com/numerology/angel-numbers/347-meaning",
                    "https://evil.example/numerology/angel-numbers/347-meaning",
                    "https://www.astrology.com/numerology/angel-numbers/222-meaning",
                    "https://www.astrology.com/"):
            opener = Mock()
            opener.open.return_value = FakeResponse(fixture("347"), url)
            self.assertNotEqual(source.lookup("347", opener=opener)["status"],
                                "ready")
        opener = Mock()
        opener.open.side_effect = urllib.error.HTTPError(
            source.source_url("347"), 404, "Not Found", {}, None)
        self.assertEqual(source.lookup("347", opener=opener)["status"],
                         "SOURCE_UNAVAILABLE")

    def test_invalid_number_cannot_issue_request(self):
        opener = Mock()
        result = source.lookup("10101010", opener=opener)
        self.assertEqual(result["status"], "UNSUPPORTED_DIGITS")
        opener.open.assert_not_called()

    def test_redirect_handler_blocks_non_publisher(self):
        handler = source.SamePublisherRedirect()
        req = Mock()
        args = (req, None, 302, "redirect", {})
        for unsafe in ("https://evil.example", "http://www.astrology.com/",
                       "https://www.astrology.com:8443/path"):
            with self.assertRaises(urllib.error.URLError):
                handler.redirect_request(*args, unsafe)


if __name__ == "__main__":
    unittest.main()
