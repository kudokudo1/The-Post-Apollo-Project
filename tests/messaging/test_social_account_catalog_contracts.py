"""Contract tests for the Social account-manager handoff, no real logins."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "services/messaging/SocialAccountCatalog.py"
SELECTOR = ROOT / "widgets/messanger/AppSelector.qml"
BROWSER = ROOT / "widgets/messanger/XBrowser.py"
spec = importlib.util.spec_from_file_location("social_catalog", CATALOG)
social = importlib.util.module_from_spec(spec)
spec.loader.exec_module(social)


def browser_site_ids() -> set[str]:
    tree = ast.parse(BROWSER.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "SITES" for t in node.targets):
                assert isinstance(node.value, ast.Dict)
                return {x.value for x in node.value.keys if isinstance(x, ast.Constant)}
    raise AssertionError("XBrowser SITES missing")


class SocialAccountHandoff(unittest.TestCase):
    def test_service_catalog_matches_actual_menu_and_browser_sites(self):
        labels = re.findall(r'name:\s*"([^"]+)"', SELECTOR.read_text(encoding="utf-8"))
        catalog = social.catalog()
        rows = catalog["services"]
        self.assertEqual(len(rows), len(labels))
        self.assertEqual([x["label"] for x in rows], labels)
        self.assertEqual([x["selectorIndex"] for x in rows], list(range(len(rows))))
        self.assertEqual(len(set(x["serviceId"] for x in rows)), len(rows))
        self.assertEqual(browser_site_ids(), social.BROWSER_IDS)
        self.assertEqual(len(social.BROWSER_IDS), 21)
        self.assertEqual(catalog["authority"], "catalog_only")
        self.assertTrue(all(x["supportsManagedBatchLogin"] is False for x in rows))

    def test_conservative_inventory_describes_real_integrations(self):
        kinds = {sid: mode for sid, _label, mode in social.ITEMS}
        self.assertEqual(kinds["sessions"], "native_session")
        self.assertEqual(kinds["telegram"], "native_telegram")
        self.assertEqual(kinds["discord"], "external_app")
        self.assertEqual(kinds["whatsapp"], "unsupported_personal")
        self.assertEqual(kinds["messenger"], "unsupported_personal")
        self.assertEqual(kinds["signal"], "unsupported_personal")
        self.assertEqual(kinds["wechat"], "unsupported_personal")
        self.assertEqual(kinds["line"], "unsupported_personal")
        self.assertEqual(kinds["viber"], "unsupported_personal")
        self.assertEqual(kinds["kakaotalk"], "unsupported_personal")
        self.assertEqual(kinds["bereal"], "unsupported_mobile")
        self.assertNotIn("email", kinds)  # Thunderbird inventory is not a live Social mode.

    def request(self, identity="default", services=None, linked=None):
        if services is None:
            services = ["sessions", "discord", "telegram", "x", "signal", "whatsapp"]
        if linked is None:
            linked = services
        return {
            "schema": "post-apollo.social-accounts.v0",
            "identityId": identity, "services": services,
            "linkedServices": linked,
        }

    def test_default_profile_plan_cannot_claim_authentication_or_login(self):
        out = social.plan(self.request())
        self.assertEqual(out["execution"], "PLAN_ONLY")
        values = {x["serviceId"]: x for x in out["services"]}
        self.assertEqual(values["x"]["status"], "PROFILE_OPEN_AVAILABLE")
        self.assertEqual(values["x"]["nextAction"], "open_existing_browser_profile")
        self.assertEqual(values["telegram"]["status"], "INTERACTIVE_AUTH_AVAILABLE")
        self.assertEqual(values["telegram"]["nextAction"], "telegram_in_menu")
        self.assertEqual(values["sessions"]["status"], "STATUS_CHECK_AVAILABLE")
        self.assertEqual(values["discord"]["status"], "EXTERNAL_APP_AVAILABLE")
        self.assertEqual(values["signal"]["status"], "UNSUPPORTED")
        self.assertEqual(values["whatsapp"]["status"], "UNSUPPORTED")
        self.assertTrue(all(x["authenticated"] is None for x in out["services"]))
        self.assertTrue(all(x["batchLoginPerformed"] is False for x in out["services"]))

    def test_switching_identity_blocks_reuse_of_global_browser_profile(self):
        out = social.plan(self.request(identity="identity_two"))
        for item in out["services"]:
            if item["channel"] in social.BLOCKED:
                self.assertEqual(item["status"], "UNSUPPORTED")
            else:
                self.assertEqual(item["status"], "IDENTITY_ISOLATION_PENDING")
                self.assertEqual(item["nextAction"], "none")
            self.assertIsNone(item["authenticated"])

    def test_unlinked_services_require_manager_link_and_never_launch(self):
        out = social.plan(self.request(services=["x", "telegram", "sessions"], linked=[]))
        self.assertEqual([x["status"] for x in out["services"]], ["UNLINKED"] * 3)
        self.assertEqual([x["nextAction"] for x in out["services"]], ["account_manager_link"] * 3)

    def test_batch_order_is_as_selected_by_account_manager(self):
        out = social.plan(self.request(services=["reddit", "x", "telegram", "sessions"]))
        self.assertEqual([x["serviceId"] for x in out["services"]],
                         ["reddit", "x", "telegram", "sessions"])
        self.assertEqual(out["requested"], 4)
        self.assertEqual(out["openable"], 2)
        self.assertEqual(out["interactive"], 1)

    def test_reject_secrets_invalid_refs_and_unknown_actions(self):
        bad = [
            {**self.request(), "password": "super-secret"},
            {**self.request(), "accessToken": "token"},
            {**self.request(), "schema": "other"},
            {**self.request(), "identityId": "../../evil"},
            {**self.request(), "identityId": ""},
            {**self.request(), "services": ["missing"]},
            {**self.request(), "services": ["x", "x"]},
            {**self.request(), "services": ["x"], "linkedServices": ["telegram"]},
            {**self.request(), "linkedServices": ["x", "x"]},
        ]
        for req in bad:
            with self.subTest(req=str(req)[:60]), self.assertRaises(ValueError):
                social.plan(req)

    def test_cli_is_json_only_and_has_no_network_or_launch_side_effects(self):
        c = subprocess.run([sys.executable, str(CATALOG), "catalog"],
                           text=True, capture_output=True, timeout=5)
        self.assertEqual(c.returncode, 0)
        self.assertEqual(json.loads(c.stdout)["schema"], "post-apollo.social-accounts.v0")
        plan = subprocess.run([sys.executable, str(CATALOG), "plan"],
                              input=json.dumps(self.request()) + "\n",
                              text=True, capture_output=True, timeout=5)
        self.assertEqual(plan.returncode, 0, plan.stderr)
        self.assertEqual(json.loads(plan.stdout)["execution"], "PLAN_ONLY")
        invalid = subprocess.run([sys.executable, str(CATALOG), "plan"],
                                 input=json.dumps({**self.request(), "password": "redact-me"}) + "\n",
                                 text=True, capture_output=True, timeout=5)
        self.assertEqual(invalid.returncode, 2)
        self.assertNotIn("redact-me", invalid.stdout + invalid.stderr)
        src = CATALOG.read_text(encoding="utf-8")
        for forbidden in ("subprocess.Popen", "subprocess.run", "requests.", "urllib.request",
                          "swaymsg", "keyring.", "os.system", "sqlite3.connect"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
