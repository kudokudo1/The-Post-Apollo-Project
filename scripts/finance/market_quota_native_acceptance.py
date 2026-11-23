#!/usr/bin/env python3
"""M23: operator-guided, read-only native quota status acceptance probe.

This script does not start or reload Quickshell, reserve provider calls,
create/repair any DB, launch a browser, connect to the network, or save logs.
The one subprocess is the existing M21 status CLI with fixed arguments.
"""
import hashlib
import json
import os
import pwd
import stat
import subprocess
import sys
from pathlib import Path

# Run from any checkout. Do not leave import __pycache__ on the live host.
sys.dont_write_bytecode = True
from market_quota_status import (  # noqa: E402
    DB_NAME, MissingLedger, UnavailableLedger, _read_canonical
)

SOURCE = "post-apollo-market-local-quota-status-v1"
SCOPE = "post-apollo-market-local-v1"
PROVIDERS = (("eodhd", 20), ("alpha-vantage", 25))
PREFIX = "FINANCE_QUOTA_STATUS "
EXIT_PASS = 0
EXIT_INCONCLUSIVE = 2
EXIT_ERROR = 3


class ProbeError(Exception):
    pass


def validate_status(raw):
    """Verify exact local-only provenance, state, UTC day and two counters."""
    text = raw.strip()
    if "\n" in text or not text.startswith(PREFIX):
        raise ProbeError("invalid-or-multiple-status-lines")
    try:
        data = json.loads(text[len(PREFIX):])
    except (ValueError, TypeError) as exc:
        raise ProbeError("malformed-status-json") from exc
    if not isinstance(data, dict) or data.get("schemaVersion") != 1 \
            or data.get("source") != SOURCE or data.get("scope") != SCOPE \
            or data.get("readOnly") is not True \
            or data.get("noProviderCalls") is not True \
            or data.get("notAccountBalance") is not True \
            or data.get("ledgerState") not in ("ready", "absent", "unavailable"):
        raise ProbeError("untrusted-status-header")
    day = data.get("utcDay")
    if not isinstance(day, str) or len(day) != 10 \
            or day[4:5] != "-" or day[7:8] != "-":
        raise ProbeError("invalid-status-date")
    import datetime as dt
    try:
        if dt.date.fromisoformat(day).isoformat() != day:
            raise ProbeError("invalid-status-date")
    except ValueError as exc:
        raise ProbeError("invalid-status-date") from exc
    rows = data.get("providers")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ProbeError("missing-status-providers")
    state = data["ledgerState"]
    for index, (provider, limit) in enumerate(PROVIDERS):
        row = rows[index]
        if not isinstance(row, dict) or row.get("provider") != provider \
                or type(row.get("limit")) is not int or row["limit"] != limit:
            raise ProbeError("unexpected-provider-row")
        count = row.get("reserved")
        if state == "ready":
            if type(count) is not int or not (0 <= count <= limit) \
                    or row.get("recordState") != "known":
                raise ProbeError("invalid-local-reservation-count")
        elif count is not None or row.get("recordState") != "unknown":
            raise ProbeError("unknown-cannot-be-zero")
    return data


