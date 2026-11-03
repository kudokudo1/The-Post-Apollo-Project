#!/usr/bin/env python3
"""Real Quickshell structure save/reload with three synthetic organizations.

All writes are inside one disposable temporary HOME/XDG root. Two independent
Quickshell processes exercise the production QML/Python singleton. Never load
the user's shell.qml or access the operator's organization records.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
QML = ROOT / "LocalOrganizationStructureNativeSmokeV1.qml"
SCHEMA = "post-apollo.social-local-org-structure.v1"
sys.path.insert(0, str(ROOT / "services" / "social"))
import SocialOrganizationDirectory as directory  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as links  # noqa: E402


def fixture() -> None:
    doc = directory.initial()
    for name, kind in (
        ("SYNTHETIC LLC A", "llc"),
        ("SYNTHETIC LLC B", "llc"),
        ("SYNTHETIC NONPROFIT", "nonprofit"),
    ):
        doc = directory.apply(doc, {
            "action": "add_org", "expectedRevision": doc["revision"],
            "name": name, "kind": kind,
        })
    directory.save(doc)

    portfolio = portfolios.apply(portfolios.initial(), {
        "action": "create", "expectedRevision": 0, "name": "SYNTHETIC PORTFOLIO",
    })
    for ident in ("org-1", "org-2", "org-3"):
        portfolio = portfolios.apply(portfolio, {
            "action": "attach", "expectedRevision": portfolio["revision"],
            "portfolioId": "portfolio-1", "orgId": ident,
        })
    portfolios.save(portfolio)

    account_links = links.apply(links.initial(), {
        "action": "add_link", "expectedRevision": 0,
        "orgId": "org-2", "branchId": None,
        "identityId": "identity-1", "serviceId": None, "accountId": None,
    })
    links.save(account_links)


def assert_document(document: dict) -> None:
    assert document["schema"] == SCHEMA
    assert document["revision"] == 8
    assert document["nextId"] == 6
    assert document["units"] == [
        {"id": "unit-1", "orgId": "org-1", "kind": "division",
         "name": "SYNTHETIC EDUCATION", "archived": False},
        {"id": "unit-2", "orgId": "org-1", "kind": "department",
         "name": "SYNTHETIC ENGINEERING", "archived": False},
        {"id": "unit-3", "orgId": "org-2", "kind": "location",
         "name": "SYNTHETIC NORTH", "archived": False},
        {"id": "unit-4", "orgId": "org-3", "kind": "team",
         "name": "SYNTHETIC OPERATIONS", "archived": False},
        {"id": "unit-5", "orgId": "org-1", "kind": "location",
         "name": "SYNTHETIC EAST", "archived": False},
    ]


def main() -> None:
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("Disposable native Quickshell binary or test root unavailable")
    with tempfile.TemporaryDirectory(prefix="post-apollo-structure-native-") as tmp:
        base = Path(tmp)
        env = os.environ.copy()
        for key, name in (
            ("HOME", "home"), ("XDG_RUNTIME_DIR", "runtime"),
            ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"), ("XDG_DATA_HOME", "data"),
        ):
            folder = base / name
            folder.mkdir(mode=0o700)
            env[key] = str(folder)
        env.update({
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "WAYLAND_DISPLAY": "",
            "DISPLAY": "",
            "QT_LOGGING_RULES": "qt.qpa.*=false",
            "QS_DISABLE_FILE_WATCHER": "1",
            "POST_APOLLO_STRUCTURE_NATIVE_SMOKE": "CI_DISPOSABLE_ONLY",
        })

        # Only the disposable fixture writes to the other accepted stores.
        with patch.dict(os.environ, env, clear=True):
            fixture()
            root = directory.root_path()
            fixture_paths = {
                "organization": root / directory.FILE_NAME,
                "portfolio": root / portfolios.FILE_NAME,
                "links": root / links.FILE_NAME,
            }
            original = {name: path.read_bytes()
                        for name, path in fixture_paths.items()}
        path = root / "local-org-structure-v1.json"
        assert not path.exists(), "Absent file must not be initialized on read"
        previous = None

        for phase in ("create", "reload"):
            env["POST_APOLLO_STRUCTURE_NATIVE_PHASE"] = phase
            result = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT), env=env, check=False, timeout=25,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            output = result.stdout or ""
            marker = "ORG_STRUCTURE_NATIVE_PASS_" + phase.upper()
            if (result.returncode != 0 or marker not in output
                    or "ORG_STRUCTURE_NATIVE_FAIL|" in output):
                diagnostic = [
                    line for line in output.splitlines()
                    if any(term in line for term in (
                        "ERROR", "Error:", "Failed", "WARN", "ORG_STRUCTURE_NATIVE_FAIL",
                    ))
                ]
                raise AssertionError(
                    f"Native structure {phase}: exit={result.returncode}, "
                    f"expected={marker}, diagnostics={diagnostic[-8:]}"
                )

            assert path.is_file(), "Structure did not persist to temporary XDG data"
            assert stat.S_IMODE(root.stat().st_mode) == 0o700
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            data = path.read_bytes()
            assert len(data) <= 65536
            assert_document(json.loads(data))
            for forbidden in (b"accessToken", b"scopeGrants", b"principalId"):
                assert forbidden not in data, "Privileged field in local metadata"
            assert fixture_paths["organization"].read_bytes() == original["organization"], (
                "Native structure editor rewrote the original organization directory"
            )
            assert fixture_paths["portfolio"].read_bytes() == original["portfolio"], (
                "Native structure editor rewrote the original portfolio directory"
            )
            assert fixture_paths["links"].read_bytes() == original["links"], (
                "Native structure editor rewrote existing Social label links"
            )
            if previous is not None:
                assert data == previous, "New Quickshell process changed saved data on read"
            previous = data
            print(f"PASS / native structure {phase} / three synthetic organizations")


if __name__ == "__main__":
    main()
