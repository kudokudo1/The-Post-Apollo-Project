#!/usr/bin/env python3
"""M23 disposable tests for the no-write native acceptance observer.

Does NOT run the real provider, DB, process, Quickshell or user prompts.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "finance" / "market_quota_native_acceptance.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("market_quota_native_acceptance", SCRIPT)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

DAY = "2026-11-23"


def status(state="ready", eod=3, alpha=9, day=DAY):
    known = state == "ready"
    return {
        "schemaVersion": 1,
        "source": probe.SOURCE,
        "scope": probe.SCOPE,
        "readOnly": True,
        "noProviderCalls": True,
        "notAccountBalance": True,
        "utcDay": day,
        "ledgerState": state,
        "providers": [
            {"provider": name, "limit": lim,
             "reserved": n if known else None,
             "recordState": "known" if known else "unknown"}
            for (name, lim), n in zip(probe.PROVIDERS, (eod, alpha))
        ],
    }


def encoded(value):
    return probe.PREFIX + json.dumps(value, separators=(",", ":")) + "\n"


def reject(raw):
    try:
        probe.validate_status(raw)
    except probe.ProbeError:
        return
    raise AssertionError(f"Accepted an invalid status: {raw[:100]}")


assert probe.validate_status(encoded(status())) == status()
assert probe.validate_status(encoded(status("absent"))) == status("absent")
assert probe.validate_status(encoded(status("unavailable"))) == status("unavailable")
for bad in (
    encoded(status()) + "EXTRA\n",
    "FINANCE_QUOTA_STATUS_ERROR status-unavailable\n",
    "FINANCE_QUOTA_STATUS not-json\n",
    encoded({**status(), "noProviderCalls": False}),
    encoded({**status(), "notAccountBalance": False}),
    encoded({**status(), "source": "unknown"}),
    encoded({**status(), "scope": "account-global"}),
    encoded({**status(), "utcDay": "2026-02-30"}),
    encoded({**status(), "providers": []}),
    encoded({**status(), "providers": status()["providers"][::-1]}),
    encoded(status(eod=21)),
    encoded(status(alpha=-1)),
    encoded({**status("absent"),
             "providers": status()["providers"]}),
):
    reject(bad)

unchanged = ("ready", ("a" * 64, 1, 2, 3, 0o100600, 4096, 10, 11))
replaced = ("ready", ("b" * 64, 1, 3, 3, 0o100600, 4096, 12, 13))
absent = ("absent", None)
unsafe = ("unavailable", None)


def view(fp=unchanged, s=None):
    return {"fingerprint": fp, "status": status() if s is None else s}


assert probe.compare_captures(view(), view()) == "unchanged-local-observation"
assert probe.compare_captures(
    view(fp=absent, s=status("absent")),
    view(fp=absent, s=status("absent"))
) == "unchanged-local-observation"
assert probe.compare_captures(view(), view(fp=replaced)) == "inconclusive-ledger-changed"
assert probe.compare_captures(
    view(), view(s=status(eod=4))
) == "inconclusive-local-status-changed"
assert probe.compare_captures(
    view(), view(s=status(day="2026-11-24"))
) == "inconclusive-utc-day-changed"
assert probe.compare_captures(
    view(), view(fp=unsafe, s=status("unavailable"))
) == "inconclusive-unavailable-ledger"


def fake_capture(fp, s):
    return probe.capture(lambda: s, lambda: fp)


assert fake_capture(unchanged, status()) == view()
assert fake_capture(absent, status("absent")) == view(
    fp=absent, s=status("absent")
)


def expect_capture_error(fps, value, expected):
    iterator = iter(fps)
    try:
        probe.capture(lambda: value, lambda: next(iterator))
    except probe.ProbeError as exc:
        assert str(exc) == expected, (str(exc), expected)
    else:
        raise AssertionError("Capture unexpectedly succeeded")


expect_capture_error([unchanged, replaced], status(),
                     "ledger-changed-during-read")
expect_capture_error([absent, absent], status(),
                     "ledger-state-race")

# The only CLI subprocess is a fixed, bounded interpreter invocation.
calls = []
def fake_run(argv, **kwargs):
    calls.append((argv, kwargs))
    return SimpleNamespace(returncode=0, stdout=encoded(status()), stderr="")
with patch.object(probe.subprocess, "run", side_effect=fake_run):
    assert probe.run_status_cli() == status()
assert len(calls) == 1
args, opts = calls[0]
assert args[0] == sys.executable
assert args[1] == "-B"
assert args[2].endswith("/market_quota_status.py")
assert args[3] == "status"
assert len(args) == 4
assert opts["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
assert opts["timeout"] == 8
assert opts["stdin"] == subprocess.DEVNULL
with patch.object(probe.subprocess, "run",
                  return_value=SimpleNamespace(
                      returncode=4, stdout="", stderr="failed")):
    try:
        probe.run_status_cli()
    except probe.ProbeError as exc:
        assert str(exc) == "status-cli-refused"
    else:
        raise AssertionError("Nonzero subprocess result was allowed")

# Operator observations are labeled as observations, never autonomous Qt proof.
def interactive(choice, before_fp=unchanged, after_fp=unchanged,
                before_status=None, after_status=None):
    outputs = []
    fingerprints = iter([
        before_fp, before_fp, after_fp, after_fp
    ])
    statuses = iter([
        status() if before_status is None else before_status,
        status() if after_status is None else after_status
    ])
    result = probe.run_interactive(
        prompt=lambda _: choice,
        output=outputs.append,
        cli=lambda: next(statuses),
        fingerprint=lambda: next(fingerprints)
    )
    return result, outputs


code, output = interactive("PASS")
assert code == probe.EXIT_PASS
assert any("OPERATOR-REPORTED PASS" in x for x in output)
assert any("UNCHANGED LEDGER" in x for x in output)
assert not any("PRODUCTION ACCEPTANCE" in x and "COMPLETE" in x
               for x in output)
code, output = interactive("FAIL")
assert code == probe.EXIT_ERROR
assert any("RESULT: FAIL" in x for x in output)
code, output = interactive("SKIP")
assert code == probe.EXIT_INCONCLUSIVE
assert any("DO NOT CLAIM NATIVE ACCEPTANCE" in x for x in output)
code, output = interactive("PASS", after_fp=replaced)
assert code == probe.EXIT_INCONCLUSIVE
assert any("INCONCLUSIVE LEDGER CHANGED" in x for x in output)
code, output = interactive("PASS", before_fp=unsafe, after_fp=unsafe,
                           before_status=status("unavailable"),
                           after_status=status("unavailable"))
assert code == probe.EXIT_INCONCLUSIVE
code, output = interactive("PASS", before_fp=absent, after_fp=absent,
                           before_status=status("absent"),
                           after_status=status("absent"))
assert code == probe.EXIT_PASS

with tempfile.TemporaryDirectory(prefix="finance-m23-nonwrite-") as directory:
    # A fake home remains empty after mocked probe paths.
    fake_home = Path(directory)
    assert list(fake_home.iterdir()) == []

# Security-negative source inventory: this tool must not add writer/network
# privileges, persist a checkpoint, or erase quota on a failed validation.
source = SCRIPT.read_text(encoding="utf-8")
for forbidden in (
    "os.mkdir(", "os.makedirs(", ".unlink(", ".write_text(",
    ".write_bytes(", "chmod(", "sqlite3.connect(",
    "market_shared_quota.reserve(", "urlopen(", "requests.get(",
    "https://eodhd.com", "https://www.alphavantage.co",
    "check_call(", "os.system(", "shell=True",
    "quickshell --", "quickshell -c",
):
    assert forbidden not in source, forbidden
assert "sys.dont_write_bytecode = True" in source
assert '["--preflight", "--interactive"]' not in source  # fixed finite modes
assert "trusted_fingerprint" in source
assert "run_status_cli" in source
assert "notAccountBalance" in source

print("Finance M23 read-only native acceptance probe, strict false-zero refusals, "
      "fixed CLI and operator observations: PASS")