def run_status_cli():
    """Use the SAME local script that M21 Quickshell would execute.

    This script is the fixed entrypoint in the repository, not a caller path.
    Python -B prevents creation of local compiled-module cache files.
    """
    script = Path(__file__).resolve().with_name("market_quota_status.py")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    try:
        call = subprocess.run(
            [sys.executable, "-B", str(script), "status"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, encoding="utf-8",
            timeout=8, check=False, env=env
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ProbeError("status-cli-unavailable") from exc
    if call.returncode != 0 or len(call.stdout) > 4096 \
            or call.stderr.strip():
        raise ProbeError("status-cli-refused")
    return validate_status(call.stdout)


def trusted_fingerprint():
    """Read only the already-validated M21 file; never create any path.

    Hash covers file bytes. POSIX lstat metadata observes in-place edits or
    file replacement even if byte contents are identical. No atime claim.
    """
    try:
        blob = _read_canonical()
    except MissingLedger:
        return ("absent", None)
    except (UnavailableLedger, OSError):
        return ("unavailable", None)
    if not isinstance(blob, bytes):
        return ("unavailable", None)
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
        if not home or not os.path.isabs(home):
            return ("unavailable", None)
        db = Path(home, ".local", "share", "post-apollo",
                  "finance-market", DB_NAME)
        info = os.stat(db, follow_symlinks=False)
        if info.st_uid != os.getuid() or not stat.S_ISREG(info.st_mode) \
                or info.st_nlink != 1 or info.st_mode & 0o077 \
                or info.st_size != len(blob):
            return ("unavailable", None)
        return ("ready", (
            hashlib.sha256(blob).hexdigest(),
            info.st_dev, info.st_ino, info.st_uid, info.st_mode,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns
        ))
    except OSError:
        return ("unavailable", None)


def capture(cli=run_status_cli, fingerprint=trusted_fingerprint):
    before = fingerprint()
    status = cli()
    after = fingerprint()
    if before != after:
        raise ProbeError("ledger-changed-during-read")
    if before[0] != status["ledgerState"]:
        raise ProbeError("ledger-state-race")
    return {"fingerprint": before, "status": status}


def compare_captures(before, after):
    """Never call an UNKNOWN result evidence of zero or write safety."""
    if before["status"]["utcDay"] != after["status"]["utcDay"]:
        return "inconclusive-utc-day-changed"
    if before["status"]["ledgerState"] == "unavailable" \
            or after["status"]["ledgerState"] == "unavailable":
        return "inconclusive-unavailable-ledger"
    if before["fingerprint"] != after["fingerprint"]:
        return "inconclusive-ledger-changed"
    if before["status"] != after["status"]:
        return "inconclusive-local-status-changed"
    return "unchanged-local-observation"


def summarize(data):
    state = data["ledgerState"]
    if state != "ready":
        return f"UTC {data['utcDay']} // {state.upper()} // both local counts UNKNOWN"
    eod, alpha = data["providers"]
    return (f"UTC {data['utcDay']} // EODHD {eod['reserved']}/20 // "
            f"ALPHA VANTAGE {alpha['reserved']}/25 // LOCAL ONLY")


def run_interactive(prompt=input, output=print, cli=run_status_cli,
                    fingerprint=trusted_fingerprint):
    output("M23 NATIVE QUOTA PROBE // READ-ONLY // NO WRITER // NO PROVIDER CALLS")
    output("This does NOT prove the account's actual API usage.")
    try:
        before = capture(cli, fingerprint)
    except ProbeError as exc:
        output(f"PRECHECK INCONCLUSIVE: {exc}")
        return EXIT_INCONCLUSIVE
    output("BEFORE: " + summarize(before["status"]))
    output("On the running desktop (do not reload/restart Quickshell):")
    output("  Finance → MARKET → STOCKS → QUOTA STATUS")
    output("  Confirm the shown UTC day, provider counts or UNKNOWN match BEFORE.")
    output("  Press REFRESH LOCAL STATUS twice. Confirm values remain consistent.")
    output("  Press BACK TO STOCKS. Confirm the STOCKS view reappears.")
    try:
        observed = prompt(
            "Type PASS if the actual UI did all three; "
            "FAIL if not; SKIP if unavailable: "
        ).strip().upper()
    except (EOFError, KeyboardInterrupt):
        output("OPERATOR UI OBSERVATION: NOT RECORDED")
        return EXIT_INCONCLUSIVE
    if observed not in ("PASS", "FAIL", "SKIP"):
        output("OPERATOR UI OBSERVATION: INVALID / INCONCLUSIVE")
        return EXIT_INCONCLUSIVE
    try:
        after = capture(cli, fingerprint)
    except ProbeError as exc:
        output(f"POSTCHECK INCONCLUSIVE: {exc}")
        return EXIT_INCONCLUSIVE
    outcome = compare_captures(before, after)
    output("AFTER: " + summarize(after["status"]))
    output("FILE OBSERVATION: " + outcome.upper().replace("-", " "))
    output("UI OBSERVATION: OPERATOR-REPORTED " + observed)
    if observed == "FAIL":
        output("RESULT: FAIL / NO AUTOMATIC REPAIR OR RESET")
        return EXIT_ERROR
    if observed != "PASS" or outcome != "unchanged-local-observation":
        output("RESULT: INCONCLUSIVE / DO NOT CLAIM NATIVE ACCEPTANCE")
        return EXIT_INCONCLUSIVE
    output("RESULT: SCOPED OPERATOR-REPORTED UI PASS + UNCHANGED LEDGER")
    output("FINAL PRODUCTION ACCEPTANCE AND M20 SECURITY REVIEW ARE SEPARATE.")
    return EXIT_PASS


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("--preflight", "--interactive"):
        print("USAGE: python3 -B scripts/finance/"
              "market_quota_native_acceptance.py "
              "[--preflight|--interactive]")
        return EXIT_ERROR
    if sys.argv[1] == "--interactive":
        return run_interactive()
    try:
        view = capture()
    except ProbeError as exc:
        print(f"M23 PREFLIGHT INCONCLUSIVE: {exc}")
        return EXIT_INCONCLUSIVE
    print("M23 LOCAL STATUS: " + summarize(view["status"]))
    if view["status"]["ledgerState"] == "unavailable":
        print("M23 PREFLIGHT INCONCLUSIVE: EXISTING LEDGER UNAVAILABLE")
        return EXIT_INCONCLUSIVE
    print("M23 PREFLIGHT PASS: LOCAL CLI RESPONDED WITHOUT OBSERVED LEDGER CHANGE")
    print("NO UI OPERATION WAS TESTED; NATIVE ACCEPTANCE NOT ESTABLISHED")
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
