"""Browser sign-in *window* status and explicit provider-owned reconnection.

Read-only backend tests run with synthetic Sway trees. Authentication is
unverifiable without provider-specific support. These checks never launch
Chromium, inspect profile contents or contact a provider.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "widgets/messanger/XBrowser.py"
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
UI = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
CATALOG = (ROOT / "services/messaging/SocialAccountCatalog.py").read_text()
STORE = (ROOT / "services/social/SocialAccountDetailsStore.qml").read_text()
spec = importlib.util.spec_from_file_location("social_signin_window_inspect", PATH)
assert spec and spec.loader
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


def leaf(name, cid=14, visible=True):
    return {"id":cid, "visible":visible,
            "window_properties":{"class":name}, "nodes":[]}


def sway_tree(*nodes):
    return {"nodes":list(nodes), "floating_nodes":[]}


class BrowserSigninWindowTests(unittest.TestCase):
    def report(self, tree, service="x", identity="identity-2"):
        with patch.object(browser, "sway_tree", return_value=tree) as query:
            with patch.object(browser, "browser_prefix") as detect:
                with patch.object(browser.subprocess, "Popen") as launch:
                    result=browser.inspect_scoped_window(service, identity)
                    query.assert_called_once()
                    detect.assert_not_called()
                    launch.assert_not_called()
        self.assertEqual(result["authentication"],"UNKNOWN")
        self.assertEqual(result["checkedVia"],"EXACT_SWAY_WINDOW_CLASS_ONLY")
        self.assertEqual(result["reconnectAction"],"OPEN_PROVIDER_WINDOW_MANUALLY")
        self.assertEqual(result["schema"],"post-apollo.social-browser-window.v1")
        self.assertEqual(result["identityId"],identity)
        self.assertEqual(result["site"],service)
        self.assertEqual(set(result),{"schema","identityId","site","windowState",
                                      "authentication","checkedVia","reconnectAction"})
        return result

    def test_only_exact_selected_identity_can_report_open(self):
        tree=sway_tree(leaf("post-apollo-x",10),
                       leaf("post-apollo-x-identity-1",11),
                       leaf("post-apollo-x-identity-2",12))
        self.assertEqual(self.report(tree)["windowState"],"OPEN_VISIBLE")
        self.assertEqual(self.report(tree,identity="identity-3")["windowState"],
                         "NOT_OPEN")
        self.assertEqual(self.report(tree,service="reddit")["windowState"],
                         "NOT_OPEN")

    def test_hidden_and_missing_browser_are_not_authentication_claims(self):
        hidden=sway_tree(leaf("post-apollo-x-identity-2",12,False))
        self.assertEqual(self.report(hidden)["windowState"],"OPEN_HIDDEN")
        self.assertEqual(self.report(sway_tree())["windowState"],"NOT_OPEN")
        self.assertNotIn("authenticated", json.dumps(self.report(hidden)).lower())

    def test_duplicates_and_unverified_sway_ids_fail_closed(self):
        duplicate=sway_tree(leaf("post-apollo-x-identity-2",12),
                            leaf("post-apollo-x-identity-2",13))
        self.assertEqual(self.report(duplicate)["windowState"],"AMBIGUOUS_WINDOW")
        for bad in (None,0,-3,True,"12"):
            with self.subTest(cid=bad):
                sample=sway_tree(leaf("post-apollo-x-identity-2",bad))
                self.assertEqual(self.report(sample)["windowState"],
                                 "UNVERIFIED_WINDOW")

    def test_reject_malformed_identity_and_invalid_sites_before_sway(self):
        for bad in ("", "../identity-2","identity-0","identity-01",
                    "identity-1\\n","identity-1]"):
            with patch.object(browser,"sway_tree") as query:
                with self.assertRaises(ValueError):
                    browser.inspect_scoped_window("x",bad)
                query.assert_not_called()
        with patch.object(browser,"sway_tree") as query:
            with self.assertRaises(ValueError):
                browser.inspect_scoped_window("unlisted","identity-1")
            query.assert_not_called()
            with self.assertRaises(ValueError):
                browser.inspect_scoped_window("x",None)
            query.assert_not_called()

    def test_cli_inspection_is_read_only_and_requires_one_identity(self):
        with patch.object(sys,"argv",["XBrowser.py","inspect","reddit",
                                      "--identity","identity-2"]):
            with patch.object(browser,"sway_tree",
                              return_value=sway_tree(
                                  leaf("post-apollo-reddit-identity-2",20))):
                with patch.object(browser.subprocess,"Popen") as launch:
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        self.assertEqual(browser.main(),0)
                    launch.assert_not_called()
        parsed=json.loads(output.getvalue())
        self.assertEqual(parsed["windowState"],"OPEN_VISIBLE")
        self.assertEqual(parsed["authentication"],"UNKNOWN")
        for args in (["XBrowser.py","inspect","x"],
                     ["XBrowser.py","inspect","all","--identity","identity-2"],
                     ["XBrowser.py","inspect","x","--identity","../identity-1"]):
            with self.subTest(args=args):
                with patch.object(sys,"argv",args):
                    with patch.object(browser,"sway_tree") as query:
                        with contextlib.redirect_stderr(io.StringIO()):
                            self.assertEqual(browser.main(),1)
                        query.assert_not_called()

    def test_chromium_profile_presence_never_changes_window_auth_state(self):
        # No on-disk browser contents may become a sign-in heuristic.
        tree=sway_tree(leaf("post-apollo-x-identity-2",12))
        with patch.object(browser, "browser_profile") as profiles:
            result=self.report(tree)
            profiles.assert_not_called()
        self.assertEqual(result["authentication"],"UNKNOWN")
        self.assertEqual(result["windowState"],"OPEN_VISIBLE")

    def test_ui_keeps_manual_signin_in_existing_contact_pane(self):
        pane=UI.split("id: settingsIdentityPane",1)[1].split(
            "id: settingsEditorPane",1)[0]
        for part in (
            'text: "BROWSER SIGN-IN // MANUAL"',
            'label: "CHECK WINDOW"',
            'label: "OPEN SIGN-IN WINDOW"',
            'function browserAccountServiceSupported(serviceId)',
            'function browserWindowStatusText()',
            'appSelector.browserWindowCheckRequested(',
            'appSelector.browserOpenSignInRequested(',
            'SIGN-IN UNKNOWN',
            'provider website owns sign-in and reconnection',
        ):
            # Helper definitions are on AppSelector; UI controls in pane.
            if part.startswith("function "):
                self.assertIn(part,UI)
            elif part == "SIGN-IN UNKNOWN":
                self.assertIn(part,UI)
            else:
                self.assertIn(part,pane,part)
        self.assertIn('id: settingsFamilyPane',UI)
        self.assertIn('id: settingsAppPane',UI)
        self.assertIn('label: "USER // SETTINGS"',UI)
        self.assertEqual(UI.count('id: settingsFooter'),1)

    def test_host_reuses_isolated_launcher_and_drops_stale_checks(self):
        for part in (
            "id: browserWindowInspectProcess",
            "function browserAccountServiceIndex(serviceId, identityId)",
            "function inspectBrowserAccountWindow(serviceId, identityId)",
            "function openBrowserAccountSignIn(serviceId, identityId)",
            'response.authentication !== "UNKNOWN"',
            'response.checkedVia !== "EXACT_SWAY_WINDOW_CLASS_ONLY"',
            "requestIdentity !== appSelector.identitySnapshot.activeId",
            "requestSite !== appSelector.accountSelectedServiceId",
            "messagingWindow.clearBrowserWindowInspection()",
            "browserConnectionNavigationPending = true",
            "appSelector.settingsOpen = false",
            "activateApp(index)",
            "browserConnectionNavigationPending = false",
            '\"inspect\", serviceId, \"--identity\", identityId',
            "onBrowserWindowCheckRequested:",
            "onBrowserOpenSignInRequested:",
        ):
            self.assertIn(part,HOST,part)
        self.assertIn("property bool browserIsolationEnabled: false", HOST)
        self.assertEqual(HOST.count("FloatingWindow {"),1)
        self.assertIn('command.push("--identity", identity)', HOST)
        self.assertNotIn("SocialAccountDetailsStore",HOST)
        self.assertIn("Setup notes only",STORE)
        self.assertIn("authenticated",CATALOG)

    def test_auth_data_remains_unknown_and_never_derived_from_account_alias(self):
        for item in ("sessionCookie", "accessToken", "Authorization",
                     "OAuth", "getProfileCookie", "loginState"):
            self.assertNotIn(item,UI.split('id: settingsIdentityPane')[1].split(
                             'id: settingsEditorPane')[0])
        self.assertIn('authentication": "UNKNOWN"',PATH.read_text())
        self.assertNotIn('return {"authenticated": True}',PATH.read_text())


if __name__=="__main__":
    unittest.main()
