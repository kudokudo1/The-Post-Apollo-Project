#!/usr/bin/env python3
"""C4b physical interpreter signed-source staging negative tests (CI only).

No C3d, C2r, C3b or host-workstation files are modified by these tests.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests/connections/c4b_silverblue/prepare_physical_status_host.py"
HOST = ROOT / "tests/connections/c2r_selinux_domain/C2rStatusHost.py"
GUEST = ROOT / "tests/connections/c4b_silverblue/guest_confined_runtime.sh"
WORKFLOW = ROOT / ".github/workflows/connections-c4b-silverblue-confined-runtime.yml"
SPEC = ROOT / "tests/connections/c3d_provenance/signed-status.spec"
C3B = ROOT / "tests/connections/c3b_origin/C3bOriginCheck.py"
spec = importlib.util.spec_from_file_location("c4b_physical_host_prep", SOURCE)
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class C4bPhysicalHostTests(unittest.TestCase):
    def test_01_exact_single_shebang_change_and_immutable_original(self):
        source = HOST.read_bytes()
        self.assertTrue(source.startswith(m.ORIGINAL))
        output = m.convert(source)
        self.assertEqual(output, m.PHYSICAL + source[len(m.ORIGINAL):])
        self.assertNotEqual(output, source)
        self.assertEqual(HOST.read_bytes(), source)
        self.assertIn(b"C2O_CI_SERVICE_READY", output)

    def test_02_no_other_source_or_bypass_accepted(self):
        for bad in (
            b"", b"#!/usr/bin/env python3\n" + b"print('bad')\n",
            b"#!/var/opt/postapollo-c2o-venv/bin/python3\n" + b"wrong\n",
            b"#!/opt/postapollo-c2o-venv/bin/python3.14\n" + b"wrong\n",
            b"#!/opt/postapollo-c2o-venv/bin/python3", None, True, 0,
        ):
            with self.subTest(bad=repr(bad)[:48]):
                with self.assertRaises(ValueError):
                    m.convert(bad)

    def test_03_original_provenance_builder_and_unit_stay_untouched(self):
        workflow = WORKFLOW.read_text()
        self.assertIn("prepare_physical_status_host.py", workflow)
        self.assertIn("POST_APOLLO_C4B_CI_SOURCE=1", workflow)
        self.assertIn(
            "dst=/src/tests/connections/c2r_selinux_domain/C2rStatusHost.py,readonly",
            workflow,
        )
        self.assertIn("dst=/src,readonly", workflow)
        self.assertIn(
            "fedora:44 /usr/bin/bash /src/tests/connections/c3d_provenance/build_signed_ci_status.sh",
            workflow,
        )
        self.assertIn(
            "tests/connections/test_connections_c4b_physical_host.py", workflow
        )
        self.assertIn("postapollo-connections-c3d-ci-status", SPEC.read_text())
        self.assertIn(m.ORIGINAL.decode().strip(), HOST.read_text())

    def test_04_guest_stays_physical_and_original_c3b_unmodified(self):
        runtime = GUEST.read_text()
        self.assertIn("python=/var/opt/postapollo-c2o-venv/bin/python3", runtime)
        self.assertIn("python3 -m venv --without-pip /var/opt/postapollo-c2o-venv", runtime)
        self.assertIn("SIGNED_PHYSICAL_INTERPRETER_SHEBANG_CHECK", runtime)
        self.assertIn("SIGNED_PHYSICAL_INTERPRETER_SHEBANG_PROVEN", runtime)
        self.assertIn("SIGNED_PHYSICAL_INTERPRETER_SHEBANG_NOT_PRESENT", runtime)
        self.assertIn('head -n 1 "$host"', runtime)
        self.assertIn('rm -rf -- /var/opt/postapollo-c2o-venv', runtime)
        self.assertNotIn('python=/opt/postapollo-c2o-venv/bin/python3', runtime)
        self.assertNotIn('python3 -m venv --without-pip /opt/postapollo-c2o-venv', runtime)
        self.assertNotIn('mount -o remount,rw', runtime)
        self.assertNotIn('rpm-ostree usroverlay', runtime)
        self.assertNotIn('setenforce ', runtime)
        c3b = C3B.read_text()
        self.assertIn('INTERPRETER = "/opt/postapollo-c2o-venv/bin/python3"', c3b)
        self.assertIn('"/opt", "/opt/postapollo-c2o-venv"', c3b)
        self.assertNotIn("POST_APOLLO_C4B_CI_SOURCE", c3b)

    def test_05_explicit_disposable_only_stage_restrictions(self):
        source = SOURCE.read_text()
        self.assertIn('os.environ.get("GITHUB_ACTIONS") != "true"', source)
        self.assertIn('os.environ.get("POST_APOLLO_C4B_CI_SOURCE") != "1"', source)
        self.assertIn('dest.open("xb")', source)
        self.assertIn('dest.parent.resolve(strict=True) != temp', source)
        self.assertIn('dest.chmod(0o600)', source)
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("eval(", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
