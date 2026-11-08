#!/usr/bin/env python3
"""Synthetic-only C4b Silverblue /opt candidate threat tests.

Not a C3b acceptance suite: the real C3b checker must remain unchanged and
fail closed until its owner authorizes a separate production-neutral policy.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c4b_silverblue/opt_link_profile_candidate.py"
spec = importlib.util.spec_from_file_location("c4b_silverblue_opt_candidate", SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def valid() -> dict:
    link = {
        "owner": 0, "group": 0, "mode": 0o777,
        "directory": False, "symlink": True,
        "target": "var/opt", "resolved": "/var/opt",
        "device": 2049, "inode": 500,
    }
    # Inode identity is part of the proposed trust boundary. Logical
    # /opt/venv paths must describe the same real inodes as /var/opt/venv.
    physical_ids = {
        "/": 900, "/var": 901, "/var/opt": 902,
        "/var/opt/postapollo-c2o-venv": 903,
        "/var/opt/postapollo-c2o-venv/bin": 904,
        "/opt/postapollo-c2o-venv": 903,
        "/opt/postapollo-c2o-venv/bin": 904,
    }
    dirs = {
        path: {
            "owner": 0, "mode": 0o755, "directory": True,
            "symlink": False, "device": 2049, "inode": physical_ids[path],
        }
        for path in m.GUARDED_PATHS
    }
    return {
        "profile": m.PROFILE,
        "fedora_release": "Fedora release 44 (Forty Four)",
        "ostree_booted": True,
        "ostree_ref": "fedora/44/x86_64/silverblue",
        "network_interfaces": [],
        "opt_before": deepcopy(link),
        "opt_after": deepcopy(link),
        "dirs_before": deepcopy(dirs),
        "dirs_after": deepcopy(dirs),
    }


class C4bSilverblueCandidateTests(unittest.TestCase):
    def check(self, data: object, expected: str) -> None:
        result = m.evaluate_candidate(data)
        self.assertEqual(result["status"], expected)
        self.assertEqual(set(result), {"status", *m.DENIED_FLAGS})
        for key in m.DENIED_FLAGS:
            self.assertIs(result[key], False)

    def test_01_exact_literal_layout_is_only_a_candidate(self) -> None:
        self.check(valid(), "C4B_SILVERBLUE_OPT_LAYOUT_CANDIDATE_ONLY")
        self.assertNotIn("C3B_PASS", m.evaluate_candidate(valid())["status"])

    def test_02_invalid_schema_never_returns_candidate(self) -> None:
        for bad in (None, [], {}, "evidence", 1, True):
            with self.subTest(bad=repr(bad)):
                self.check(bad, "C4B_CANDIDATE_INVALID_EVIDENCE")
        for field in m.CONTEXT_KEYS:
            with self.subTest(missing=field):
                data = valid()
                del data[field]
                self.check(data, "C4B_CANDIDATE_INVALID_EVIDENCE")
        data = valid()
        data["privileged"] = True
        self.check(data, "C4B_CANDIDATE_INVALID_EVIDENCE")

    def test_03_only_explicit_offline_silverblue_44_context(self) -> None:
        changes = {
            "profile": [None, "", "C3B_PRODUCTION", "C4B_OFFLINE_SILVERBLUE_45_CANDIDATE_ONLY"],
            "fedora_release": ["Fedora release 43", "Fedora release 45", "Ubuntu 24.04", None],
            "ostree_booted": [False, 1, None],
            "ostree_ref": [None, "", "fedora/44/x86_64/workstation", "/fake", "notsilverblue", "fedora/45/x86_64/silverblue", "fedora/44/aarch64/silverblue"],
            "network_interfaces": [["eth0"], ["wlan0"], None, "[]", {"lo": "only"}],
        }
        for field, values in changes.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    data = valid()
                    data[field] = value
                    self.check(data, "C4B_CANDIDATE_NOT_OFFLINE_SILVERBLUE_44")

    def test_04_no_redirected_or_aliased_link_targets(self) -> None:
        targets = [
            "/var/opt", "../var/opt", "var/opt/", "var//opt", "var/../var/opt",
            "var/opt/../tmp", "../../tmp", "/tmp", "var/tmp", "var/opt\x00",
            "./var/opt", "var/opt/postapollo", None, "",
        ]
        for field in ("opt_before", "opt_after"):
            for target in targets:
                with self.subTest(field=field, target=repr(target)):
                    data = valid()
                    data[field]["target"] = target
                    self.check(data, "C4B_CANDIDATE_UNTRUSTED_OPT_LINK")
            for resolved in ("/tmp", "/var/tmp", "/var/opt/", None, "../var/opt", ""):
                with self.subTest(field=field, resolved=repr(resolved)):
                    data = valid()
                    data[field]["resolved"] = resolved
                    self.check(data, "C4B_CANDIDATE_UNTRUSTED_OPT_LINK")

    def test_05_link_inode_must_be_root_owned_real_symlink(self) -> None:
        bad = {
            "owner": [1000, True, -1],
            "group": [1000, True, -1],
            "mode": [0o755, 0o775, True, "0777"],
            "directory": [True, 1, None],
            "symlink": [False, 1, None],
            "device": [0, -1, True, "2049"],
            "inode": [0, -1, True, "500"],
        }
        for field in ("opt_before", "opt_after"):
            for key, values in bad.items():
                for value in values:
                    with self.subTest(field=field, key=key, value=repr(value)):
                        data = valid()
                        data[field][key] = value
                        self.check(data, "C4B_CANDIDATE_UNTRUSTED_OPT_LINK")
            data = valid()
            del data[field]["target"]
            self.check(data, "C4B_CANDIDATE_UNTRUSTED_OPT_LINK")
            data = valid()
            data[field]["untrusted"] = "extra"
            self.check(data, "C4B_CANDIDATE_UNTRUSTED_OPT_LINK")

    def test_06_changed_link_between_observations_refused(self) -> None:
        for key, value in (
            ("device", 2050),
            ("inode", 501),
            ("mode", 0o777),  # tested independently below when unchanged
        ):
            if key == "mode":
                continue
            data = valid()
            data["opt_after"][key] = value
            self.check(data, "C4B_CANDIDATE_OPT_LINK_CHANGED")

    def test_07_no_missing_or_extra_ancestor_paths(self) -> None:
        for field in ("dirs_before", "dirs_after"):
            for path in m.GUARDED_PATHS:
                with self.subTest(field=field, missing=path):
                    data = valid()
                    del data[field][path]
                    self.check(data, "C4B_CANDIDATE_INVALID_DIRECTORY_CHAIN")
            data = valid()
            data[field]["/tmp"] = {
                "owner": 0, "mode": 0o755, "directory": True, "symlink": False
            }
            self.check(data, "C4B_CANDIDATE_INVALID_DIRECTORY_CHAIN")
            data = valid()
            data[field] = []
            self.check(data, "C4B_CANDIDATE_INVALID_DIRECTORY_CHAIN")

    def test_08_every_guarded_dir_must_be_safe_before_and_after(self) -> None:
        changes = {
            "owner": [1000, True, -1],
            "mode": [0o777, 0o775, 0o757, 0o733, True, "0755", -1],
            "directory": [False, 1, None],
            "symlink": [True, 1, None],
            "device": [0, -1, True, "2049", None],
            "inode": [0, -1, True, "904", None],
        }
        for field in ("dirs_before", "dirs_after"):
            for path in m.GUARDED_PATHS:
                for key, values in changes.items():
                    for value in values:
                        with self.subTest(field=field, path=path, key=key, value=repr(value)):
                            data = valid()
                            data[field][path][key] = value
                            self.check(data, "C4B_CANDIDATE_UNPROTECTED_DIRECTORY")
                for mutation in ("missing", "extra"):
                    data = valid()
                    if mutation == "missing":
                        del data[field][path]["owner"]
                    else:
                        data[field][path]["new_property"] = True
                    self.check(data, "C4B_CANDIDATE_UNPROTECTED_DIRECTORY")

    def test_09_directory_identity_changes_refused(self) -> None:
        # Both snapshots independently satisfy the protection predicate,
        # but changed mode still refuses before any origin assertion.
        for path in m.GUARDED_PATHS:
            data = valid()
            data["dirs_after"][path]["mode"] = 0o750
            self.check(data, "C4B_CANDIDATE_DIRECTORY_CHAIN_CHANGED")

    def test_09b_replaced_inodes_refused_even_with_same_owner_mode(self) -> None:
        # Swapping a directory inode may leave UID, mode and type unchanged.
        for path in m.GUARDED_PATHS:
            for identity_field in ("inode", "device"):
                with self.subTest(path=path, identity_field=identity_field):
                    data = valid()
                    data["dirs_after"][path][identity_field] += 1
                    self.check(data, "C4B_CANDIDATE_DIRECTORY_CHAIN_CHANGED")

    def test_09c_logical_opt_alias_must_match_physical_inode(self) -> None:
        for physical, alias in m.PHYSICAL_ALIAS_PAIRS:
            for swapped in ("device", "inode"):
                for path in (physical, alias):
                    with self.subTest(path=path, field=swapped):
                        data = valid()
                        # Keep BEFORE and AFTER internally stable to isolate
                        # the mismatch between the real and alias paths.
                        data["dirs_before"][path][swapped] += 1
                        data["dirs_after"][path][swapped] += 1
                        self.check(data, "C4B_CANDIDATE_ALIAS_IDENTITY_MISMATCH")

    def test_09d_no_second_symlink_is_allowed_on_alias_target(self) -> None:
        for physical, alias in m.PHYSICAL_ALIAS_PAIRS:
            for path in (physical, alias):
                for snapshot in ("dirs_before", "dirs_after"):
                    with self.subTest(path=path, snapshot=snapshot):
                        data = valid()
                        data[snapshot][path]["symlink"] = True
                        data[snapshot][path]["directory"] = False
                        self.check(data, "C4B_CANDIDATE_UNPROTECTED_DIRECTORY")

    def test_10_no_os_access_or_grant_authority_in_candidate(self) -> None:
        source = SOURCE.read_text()
        for forbidden in (
            "import os", "import subprocess", "import socket",
            "os.lstat(", "os.readlink(", "os.path.realpath(",
            "systemctl ", "setenforce ", "semodule ", "grantActive\": True",
            "hostAuthenticated\": True", "canApprove\": True",
            "canUseApi\": True", "C3B_PASS //",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        original = (ROOT / "tests/connections/c3b_origin/C3bOriginCheck.py").read_text()
        self.assertNotIn("opt_link_profile_candidate", original)
        self.assertNotIn("C4B_SILVERBLUE_OPT_LAYOUT_CANDIDATE_ONLY", original)


if __name__ == "__main__":
    unittest.main(verbosity=2)
