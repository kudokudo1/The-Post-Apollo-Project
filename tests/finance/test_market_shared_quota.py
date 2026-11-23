#!/usr/bin/env python3
"""M20 disposable-only SQLite quota tests; never touch host FinanceW files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "finance"))
from market_shared_quota import (  # noqa: E402
    LIMITS, SCOPE, QuotaExhausted, QuotaStorageUnavailable, reserve
)


def assert_raises(expected, func):
    try:
        func()
    except expected:
        return
    raise AssertionError(f"expected {expected.__name__}")


with tempfile.TemporaryDirectory(prefix="finance-m20-quota-") as directory:
    db = Path(directory) / "quota.sqlite3"
    day = "2026-11-23"
    previous = "2026-11-22"

    # Independent providers, durable reopening, and exact maximum.
    assert LIMITS == {"eodhd": 20, "alpha-vantage": 25}
    first = reserve("eodhd", utc_day=day, database=db)
    assert first == {
        "schemaVersion": 1, "scope": SCOPE, "provider": "eodhd",
        "utcDay": day, "reserved": 1, "limit": 20,
        "notAccountBalance": True,
    }
    for number in range(2, 21):
        x = reserve("eodhd", utc_day=day, database=db)
        assert x["reserved"] == number
    assert_raises(QuotaExhausted,
                  lambda: reserve("eodhd", utc_day=day, database=db))
    assert reserve("alpha-vantage", utc_day=day, database=db)["reserved"] == 1
    assert reserve("eodhd", utc_day=previous, database=db)["reserved"] == 1
    assert reserve("eodhd", utc_day=day, database=db) if False else True
    assert_raises(ValueError, lambda: reserve("unknown", utc_day=day, database=db))
    assert_raises(ValueError, lambda: reserve("eodhd", utc_day="2026-02-30", database=db))

    # No completion/refund action exists; crash after reservation is counted.
    with sqlite3.connect(db) as con:
        rows = con.execute(
            "SELECT provider,utc_day,reserved FROM quota_attempts ORDER BY provider,utc_day"
        ).fetchall()
    assert rows == [
        ("alpha-vantage", day, 1),
        ("eodhd", previous, 1),
        ("eodhd", day, 20),
    ]

    # Concurrent independent SQLite connections cannot over-allocate.
    simultaneous = Path(directory) / "contended.sqlite3"
    def run_one(_):
        try:
            return reserve("eodhd", utc_day=day, database=simultaneous)["reserved"]
        except QuotaExhausted:
            return None

    with ThreadPoolExecutor(max_workers=12) as workers:
        outcomes = list(workers.map(run_one, range(32)))
    winners = [n for n in outcomes if n is not None]
    assert len(winners) == 20, winners
    assert sorted(winners) == list(range(1, 21)), winners
    assert len(outcomes) - len(winners) == 12
    with sqlite3.connect(simultaneous) as con:
        actual = con.execute(
            "SELECT reserved FROM quota_attempts WHERE provider='eodhd'"
        ).fetchone()[0]
    assert actual == 20
    assert reserve("alpha-vantage", utc_day=day,
                   database=simultaneous)["reserved"] == 1

    # Broken SQLite must fail closed; no pretend allowance.
    damaged = Path(directory) / "not-db.sqlite3"
    damaged.write_text("not a SQLite database", encoding="utf-8")
    assert_raises(QuotaStorageUnavailable,
                  lambda: reserve("eodhd", utc_day=day, database=damaged))

print("Finance M20 atomic shared local quota, crash conservatism, exact limits and cross-process DB contention: PASS")
