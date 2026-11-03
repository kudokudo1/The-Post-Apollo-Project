#!/usr/bin/env python3
"""Two genuine Quickshell processes under isolated fake three-company XDG roots."""
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
QML = ROOT / "LocalUnitLocationNativeSmokeV1.qml"
sys.path.insert(0, str(ROOT / "services" / "social"))

import SocialOrganizationDirectory as directory  # noqa: E402
import SocialLocalOrganizationStructure as structure  # noqa: E402
import SocialLocalPortfolios as portfolios  # noqa: E402
import SocialOrganizationLinks as social_links  # noqa: E402

EXPECTED_LINKS = [
    {"id": "placement-2", "orgId": "org-1",
     "functionId": "unit-1", "locationId": "unit-4"},
    {"id": "placement-3", "orgId": "org-1",
     "functionId": "unit-2", "locationId": "unit-3"},
    {"id": "placement-4", "orgId": "org-2",
     "functionId": "unit-5", "locationId": "unit-6"},
    {"id": "placement-5", "orgId": "org-3",
     "functionId": "unit-7", "locationId": "unit-8"},
    {"id": "placement-6", "orgId": "org-1",
     "functionId": "unit-2", "locationId": "unit-4"},
]


def seed_sources() -> None:
    companies = directory.initial()
    for name, kind in (("FAKE LLC ONE", "llc"), ("FAKE LLC TWO", "llc"),
                       ("FAKE NONPROFIT", "nonprofit")):
        companies = directory.apply(companies, {
            "action": "add_org", "expectedRevision": companies["revision"],
            "name": name, "kind": kind,
        })
    directory.save(companies)

    units = structure.initial()
    for org_id, kind, label in (
        ("org-1", "division", "FAKE EDUCATION"),
        ("org-1", "team", "FAKE SUPPORT"),
        ("org-1", "location", "FAKE NORTH"),
        ("org-1", "location", "FAKE SOUTH"),
        ("org-2", "department", "FAKE OPERATIONS"),
        ("org-2", "location", "FAKE WEST"),
        ("org-3", "team", "FAKE OUTREACH"),
        ("org-3", "location", "FAKE EAST"),
    ):
        units = structure.apply(units, {
            "action": "create", "expectedRevision": units["revision"],
            "orgId": org_id, "kind": kind, "name": label,
        })
    structure.save(units)

    group = portfolios.apply(portfolios.initial(), {
        "action": "create", "expectedRevision": 0, "name": "FAKE GROUP",
    })
    for org_id in ("org-1", "org-2", "org-3"):
        group = portfolios.apply(group, {
            "action": "attach", "expectedRevision": group["revision"],
            "portfolioId": "portfolio-1", "orgId": org_id,
        })
    portfolios.save(group)

    link = social_links.apply(social_links.initial(), {
        "action": "add_link", "expectedRevision": 0,
        "orgId": "org-2", "branchId": None,
        "identityId": "identity-1", "serviceId": None, "accountId": None,
    })
    social_links.save(link)


def inspect(document: dict) -> None:
    assert document["schema"] == "post-apollo.social-local-unit-location-links.v1"
    assert document["revision"] == 7
    assert document["nextId"] == 7
    assert document["links"] == EXPECTED_LINKS


def main() -> None:
    qs = shutil.which("qs")
    if qs is None or not QML.is_file():
        raise RuntimeError("Genuine disposable Quickshell root unavailable")
    with tempfile.TemporaryDirectory(prefix="unit-location-native-smoke-") as tmp:
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
            "POST_APOLLO_LOCAL_UNIT_LOCATION_SMOKE": "CI_DISPOSABLE_ONLY",
        })

        # Seed only temporary data; freeze source file paths before restoring
        # the host environment. Never recompute them from a different HOME.
        with patch.dict(os.environ, env, clear=True):
            seed_sources()
            root = directory.root_path()
            source_paths = {
                "directory": root / directory.FILE_NAME,
                "structure": root / structure.FILE_NAME,
                "portfolio": root / portfolios.FILE_NAME,
                "social": root / social_links.FILE_NAME,
            }
            original = {name: path.read_bytes()
                        for name, path in source_paths.items()}

        target = root / "local-unit-location-links-v1.json"
        assert not target.exists()
        first_payload = None

        for phase in ("create", "reload"):
            env["POST_APOLLO_LOCAL_UNIT_LOCATION_PHASE"] = phase
            process = subprocess.run(
                [qs, "-p", str(QML), "--no-color"],
                cwd=str(ROOT), env=env, check=False, timeout=25,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, errors="replace",
            )
            output = process.stdout or ""
            marker = "UNIT_LOCATION_NATIVE_PASS_" + phase.upper()
            if (process.returncode != 0 or marker not in output
                    or "UNIT_LOCATION_NATIVE_FAIL|" in output):
                diagnostics = [
                    line for line in output.splitlines()
                    if any(x in line for x in (
                        "ERROR", "Error:", "Failed", "WARN", "UNIT_LOCATION_NATIVE_FAIL",
                    ))
                ]
                raise AssertionError(
                    f"Native {phase} failed: exit={process.returncode}, "
                    f"marker={marker}, diagnostics={diagnostics[-8:]}"
                )
            assert target.is_file(), "No saved local placement file"
            assert stat.S_IMODE(root.stat().st_mode) == 0o700
            assert stat.S_IMODE(target.stat().st_mode) == 0o600
            data = target.read_bytes()
            assert len(data) <= 65536
            inspect(json.loads(data))
            for sensitive in (b"scopeGrants", b"accessToken", b"principalId",
                              b"providerSubject"):
                assert sensitive not in data
            for name, path in source_paths.items():
                assert path.read_bytes() == original[name], (
                    f"Native placement run modified original {name} data"
                )
            if first_payload is not None:
                assert data == first_payload, (
                    "Independent Quickshell reload changed persisted links"
                )
            first_payload = data
            print(f"PASS / genuine Quickshell {phase} / local unit locations")


if __name__ == "__main__":
    main()
