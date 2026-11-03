#!/usr/bin/env python3
"""Native Quickshell two-process local reporting graph smoke, synthetic only."""
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
QML = ROOT / "LocalFunctionalReportingNativeSmokeV1.qml"
sys.path.insert(0, str(ROOT / "services" / "social"))

import SocialOrganizationDirectory as directory  # noqa: E402
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as social_links  # noqa: E402
import SocialLocalUnitLocationLinks as function_locations  # noqa: E402
import SocialLocalBranchLocationLinks as branch_locations  # noqa: E402

EXPECTED = [
    {"id": "report-link-1", "orgId": "org-1", "parentId": "unit-1", "childId": "unit-2"},
    {"id": "report-link-2", "orgId": "org-1", "parentId": "unit-2", "childId": "unit-3"},
    {"id": "report-link-3", "orgId": "org-1", "parentId": "unit-4", "childId": "unit-3"},
    {"id": "report-link-5", "orgId": "org-2", "parentId": "unit-5", "childId": "unit-6"},
    {"id": "report-link-6", "orgId": "org-3", "parentId": "unit-7", "childId": "unit-8"},
    {"id": "report-link-7", "orgId": "org-1", "parentId": "unit-4", "childId": "unit-2"},
]


def seed_sources() -> None:
    orgs = directory.initial()
    for name, kind in (("FAKE LLC ONE", "llc"), ("FAKE LLC TWO", "llc"),
                       ("FAKE NONPROFIT", "nonprofit")):
        orgs = directory.apply(orgs, {
            "action": "add_org", "expectedRevision": orgs["revision"],
            "name": name, "kind": kind,
        })
    orgs = directory.apply(orgs, {
        "action": "add_branch", "expectedRevision": orgs["revision"],
        "orgId": "org-1", "name": "FAKE BRANCH",
    })
    directory.save(orgs)

    units = structure.initial()
    for org_id, kind, label in (
        ("org-1", "division", "FAKE EDUCATION"),
        ("org-1", "department", "FAKE SUPPORT"),
        ("org-1", "team", "FAKE FIELD"),
        ("org-1", "department", "FAKE OUTREACH"),
        ("org-2", "division", "FAKE SECOND COMPANY"),
        ("org-2", "team", "FAKE SECOND TEAM"),
        ("org-3", "department", "FAKE NONPROFIT"),
        ("org-3", "team", "FAKE THIRD TEAM"),
        ("org-1", "location", "FAKE OFFICE"),
    ):
        units = structure.apply(units, {
            "action": "create", "expectedRevision": units["revision"],
            "orgId": org_id, "kind": kind, "name": label,
        })
    structure.save(units)

    group = portfolios.apply(portfolios.initial(), {
        "action": "create", "expectedRevision": 0, "name": "FAKE PORTFOLIO",
    })
    for org_id in ("org-1", "org-2", "org-3"):
        group = portfolios.apply(group, {
            "action": "attach", "expectedRevision": group["revision"],
            "portfolioId": "portfolio-1", "orgId": org_id,
        })
    portfolios.save(group)

    social = social_links.apply(social_links.initial(), {
        "action": "add_link", "expectedRevision": 0,
        "orgId": "org-1", "branchId": "branch-4",
        "identityId": "identity-1", "serviceId": None, "accountId": None,
    })
    social_links.save(social)

    function_link = function_locations.apply(function_locations.initial(), {
        "action": "add", "expectedRevision": 0,
        "orgId": "org-1", "functionId": "unit-3", "locationId": "unit-9",
    })
    function_locations.save(function_link)

    branch_link = branch_locations.apply(branch_locations.initial(), {
        "action": "add", "expectedRevision": 0,
        "orgId": "org-1", "branchId": "branch-4", "locationId": "unit-9",
    })
    branch_locations.save(branch_link)


def inspect(payload: bytes) -> None:
    doc = json.loads(payload)
    assert doc["schema"] == "post-apollo.social-local-functional-reporting.v1"
    assert doc["revision"] == 8
    assert doc["nextId"] == 8
    assert doc["links"] == EXPECTED
    assert len(payload) <= 65536
    for forbidden in (b"accessToken", b"scopeGrants", b"principalId",
                      b"employeeId", b"managerId"):
        assert forbidden not in payload


def main() -> None:
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("Pinned disposable Quickshell runtime unavailable")
    with tempfile.TemporaryDirectory(prefix="functional-reporting-native-") as temp:
        base = Path(temp)
        env = os.environ.copy()
        for key, folder in (
            ("HOME", "home"), ("XDG_RUNTIME_DIR", "runtime"),
            ("XDG_CONFIG_HOME", "config"), ("XDG_STATE_HOME", "state"),
            ("XDG_CACHE_HOME", "cache"), ("XDG_DATA_HOME", "data"),
        ):
            path = base / folder
            path.mkdir(mode=0o700)
            env[key] = str(path)
        env.update({
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_BACKEND": "software",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "WAYLAND_DISPLAY": "",
            "DISPLAY": "",
            "QT_LOGGING_RULES": "qt.qpa.*=false",
            "QS_DISABLE_FILE_WATCHER": "1",
            "POST_APOLLO_FUNCTIONAL_REPORTING_SMOKE": "CI_DISPOSABLE_ONLY",
        })
        with patch.dict(os.environ, env, clear=True):
            seed_sources()
            root = directory.root_path()
            frozen_paths = {
                "organization": root / directory.FILE_NAME,
                "structure": root / structure.FILE_NAME,
                "portfolio": root / portfolios.FILE_NAME,
                "social": root / social_links.FILE_NAME,
                "function_location": root / function_locations.FILE_NAME,
                "branch_location": root / branch_locations.FILE_NAME,
            }
            original = {name: path.read_bytes()
                        for name, path in frozen_paths.items()}

        target = root / "local-functional-reporting-v1.json"
        assert not target.exists()
        first_bytes = None
        for phase in ("create", "reload"):
            env["POST_APOLLO_FUNCTIONAL_REPORTING_PHASE"] = phase
            process = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT), env=env, check=False, timeout=25,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            output = process.stdout or ""
            marker = "FUNCTION_REPORTING_NATIVE_PASS_" + phase.upper()
            if (process.returncode != 0 or marker not in output
                    or "FUNCTION_REPORTING_NATIVE_FAIL|" in output):
                lines = [
                    line for line in output.splitlines()
                    if any(term in line for term in (
                        "ERROR", "Error:", "Failed", "WARN",
                        "FUNCTION_REPORTING_NATIVE_FAIL",
                    ))
                ]
                raise AssertionError(
                    f"Genuine Quickshell {phase}: exit={process.returncode}, "
                    f"expected={marker}, diagnostics={lines[-8:]}"
                )
            assert target.is_file(), "Missing reporting graph file after QS save"
            assert stat.S_IMODE(root.stat().st_mode) == 0o700
            assert stat.S_IMODE(target.stat().st_mode) == 0o600
            data = target.read_bytes()
            inspect(data)
            for name, source_path in frozen_paths.items():
                assert source_path.read_bytes() == original[name], (
                    f"Native reporting graph altered original {name} data"
                )
            if first_bytes is not None:
                assert data == first_bytes, "Independent QS reload modified data"
            first_bytes = data
            print(f"PASS / genuine Quickshell {phase} / local reporting graph")


if __name__ == "__main__":
    main()
