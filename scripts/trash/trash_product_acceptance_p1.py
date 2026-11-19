#!/usr/bin/env python3
"""P1: disposable Trash++ product acceptance, strictly GitHub Actions ONLY.

Real GIO single Burn and Burn All use a new private HOME, XDG dirs, GVfs and
D-Bus session. Managed-copy and V2 Archive operations use only fabricated
research-source files in that same private root. Never run on a workstation.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import sys
import tempfile

# -I omits the script parent; load only this checked-out application tree.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.trash import gio_disposable_roundtrip_u9 as u9

SCHEMA = "post-apollo.trashpp.disposable-product-acceptance.p1"
PREFIX = "trashpp-product-p1-"
ROOT = Path(__file__).resolve().parents[2]
GIO_BACKEND = ROOT / "scripts/trash/trash_cli.py"
MANAGED_BACKEND = ROOT / "scripts/trash/research_records.py"
COMBINED_BACKEND = ROOT / "scripts/trash/trash_all_cli.py"
V2_CAPTURE = ROOT / "scripts/trash/archive_v2_capture_cli.py"
V2_INDEX = ROOT / "scripts/trash/archive_v2_index.py"


class AcceptanceError(Exception):
    """Only fixed error codes reach the public CI result."""


def need(condition, reason):
    if not condition:
        raise AcceptanceError(reason)


def backend(script: Path, args: list[str], env: dict, phase: str,
            expected=True) -> dict:
    process = u9.command([sys.executable, "-I", "-B", str(script), *args], env)
    return u9.json_response(process, expected, phase)


def refusal(script: Path, args: list[str], env: dict, code: str, phase: str):
    result = backend(script, args, env, phase, expected=False)
    need(result.get("error") == code, "UNEXPECTED_REFUSAL_" + phase)


def checked_index(env: dict, phase: str, count: int) -> dict:
    result = backend(GIO_BACKEND, ["index"], env, phase)
    need(result.get("complete") is True and result.get("total") == count
         and len(result.get("items", [])) == count,
         "GIO_INDEX_NOT_EXACT_" + phase)
    return result


def run_gio(root: Path, env: dict) -> None:
    """Never operate unless we started with an empty private GIO Trash."""
    gio = shutil.which("gio", path=env.get("PATH"))
    need(gio is not None, "GIO_MISSING")
    u9.assert_empty_index(checked_index(env, "INITIAL", 0))
    home = root / "home"

    one = home / "P1-single-burn-disposable.txt"
    one.write_bytes(b"P1_SINGLE_BURN:" + secrets.token_bytes(32))
    need(u9.command([gio, "trash", str(one)], env).returncode == 0,
         "SINGLE_TRASH_FAILED")
    row = u9.reviewed_item(checked_index(env, "SINGLE_INDEX", 1), one)

    refusal(GIO_BACKEND, ["burn", row["uri"], str(one), "NO"],
            env, "BURN_CONFIRMATION_REQUIRED", "SINGLE_UNCONFIRMED")
    need(checked_index(env, "AFTER_REFUSAL", 1)["items"][0]["uri"] == row["uri"],
         "UNCONFIRMED_BURN_CHANGED_BIN")

    burned = backend(GIO_BACKEND,
                     ["burn", row["uri"], str(one), "BURN_CONFIRMED"],
                     env, "SINGLE_CONFIRMED")
    need(burned.get("kind") == "burn" and burned.get("verified") is True
         and [x.get("original") for x in burned.get("burnedItems", [])]
         == [str(one)], "SINGLE_BURN_NOT_VERIFIED")
    need(not one.exists() and not one.is_symlink(), "SINGLE_SOURCE_REAPPEARED")
    u9.assert_empty_index(checked_index(env, "AFTER_SINGLE", 0))

    originals = [home / ("P1-bulk-" + str(i) + ".txt") for i in range(2)]
    for original in originals:
        original.write_bytes(b"P1_BULK_BURN:" + secrets.token_bytes(32))
        need(u9.command([gio, "trash", str(original)], env).returncode == 0,
             "BULK_TRASH_FAILED")
    before = checked_index(env, "BULK_INDEX", 2)
    need({x["original"] for x in before["items"]} ==
         {str(x) for x in originals}, "BULK_SELECTED_OTHER_FILE")
    revision = before["revision"]
    refusal(GIO_BACKEND, ["burn-all", revision, "2", "NO"],
            env, "BURN_ALL_CONFIRMATION_REQUIRED", "BULK_UNCONFIRMED")
    refusal(GIO_BACKEND, ["burn-all", "0" * 64, "2", "BURN_ALL_CONFIRMED"],
            env, "TRASH_CHANGED_REFRESH_REQUIRED", "BULK_STALE")
    need(checked_index(env, "AFTER_BULK_REFUSALS", 2)["revision"] == revision,
         "BULK_REFUSAL_CHANGED_BIN")

    receipt = backend(GIO_BACKEND,
                      ["burn-all", revision, "2", "BURN_ALL_CONFIRMED"],
                      env, "BULK_CONFIRMED")
    need(receipt.get("verified") is True and receipt.get("partial") is False
         and receipt.get("count") == 2 and receipt.get("burnedCount") == 2
         and receipt.get("remainingCount") == 0
         and {x.get("original") for x in receipt.get("burnedItems", [])}
         == {str(x) for x in originals}, "BULK_BURN_NOT_VERIFIED")
    need(all(not p.exists() and not p.is_symlink() for p in originals),
         "BULK_SOURCE_REAPPEARED")
    u9.assert_empty_index(checked_index(env, "AFTER_BULK", 0))


def run_managed_archive(root: Path, env: dict) -> None:
    """Prove managed Burn never affects original source or V2 read-only copy."""
    home = root / "home"
    data = home / ".local" / "share" / "quickshell"
    data.mkdir(parents=True, mode=0o700, exist_ok=True)
    crawl = home / ".local/share/post-apollo/finance-crawler/crawl-records.json"
    crawl.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    timestamp = "2026-10-12T10:30:00Z"
    pages = [
        {"schemaVersion": 1, "source": "finance-demo-scrapy",
         "readOnly": True,
         "url": "https://quotes.toscrape.com/page/" + str(i) + "/",
         "title": "Disposable demo " + str(i), "observedAt": timestamp,
         "links": ["https://quotes.toscrape.com/author/Test"],
         "snippets": ["CI-only source, not personal data"]}
        for i in (1, 2)
    ]
    crawl.write_text(json.dumps(pages), encoding="utf-8")
    source_digest = hashlib.sha256(crawl.read_bytes()).hexdigest()
    data_arg = str(data)

    # V2 snapshot preview must not create storage or expose payload.
    preview = backend(V2_CAPTURE,
                      ["preview", data_arg, "demo", pages[0]["url"], timestamp],
                      env, "V2_PREVIEW")
    need(preview.get("readOnly") is True and
         preview.get("preview", {}).get("ownerId") == "demo-scrape",
         "V2_PREVIEW_UNEXPECTED")
    witness = preview["preview"]["sourceRevision"]
    refusal(V2_CAPTURE,
            ["capture", data_arg, "demo", pages[0]["url"], timestamp, "0" * 64],
            env, "STALE_SOURCE_REFRESH_REQUIRED", "V2_STALE")
    captured = backend(V2_CAPTURE,
                       ["capture", data_arg, "demo", pages[0]["url"],
                        timestamp, witness], env, "V2_CAPTURE")
    need(captured.get("copyOnly") is True and
         captured.get("receipt", {}).get("ownerId") == "demo-scrape",
         "V2_CAPTURE_UNEXPECTED")
    before = backend(V2_INDEX, ["index", data_arg], env, "V2_INDEX")
    need(before.get("total") == 1 and len(before.get("items", [])) == 1,
         "V2_INDEX_NOT_ONE")

    def managed(action, *args):
        return backend(MANAGED_BACKEND, [action, data_arg, *map(str, args)],
                       env, "MANAGED_" + action.upper().replace("-", "_"))

    summary = managed("list")
    need(summary.get("total") == 0 and summary.get("revision") == 0,
         "MANAGED_NOT_EMPTY")
    saved = managed("archive", pages[0]["url"], timestamp, summary["revision"])
    row = saved["items"][0]
    need(row["state"] == "archived", "COPY_NOT_CREATED")
    trashed = managed("trash", row["id"], saved["revision"])
    need(trashed["items"][0]["state"] == "trashed", "COPY_NOT_TRASHED")
    restored = managed("restore", row["id"], trashed["revision"])
    need(restored["items"][0]["state"] == "archived", "COPY_NOT_RESTORED")
    trashed = managed("trash", row["id"], restored["revision"])
    refusal(MANAGED_BACKEND,
            ["burn", data_arg, row["id"], str(trashed["revision"]), "NO"],
            env, "BURN_CONFIRMATION_REQUIRED", "MANAGED_UNCONFIRMED")
    burned = managed("burn", row["id"], trashed["revision"],
                     "BURN_SAVED_COPY_CONFIRMED")
    need(burned.get("verified") is True and burned.get("burnedCount") == 1
         and burned.get("total") == 0, "MANAGED_SINGLE_BURN_UNVERIFIED")

    for page in pages:
        previous = managed("list")
        saved = managed("archive", page["url"], timestamp, previous["revision"])
    for row in list(saved["items"]):
        previous = managed("list")
        managed("trash", row["id"], previous["revision"])
    pending = managed("list")
    need(pending.get("binCount") == 2 and
         len(pending.get("binDigest", "")) == 64, "MANAGED_BIN_NOT_TWO")
    refusal(MANAGED_BACKEND,
            ["burn-all", data_arg, str(pending["revision"]),
             "2", pending["binDigest"], "NO"], env,
            "BURN_ALL_CONFIRMATION_REQUIRED", "MANAGED_BULK_UNCONFIRMED")
    done = managed("burn-all", pending["revision"], pending["binCount"],
                   pending["binDigest"], "BURN_ALL_MANAGED_COPIES_CONFIRMED")
    need(done.get("verified") is True and done.get("burnedCount") == 2
         and done.get("total") == 0, "MANAGED_BULK_UNVERIFIED")
    need(managed("list").get("total") == 0, "MANAGED_POST_BURN_NOT_EMPTY")

    after = backend(V2_INDEX, ["index", data_arg], env, "V2_AFTER_BURN")
    need(after.get("total") == 1 and
         after.get("items", [None])[0] == before["items"][0],
         "V2_READ_ONLY_COPY_CHANGED_BY_BURN")
    need(hashlib.sha256(crawl.read_bytes()).hexdigest() == source_digest,
         "SOURCE_MODIFIED_BY_LIFECYCLE")



def run_combined_all(root: Path, env: dict) -> None:
    """Use both real independently guarded stores inside private GVfs CI."""
    home = root / "home"
    data = home / ".local" / "share" / "quickshell"
    data_arg = str(data)
    source = home / ".local/share/post-apollo/finance-crawler/crawl-records.json"
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    snapshots = backend(V2_INDEX, ["index", data_arg], env, "ALL_V2_BEFORE")
    need(snapshots.get("total") == 1, "ALL_V2_MISSING")
    gio = shutil.which("gio", path=env.get("PATH"))
    need(gio is not None, "ALL_GIO_UNAVAILABLE")

    before_copies = backend(MANAGED_BACKEND, ["list", data_arg], env,
                            "ALL_MANAGED_BEFORE")
    need(before_copies.get("binCount") == 0, "ALL_MANAGED_NOT_EMPTY")
    pages = json.loads(source.read_text(encoding="utf-8"))
    selected = pages[0]
    archived = backend(MANAGED_BACKEND,
                       ["archive", data_arg, selected["url"],
                        selected["observedAt"], str(before_copies["revision"])],
                       env, "ALL_CREATE_MANAGED_COPY")
    record = next(x for x in archived["items"] if x["state"] == "archived")
    trashed = backend(MANAGED_BACKEND,
                      ["trash", data_arg, record["id"], str(archived["revision"])],
                      env, "ALL_TRASH_MANAGED_COPY")
    need(trashed.get("binCount") == 1, "ALL_BIN_NOT_ONE")

    file = home / "P1-COMBINED-disposable.txt"
    file.write_bytes(b"PRIVATE_COMBINED_TEST:" + secrets.token_bytes(16))
    need(u9.command([gio, "trash", str(file)], env).returncode == 0,
         "ALL_FILE_TRASH_FAILED")
    gio_before = checked_index(env, "ALL_GIO_BEFORE", 1)
    args = [data_arg, gio_before["revision"], "1",
            str(trashed["revision"]), "1", trashed["binDigest"]]
    refusal(COMBINED_BACKEND, ["burn-all", *args, "NO"], env,
            "COMBINED_BURN_CONFIRMATION_REQUIRED", "ALL_UNCONFIRMED")
    refusal(COMBINED_BACKEND,
            ["burn-all", data_arg, "0" * 64, "1", *args[3:],
             "BURN_ALL_FILES_AND_COPIES_CONFIRMED"], env,
            "STALE_SYSTEM_TRASH_REFRESH_REQUIRED", "ALL_STALE_GIO")
    refusal(COMBINED_BACKEND,
            ["burn-all", data_arg, gio_before["revision"], "1",
             str(trashed["revision"] + 1), "1", trashed["binDigest"],
             "BURN_ALL_FILES_AND_COPIES_CONFIRMED"], env,
            "STALE_MANAGED_COPIES_REFRESH_REQUIRED", "ALL_STALE_MANAGED")

    need(checked_index(env, "ALL_NO_EARLY_FILE_DELETE", 1)["revision"]
         == gio_before["revision"], "ALL_REFUSAL_DELETED_FILE")
    need(backend(MANAGED_BACKEND, ["list", data_arg], env,
                 "ALL_NO_EARLY_COPY_DELETE")["binCount"] == 1,
         "ALL_REFUSAL_DELETED_COPY")

    combined = backend(COMBINED_BACKEND,
                       ["burn-all", *args,
                        "BURN_ALL_FILES_AND_COPIES_CONFIRMED"], env,
                       "ALL_BOTH_CONFIRMED")
    need(combined.get("kind") == "combined-burn-all"
         and combined.get("verified") is True
         and combined.get("partial") is False
         and combined.get("count") == 2
         and combined.get("burnedCount") == 2
         and {x.get("kind") for x in combined.get("burnedItems", [])}
         == {"SYSTEM FILE", "SAVED RESEARCH"},
         "ALL_BOTH_RECEIPT_UNVERIFIED")
    u9.assert_empty_index(checked_index(env, "ALL_AFTER", 0))
    need(backend(MANAGED_BACKEND, ["list", data_arg], env,
                 "ALL_MANAGED_AFTER")["binCount"] == 0,
         "ALL_MANAGED_BIN_NOT_EMPTY")
    need(backend(V2_INDEX, ["index", data_arg], env, "ALL_V2_AFTER") == snapshots,
         "ALL_CHANGED_READ_ONLY_ARCHIVE")
    need(hashlib.sha256(source.read_bytes()).hexdigest() == source_digest,
         "ALL_CHANGED_ORIGINAL_SOURCE")


def validated_child(raw: str, runner: Path, env: dict) -> Path:
    need(bool(env.get("DBUS_SESSION_BUS_ADDRESS")), "PRIVATE_DBUS_REQUIRED")
    need(bool(raw) and os.path.isabs(raw), "CHILD_PATH_INVALID")
    path = Path(raw)
    info = path.lstat()
    need(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
         and not (info.st_mode & 0o077)
         and path.name.startswith(PREFIX)
         and path.resolve().parent == runner, "CHILD_NOT_PRIVATE")
    return path.resolve()


def main(argv: list[str]) -> int:
    try:
        need(len(argv) == 1 or (len(argv) == 3 and argv[1] == "--ci-child"),
             "INVALID_ARGUMENTS")
        inherited = dict(os.environ)
        runner = u9.ci_runner_temp(inherited)  # Must precede any file operation.
        if len(argv) == 3:
            root = validated_child(argv[2], runner, inherited)
            env = u9.isolated_environment(root, inherited)
            run_gio(root, env)
            run_managed_archive(root, env)
            run_combined_all(root, env)
            result = {
                "schema": SCHEMA, "ok": True,
                "scope": "github-actions-private-gvfs-only",
                "gioSingleBurnVerified": True, "gioBurnAllVerified": True,
                "gioUnconfirmedAndStaleDenied": True,
                "combinedAllBurnVerified": True,
                "combinedStaleAndUnconfirmedDenied": True,
                "managedRestoreVerified": True,
                "managedSingleAndBulkBurnVerified": True,
                "archiveV2ReadOnlyPreserved": True,
                "originalSourceUnmodified": True,
                "hospitalAuthorityUsed": False,
                "protectedArchiveAuthorityUsed": False,
                "hostAcceptance": False,
            }
        else:
            with tempfile.TemporaryDirectory(prefix=PREFIX, dir=runner) as temp:
                root = Path(temp)
                env = u9.isolated_environment(root, inherited)
                env.update(GITHUB_ACTIONS="true", CI="true",
                           RUNNER_TEMP=str(runner))
                child = u9.command(
                    ["dbus-run-session", "--", sys.executable, "-I", "-B",
                     str(Path(__file__).resolve()), "--ci-child", str(root)],
                    env, timeout=210)
                try:
                    result = json.loads(child.stdout)
                except (TypeError, ValueError) as exc:
                    raise AcceptanceError("CHILD_INVALID_JSON") from exc
                need(type(result) is dict and
                     ((child.returncode == 0) == (result.get("ok") is True)),
                     "CHILD_RESULT_MISMATCH")
    except (AcceptanceError, u9.RoundTripError) as exc:
        result = {"schema": SCHEMA, "ok": False, "error": str(exc)}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"schema": SCHEMA, "ok": False,
                  "error": "FIXTURE_FAILURE_" + type(exc).__name__}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0 if result.get("ok") is True else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
