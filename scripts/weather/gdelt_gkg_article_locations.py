#!/usr/bin/env python3
"""Resolve one selected GDELT DOC article to GKG 2.1 mentioned locations.

The DOC article's seendate determines nearby 15-minute GKG slices. The helper
downloads only those bounded ZIPs, joins by exact/canonical document URL, and
parses V2Locations from that one matching GKG row.

This returns locations *mentioned in the article*. It does not claim that any
mention is the event location, impact area, or publisher location.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
import json
import math
import re
import sys
import zipfile
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "data.gdeltproject.org"
BASE = "https://" + HOST + "/gdeltv2/"
MAX_ZIP_BYTES = 12 * 1024 * 1024
MAX_CSV_BYTES = 96 * 1024 * 1024
MAX_LOCATIONS = 12
TRACKING_KEYS = {
    "fbclid", "gclid", "dclid", "mc_cid", "mc_eid",
}
ENGLISH_LABELS = {"en", "eng", "english"}


class GdeltOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != HOST:
            raise ValueError("Unexpected GDELT redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def short_text(value, limit):
    return " ".join(str(value or "").replace("\x00", " ").split())[:limit]


def safe_article_url(value):
    text = str(value or "").strip()
    if not text or len(text) > 2048:
        return ""
    parts = urlsplit(text)
    if parts.scheme != "https" or not parts.hostname:
        return ""
    host = parts.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        return ""
    if parts.username or parts.password or parts.port:
        return ""
    if re.fullmatch(r"\d+(?:\.\d+){3}", host):
        return ""
    return text


def canonical_url(value):
    safe = safe_article_url(value)
    if not safe:
        return ""
    parts = urlsplit(safe)
    host = parts.hostname.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    kept = []
    for key, val in parse_qsl(parts.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_KEYS:
            continue
        kept.append((key, val))
    kept.sort()
    return urlunsplit((
        parts.scheme.lower(),
        host,
        path,
        urlencode(kept, doseq=True),
        "",
    ))


def parse_seen_time(value):
    raw = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z?", raw)
    if match:
        return datetime(
            int(match.group(1)), int(match.group(2)), int(match.group(3)),
            int(match.group(4)), int(match.group(5)), int(match.group(6)),
            tzinfo=timezone.utc,
        )
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def slice_candidates(seen):
    minute = (seen.minute // 15) * 15
    base = seen.replace(minute=minute, second=0, microsecond=0)
    return [base, base - timedelta(minutes=15), base + timedelta(minutes=15)]


def feed_suffix(language):
    normalized = short_text(language, 32).lower()
    return ".gkg.csv.zip" if normalized in ENGLISH_LABELS else ".translation.gkg.csv.zip"


def slice_url(stamp, language):
    token = stamp.strftime("%Y%m%d%H%M%S")
    return BASE + token + feed_suffix(language)


def finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def location_type_label(value):
    return {
        1: "COUNTRY",
        2: "US STATE",
        3: "US CITY / LANDMARK",
        4: "WORLD CITY / LANDMARK",
        5: "WORLD ADM1",
    }.get(value, "UNKNOWN")


def parse_locations(value):
    groups = {}
    raw = str(value or "")
    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        parts = token.split("#")
        if len(parts) < 9:
            continue
        try:
            kind = int(parts[0])
        except ValueError:
            continue
        name = short_text(parts[1], 160)
        country = short_text(parts[2], 12)
        adm1 = short_text(parts[3], 24)
        adm2 = short_text(parts[4], 32)
        lat = finite(parts[5])
        lon = finite(parts[6])
        feature_id = short_text(parts[7], 48)
        try:
            offset = int(parts[8])
        except ValueError:
            offset = -1

        if (
            kind not in {1, 2, 3, 4, 5}
            or not name
            or lat is None or lon is None
            or not -90 <= lat <= 90
            or not -180 <= lon <= 180
        ):
            continue

        key = feature_id if feature_id else (
            f"{kind}|{name.lower()}|{lat:.5f}|{lon:.5f}"
        )
        if key not in groups:
            groups[key] = {
                "name": name,
                "type": kind,
                "typeLabel": location_type_label(kind),
                "countryCode": country,
                "adm1": adm1,
                "adm2": adm2,
                "latitude": lat,
                "longitude": lon,
                "featureId": feature_id,
                "firstOffset": offset,
                "mentionCount": 0,
            }
        group = groups[key]
        group["mentionCount"] += 1
        if offset >= 0 and (group["firstOffset"] < 0 or offset < group["firstOffset"]):
            group["firstOffset"] = offset

    rows = list(groups.values())
    specificity = {3: 0, 4: 0, 2: 1, 5: 1, 1: 2}
    rows.sort(key=lambda row: (
        specificity.get(row["type"], 3),
        row["firstOffset"] if row["firstOffset"] >= 0 else 10**9,
        -row["mentionCount"],
        row["name"].lower(),
    ))
    return rows[:MAX_LOCATIONS]


def find_article_in_zip(payload, article_url):
    if len(payload) > MAX_ZIP_BYTES:
        raise ValueError("GDELT GKG ZIP too large")
    wanted_exact = safe_article_url(article_url)
    wanted_canonical = canonical_url(article_url)
    if not wanted_exact or not wanted_canonical:
        raise ValueError("Invalid article URL")

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise ValueError("Unexpected GDELT GKG archive")
        info = archive.getinfo(names[0])
        if info.file_size > MAX_CSV_BYTES:
            raise ValueError("GDELT GKG CSV too large")

        with archive.open(info, "r") as raw:
            text = io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
            for line in text:
                cols = line.rstrip("\r\n").split("\t")
                if len(cols) < 11:
                    continue
                document = short_text(cols[4], 2048)
                if not document:
                    continue
                method = ""
                if document == wanted_exact:
                    method = "EXACT URL"
                elif canonical_url(document) == wanted_canonical:
                    method = "CANONICAL URL"
                if not method:
                    continue

                return {
                    "matchMethod": method,
                    "gkgRecordId": short_text(cols[0], 40),
                    "sourceCommonName": short_text(cols[3], 120),
                    "documentIdentifier": document,
                    "locations": parse_locations(cols[10]),
                }
    return None


def fetch_slice(url):
    opener = build_opener(GdeltOnlyRedirects())
    request = Request(
        url,
        headers={
            "User-Agent": "Post-Apollo-WeatherStation/1.3",
            "Accept": "application/zip,application/octet-stream",
        },
    )
    with opener.open(request, timeout=20) as response:
        actual = urlsplit(response.geturl())
        if actual.scheme != "https" or actual.hostname != HOST:
            raise ValueError("Unexpected GDELT response URL")
        payload = response.read(MAX_ZIP_BYTES + 1)
        if len(payload) > MAX_ZIP_BYTES:
            raise ValueError("GDELT GKG ZIP too large")
        return payload


def lookup(article_url, seen_raw, language):
    safe = safe_article_url(article_url)
    seen = parse_seen_time(seen_raw)
    if not safe:
        raise ValueError("Article URL unavailable")
    if seen is None:
        raise ValueError("Article seendate unavailable")

    attempted = []
    for stamp in slice_candidates(seen):
        url = slice_url(stamp, language)
        attempted.append(stamp.strftime("%Y-%m-%d %H:%MZ"))
        try:
            match = find_article_in_zip(fetch_slice(url), safe)
        except (HTTPError, URLError, OSError, zipfile.BadZipFile):
            continue
        if match is None:
            continue
        return {
            "source": "GDELT GKG 2.1",
            "articleUrl": safe,
            "language": short_text(language, 32),
            "feed": "ENGLISH" if feed_suffix(language) == ".gkg.csv.zip"
                    else "TRANSLINGUAL",
            "sliceUtc": stamp.strftime("%Y-%m-%d %H:%MZ"),
            "matchMethod": match["matchMethod"],
            "gkgRecordId": match["gkgRecordId"],
            "sourceCommonName": match["sourceCommonName"],
            "locations": match["locations"],
            "locationCount": len(match["locations"]),
            "attemptedSlices": attempted,
            "semantics": "MENTIONED LOCATIONS, NOT VERIFIED EVENT LOCATIONS",
        }

    return {
        "source": "GDELT GKG 2.1",
        "articleUrl": safe,
        "language": short_text(language, 32),
        "feed": "ENGLISH" if feed_suffix(language) == ".gkg.csv.zip"
                else "TRANSLINGUAL",
        "sliceUtc": "",
        "matchMethod": "NO MATCH",
        "gkgRecordId": "",
        "sourceCommonName": "",
        "locations": [],
        "locationCount": 0,
        "attemptedSlices": attempted,
        "semantics": "ARTICLE NOT FOUND IN NEARBY GKG SLICES",
    }


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 3:
        sys.stdout.write('{"error":"ARTICLE LOCATION INPUT REQUIRED"}')
        return 2
    try:
        result = lookup(args[0], args[1], args[2])
        sys.stdout.write(json.dumps(result, separators=(",", ":")))
        return 0
    except ValueError:
        sys.stdout.write('{"error":"ARTICLE LOCATION INPUT INVALID"}')
        return 2
    except Exception:
        sys.stdout.write('{"error":"GDELT GKG LOCATION LOOKUP FAILED"}')
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
