"""Source and fixture safety checks for disposable real-Quickshell smoke.

Never starts qs, changes local config, opens an external connection or writes
any runtime directory. Genuine native Process/Qt tests run in Debian CI job.
"""
from __future__ import annotations

from pathlib import Path
import importlib.util
import json
import unittest

ROOT = Path(__file__).resolve().parents[2]
SMOKE = ROOT / "IdentityNativeDisplaySmokeV0.qml"
SCRIPT = ROOT / "tests/identity/native_quickshell_display_smoke_v0.py"
SHELL = ROOT / "shell.qml"
READER = ROOT / "widgets/messanger/IdentityCenterOrganizationDisplayReader.qml"
SECTIONS = ROOT / "widgets/messanger/IdentityCenterSettingsSections.qml"


def fixture():
    spec = importlib.util.spec_from_file_location("identity_smoke_runner", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SyntheticNativeQuickshellGuard(unittest.TestCase):
    def test_unmounted_smoke_root_requires_exact_test_gate(self):
        root = SMOKE.read_text()
        self.assertNotIn(SMOKE.name, SHELL.read_text())
        self.assertIn("ShellRoot {", root)
        self.assertIn("IdentityCenterSettingsSections {", root)
        self.assertIn('=== "CI_DISPOSABLE_ONLY"', root)
        self.assertIn('settingsOpen: smoke.armed', root)
        self.assertIn('activeSection: smoke.armed ? "ORGANIZATIONS" : "SOCIAL LAYOUT"', root)
        self.assertIn("Quickshell.watchFiles = false;", root)
        self.assertIn("if (!armed)", root)
        for invalid in ("PanelWindow {", "FloatingWindow {", "FileView {",
                        "Qt.openUrlExternally", "requestWrite(", "execDetached("):
            self.assertNotIn(invalid, root)

    def test_quickshell_uses_existing_readonly_ui_only(self):
        smoke = SMOKE.read_text()
        reader = READER.read_text()
        sections = SECTIONS.read_text()
        for expected in (
            "IDENTITY_NATIVE_SMOKE_PASS_READY",
            "IDENTITY_NATIVE_SMOKE_PASS_SIGNED_OUT",
            "IDENTITY_NATIVE_SMOKE_PASS_MISSING",
            "IDENTITY_NATIVE_SMOKE_PASS_REVOKE",
        ):
            self.assertIn(expected, smoke)
        self.assertIn('label: "SWITCH ORGANIZATION // UNAVAILABLE"', sections)
        idx = sections.index('label: "SWITCH ORGANIZATION // UNAVAILABLE"')
        self.assertIn("interactive: false", sections[idx:idx + 230])
        self.assertIn('readerPath, "--json"', reader)
        self.assertNotIn("accessToken", reader)
        self.assertNotIn("refreshToken", reader)
        self.assertNotIn("Bearer ", reader)

    def test_runner_cannot_start_operator_default_shell_or_use_credentials(self):
        runner = SCRIPT.read_text()
        self.assertIn('shutil.which("qs")', runner)
        self.assertIn('[qs, "-p", str(root_config), "--no-color"]', runner)
        self.assertIn("TemporaryDirectory(", runner)
        self.assertIn('"XDG_RUNTIME_DIR": str(xdg)', runner)
        for name in ("HOME", "XDG_CACHE_HOME", "XDG_CONFIG_HOME",
                     "XDG_STATE_HOME", "XDG_DATA_HOME"):
            self.assertIn('("' + name + '",', runner)
        self.assertIn('"WAYLAND_DISPLAY": ""', runner)
        self.assertIn('"DISPLAY": ""', runner)
        self.assertIn('"QT_QPA_PLATFORM": "offscreen"', runner)
        for forbidden in (
            '["qs", "kill"]', '"qs -c default"',
            "os.system(", "shell=True", "sudo ", "requests.",
            "urllib.request", "password", "access_token",
            "refresh_token", "real_company",
        ):
            self.assertNotIn(forbidden, runner)

    def test_all_fixture_objects_are_synthetic_and_never_authorize_switching(self):
        module = fixture()
        self.assertEqual(set(module.EXPECTED), {
            "ready", "signed-out", "missing", "revoke",
        })
        for status in ("READY", "SIGNED_OUT", "UNAVAILABLE"):
            result = module.synthetic(status)
            self.assertEqual(
                result["schema"], "post-apollo.identity.desktop-context-display.v0"
            )
            self.assertFalse(result["canSwitchOrganization"])
            rendered = json.dumps(result)
            self.assertNotIn("accessToken", rendered)
            self.assertNotIn("refreshToken", rendered)
            self.assertNotIn("Bearer", rendered)
            self.assertNotIn("principalId", rendered)
        ready = module.synthetic("READY")
        self.assertEqual(
            [x["organizationId"] for x in ready["organizations"]],
            ["synthetic_llc_a", "synthetic_nonprofit"],
        )
        self.assertEqual(ready["portfolios"][0]["organizationIds"],
                         ["synthetic_llc_a", "synthetic_nonprofit"])
        self.assertTrue(all(not item["scopeGrants"]
                            for item in ready["organizations"]))
        self.assertEqual(module.synthetic("SIGNED_OUT")["organizations"], [])

    def test_native_smoke_has_no_production_import_or_unsafe_switch(self):
        self.assertFalse(
            any(SMOKE.name in file.read_text(errors="replace")
                for file in (SHELL, SECTIONS, READER))
        )
        self.assertNotIn("switchOrganization(", SMOKE.read_text())
        self.assertNotIn("selectedOrganizationId", SMOKE.read_text())


if __name__ == "__main__":
    unittest.main()
