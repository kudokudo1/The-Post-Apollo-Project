#!/usr/bin/env python3
"""Fetch upcoming solar and lunar eclipse dates from NASA GSFC annual pages.

NASA's annual OH pages provide a stable year-indexed list of eclipse dates and
types. This helper reads the current UTC year plus the next two years, extracts
only explicit "YYYY Mon DD: <type> Solar/Lunar Eclipse" records, deduplicates
them, and emits upcoming calendar events.

This slice intentionally does not infer local visibility or exact maximum time.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "eclipse.gsfc.nasa.gov"
BASE = "https://" + HOST + "/OH/OH{year}.html"
MAX_BYTES = 2 * 1024 * 1024
YEARS_AHEAD = 2
MAX_EVENTS = 10

MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

EVENT_RE = re.compile(
    r"\b(?P<year>\d{4})\s+"
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d{1,2})\s*:\s*"
    r"(?P<phase>Annular|Total|Partial|Penumbral|Hybrid)\s+"
    r"(?P<body>Solar|Lunar)\s+Eclipse\b",
    flags=re.IGNORECASE,
)


class NasaOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected NASA eclipse redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class VisibleText(HTMLParser):
    BREAKS = {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "table"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.BREAKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(str(data))

    def text(self) -> str:
        return "".join(self.parts)


def page_url(year: int) -> str:
    value = int(year)
    if value < 2000 or value > 2100:
        raise ValueError("Unsupported NASA eclipse year")
    return BASE.format(year=value)


def normalize_phase(value: str) -> str:
    text = str(value or "").strip().upper()
    allowed = {"ANNULAR", "TOTAL", "PARTIAL", "PENUMBRAL", "HYBRID"}
    return text if text in allowed else ""


def normalize_body(value: str) -> str:
    text = str(value or "").strip().upper()
    return text if text in {"SOLAR", "LUNAR"} else ""


def parse_page(raw_html: bytes, expected_year: int):
    parser = VisibleText()
    parser.feed(raw_html.decode("utf-8", "replace"))
    text = re.sub(r"\s+", " ", parser.text())

    rows = []
    seen = set()
    for match in EVENT_RE.finditer(text):
        year = int(match.group("year"))
        if year != int(expected_year):
            continue
        month_name = match.group("month").title()
        month = MONTHS.get(month_name)
        day = int(match.group("day"))
        phase = normalize_phase(match.group("phase"))
        body = normalize_body(match.group("body"))
        if not month or not phase or not body:
            continue

        try:
            event_date = date(year, month, day)
        except ValueError:
            continue

        key = f"{event_date.isoformat()}|{body}|{phase}"
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "key": key,
            "date": event_date.isoformat(),
            "year": year,
            "month": month,
            "day": day,
            "body": body,
            "phase": phase,
            "event": f"{phase} {body} ECLIPSE",
            "sourceYear": year,
            "sourcePage": page_url(year),
        })

    rows.sort(key=lambda row: (row["date"], row["body"], row["phase"]))
    return rows


def fetch_year(opener, year: int):
    url = page_url(year)
    request = Request(
        url,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/1.1",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with opener.open(request, timeout=15) as response:
        actual = urlsplit(response.geturl())
        if (
            actual.scheme != "https"
            or actual.hostname != HOST
            or actual.path != f"/OH/OH{int(year)}.html"
        ):
            raise ValueError("Unexpected NASA eclipse response URL")
        payload = response.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError("NASA eclipse page too large")
        return parse_page(payload, year)


def summarize(pages, now: datetime):
    current_date = now.astimezone(timezone.utc).date()
    rows = []
    seen = set()

    for page_rows in pages:
        for row in page_rows:
            if row["key"] in seen:
                continue
            seen.add(row["key"])
            event_date = date.fromisoformat(row["date"])
            enriched = dict(row)
            enriched["daysUntil"] = (event_date - current_date).days
            if enriched["daysUntil"] < 0:
                continue
            rows.append(enriched)

    rows.sort(key=lambda row: (
        row["daysUntil"],
        0 if row["body"] == "SOLAR" else 1,
        row["date"],
    ))

    solar = [row for row in rows if row["body"] == "SOLAR"]
    lunar = [row for row in rows if row["body"] == "LUNAR"]

    return {
        "source": "NASA GSFC ECLIPSE WEB SITE",
        "generatedUtc": now.astimezone(timezone.utc)
            .isoformat().replace("+00:00", "Z"),
        "events": rows[:MAX_EVENTS],
        "nextSolar": solar[0] if solar else None,
        "nextLunar": lunar[0] if lunar else None,
        "eventCount": len(rows),
        "dateScope": "GLOBAL UTC CALENDAR DATE",
        "localVisibility": False,
        "exactMaximumTime": False,
    }


def main() -> int:
    now = datetime.now(timezone.utc)
    opener = build_opener(NasaOnlyRedirects())
    pages = []

    try:
        for year in range(now.year, now.year + YEARS_AHEAD + 1):
            pages.append(fetch_year(opener, year))
        result = summarize(pages, now)
        if not result["events"]:
            raise ValueError("No upcoming NASA eclipse events")
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except (HTTPError, URLError, OSError, ValueError):
        sys.stdout.write('{"error":"NASA ECLIPSE CALENDAR UNAVAILABLE"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
