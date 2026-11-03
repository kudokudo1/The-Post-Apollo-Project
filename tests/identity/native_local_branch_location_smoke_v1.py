#!/usr/bin/env python3
"""Genuine Quickshell create/reload with three fake organizations and private XDG."""
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
QML = ROOT / "LocalBranchLocationNativeSmokeV1.qml"
sys.path.insert(0, str(ROOT / "services" / "social"))

import SocialOrganizationDirectory as organizations  # noqa: E402
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as social_links  # noqa: E402
import SocialLocalUnitLocationLinks as function_locations  # noqa: E402

EXPECTED = [
    {"id": "branch-placement-2", "orgId": "org-1",
     "branchId": "branch-4", "locationId": "unit-2"},
    {"id": "branch-placement-3", "orgId": "org-1",
     "branchId": "branch-7", "locationId": "unit-1"},
    {"id": "branch-placement-4", "orgId": "org-2",
     "branchId": "branch-5", "locationId": "unit-3"},
    {"id": "branch-placement-5", "orgId": "org-3",
     "branchId": "branch-6", "locationId": "unit-4"},
    {"id": "branch-placement-6", "orgId": "org-1",
     "branchId": "branch-7", "locationId": "unit-2"},
]


def seed_sources() -> None:
    doc = organizations.initial()
    for name, kind in (
        ("FAKE LLC ONE", "llc"),
        ("FAKE LLC TWO", "llc"),
        ("FAKE NONPROFIT", "nonprofit"),
    ):
        doc = organizations.apply(doc, {
            "action": "add_org", "expectedRevision": doc["revision"],
            "name": name, "kind": kind,
        })
    for oid, label in (
        ("org-1", "FAKE BRANCH A"),
        ("org-2", "FAKE BRANCH B"),
        ("org-3", "FAKE BRANCH C"),
        ("org-1", "FAKE BRANCH D"),
    ):
        doc = organizations.apply(doc, {
            "action": "add_branch", "expectedRevision": doc["revision"],
            "orgId": oid, "name": label,
        })
    organizations.save(doc)

    units = structure.initial()
    for oid, kind, label in (
        ("org-1", "location", "FAKE NORTH"),
        ("org-1", "location", "FAKE SOUTH"),
        ("org-2", "location", "FAKE WEST"),
        ("org-3", "location", "FAKE EAST"),
        ("org-1", "team", "FAKE OPERATIONS"),
    ):
        units = structure.apply(units, {
            "action": "create", "expectedRevision": units["revision"],
            "orgId": oid, "kind": kind, "name": label,
        })
    structure.save(units)

    group = portfolios.apply(portfolios.initial(), {
        "action": "create", "expectedRevision": 0,
        "name": "FAKE THREE COMPANY GROUP",
    })
    for oid in ("org-1", "org-2", "org-3"):
        group = portfolios.apply(group, {
            "action": "attach", "expectedRevision": group["revision"],
            "portfolioId": "portfolio-1", "orgId": oid,
        })
    portfolios.save(group)

    social = social_links.apply(social_links.initial(), {
        "action": "add_link", "expectedRevision": 0,
        "orgId": "org-1", "branchId": "branch-4",
        "identityId": "identity-1", "serviceId": None, "accountId": None,
    })
    social_links.save(social)

    function = function_locations.apply(function_locations.initial(), {
        "action": "add", "expectedRevision": 0,
        "orgId": "org-1", "functionId": "unit-5", "locationId": "unit-1",
    })
    function_locations.save(function)


def inspect(raw: bytes) -> None:
    doc = json.loads(raw)
    assert doc["schema"] == "post-apollo.social-local-branch-location-links.v1"
    assert doc["revision"] == 7
    assert doc["nextId"] == 7
    assert doc["links"] == EXPECTED
    assert len(raw) <= 65536
    for name in (b"scopeGrants", b"accessToken", b"principalId",
                 b"refreshToken", b"verifiedAddress"):
        assert name not in raw


def run() -> None:
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("Pinned disposable Quickshell runtime unavailable")
    with tempfile.TemporaryDirectory(prefix="branch-location-native-") as temp:
        base = Path(temp)
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
            "POST_APOLLO_LOCAL_BRANCH_LOCATION_SMOKE": "CI_DISPOSABLE_ONLY",
        })
        with patch.dict(os.environ, env, clear=True):
            seed_sources()
            root = organizations.root_path()
            frozen_paths = {
                "organizations": root / organizations.FILE_NAME,
                "structure": root / structure.FILE_NAME,
                "portfolios": root / portfolios.FILE_NAME,
                "social": root / social_links.FILE_NAME,
                "function_locations": root / function_locations.FILE_NAME,
            }
            source_bytes = {
                name: path.read_bytes() for name, path in frozen_paths.items()
            }

        path = root / "local-branch-location-links-v1.json"
        assert not path.exists()
        first_bytes = None
        for phase in ("create", "reload"):
            env["POST_APOLLO_LOCAL_BRANCH_LOCATION_PHASE"] = phase
            process = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT), env=env, check=False, timeout=25,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            output = process.stdout or ""
            marker = "BRANCH_LOCATION_NATIVE_PASS_" + phase.upper()
            if (process.returncode != 0 or marker not in output
                    or "BRANCH_LOCATION_NATIVE_FAIL|" in output):
                lines = [
                    line for line in output.splitlines()
                    if any(term in line for term in (
                        "ERROR", "Error:", "Failed", "WARN",
                        "BRANCH_LOCATION_NATIVE_FAIL",
                    ))
                ]
                raise AssertionError(
                    f"Quickshell {phase} exit={process.returncode} "
                    f"expected={marker} diagnostics={lines[-8:]}"
                )
            assert path.is_file(), "Missing branch-location store after Quickshell"
            assert stat.S_IMODE(root.stat().st_mode) == 0o700
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
            data = path.read_bytes()
            inspect(data)
            for name, original_path in frozen_paths.items():
                assert original_path.read_bytes() == source_bytes[name], (
                    f"Native test changed original {name} source bytes"
                )
            if first_bytes is not None:
                assert data == first_bytes, "New process altered links on read"
            first_bytes = data
            print(f"PASS / real Quickshell {phase} / synthetic branch locations")


if __name__ == "__main__":
    run()
