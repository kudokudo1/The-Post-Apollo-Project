"""P1 product acceptance fixture safety tests. Never invokes actual GIO."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/trash/trash_product_acceptance_p1.py"
spec = importlib.util.spec_from_file_location("trashpp_p1_acceptance", SCRIPT)
p1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p1)


class ProductAcceptanceSafetyTests(unittest.TestCase):
    def test_ci_only_entry_denies_without_side_effects(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-p1-safety-") as tmp:
            output = io.StringIO()
            with patch.dict("os.environ",
                            {"HOME": tmp, "GITHUB_ACTIONS": "false",
                             "CI": "false", "RUNNER_TEMP": tmp}, clear=True):
                with patch.object(p1, "run_gio", side_effect=AssertionError("GIO_CALLED")), \
                     patch.object(p1, "run_managed_archive",
                                  side_effect=AssertionError("ARCHIVE_CALLED")):
                    with redirect_stdout(output):
                        rc = p1.main(["script"])
            self.assertNotEqual(rc, 0)
            data = json.loads(output.getvalue())
            self.assertEqual(data["error"], "CI_ONLY")
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_validated_child_rejects_unowned_names_and_symlinks(self):
        with tempfile.TemporaryDirectory(prefix="trashpp-p1-safety-") as tmp:
            runner = Path(tmp).resolve()
            other = runner / "wrong-name"
            other.mkdir(mode=0o700)
            link = runner / "trashpp-product-p1-link"
            link.symlink_to(other, target_is_directory=True)
            env = {"DBUS_SESSION_BUS_ADDRESS": "test-only"}
            with self.assertRaises(p1.AcceptanceError):
                p1.validated_child(str(other), runner, env)
            with self.assertRaises(p1.AcceptanceError):
                p1.validated_child(str(link), runner, env)
            with self.assertRaises(p1.AcceptanceError):
                p1.validated_child(str(other), runner,
                                   {"DBUS_SESSION_BUS_ADDRESS": ""})

    def test_refusals_must_be_backend_denials(self):
        with patch.object(p1, "backend",
                          return_value={"ok": False, "error": "WRONG"}):
            with self.assertRaisesRegex(p1.AcceptanceError, "UNEXPECTED_REFUSAL"):
                p1.refusal(p1.GIO_BACKEND, [], {}, "EXPECTED", "TEST")

    def test_scope_syntactically_prohibits_unscoped_file_operations(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("shell=True", source)
        self.assertNotIn("os.system(", source)
        self.assertNotIn("shutil.rmtree(", source)
        self.assertNotIn("Path.home()", source)
        self.assertIn("u9.ci_runner_temp(inherited)", source)
        self.assertIn("dbus-run-session", source)
        self.assertIn("u9.assert_empty_index(", source)
        self.assertIn("GIO_BACKEND", source)
        self.assertIn("MANAGED_BACKEND", source)
        self.assertIn("V2_CAPTURE", source)
        self.assertIn("V2_INDEX", source)


if __name__ == "__main__":
    unittest.main()
