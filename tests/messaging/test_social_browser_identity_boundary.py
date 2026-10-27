"""Identity-scoped browser profiles: exact class boundaries and fail-closed pilot.

Run without a browser, a compositor, network access, credentials, or writes to
the operator's real Chromium profiles. This stage does not enable live identity
switching. The shared DiscordGeometry.py still owns legacy browser placement.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "widgets/messanger/XBrowser.py"
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
GEOMETRY = (ROOT / "widgets/messanger/DiscordGeometry.py").read_text()
IDENTITIES = (ROOT / "services/social/SocialIdentityStore.qml").read_text()
spec = importlib.util.spec_from_file_location("identity_scoped_browser", SCRIPT)
assert spec is not None and spec.loader is not None
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


class ScopedBrowserBoundary(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="post-apollo-browser-boundary-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        env = patch.dict(os.environ, {
            "XDG_DATA_HOME": str(self.root),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
        })
        env.start()
        self.addCleanup(env.stop)

    def test_default_profile_and_class_unchanged(self):
        prefix = ["/usr/bin/chromium"]
        for site, (_, cls, folder) in browser.ALL_SITES.items():
            with self.subTest(site=site):
                self.assertEqual(browser.site_window_class(site), cls)
                self.assertEqual(browser.site_criteria(site), f'[class="{cls}"]')
                self.assertEqual(browser.browser_profile(site, prefix),
                                 self.root / "post-apollo" / folder)
        with patch.object(browser, "browser_prefix", return_value=prefix):
            cmd = browser.browser_command("x")
        self.assertIn("--class=post-apollo-x", cmd)
        self.assertIn(
            f"--user-data-dir={self.root / 'post-apollo' / 'x-browser'}", cmd)
        self.assertNotIn("--identity", " ".join(cmd))
        self.assertFalse((self.root / "post-apollo").exists())

    def test_scoped_paths_are_isolated_from_legacy_and_other_identities(self):
        prefix = ["/usr/bin/chromium"]
        for site in browser.ALL_SITES:
            a = browser.browser_profile(site, prefix, "identity-1")
            b = browser.browser_profile(site, prefix, "identity-2")
            old = browser.browser_profile(site, prefix)
            self.assertNotEqual(a, b)
            self.assertNotEqual(a, old)
            self.assertNotEqual(b, old)
            self.assertEqual(a.parent, self.root / "post-apollo" / "identities" / "identity-1")
            self.assertEqual(b.parent, self.root / "post-apollo" / "identities" / "identity-2")
            self.assertEqual(browser.site_window_class(site, "identity-1"),
                             browser.site_config(site)[1] + "-identity-1")
            self.assertEqual(browser.site_window_class(site, "identity-2"),
                             browser.site_config(site)[1] + "-identity-2")
        self.assertFalse((self.root / "post-apollo").exists())

    def test_scoped_command_is_pure_and_uses_exact_matching_window_class(self):
        with patch.object(browser, "browser_prefix", return_value=["/usr/bin/chromium"]):
            cmd = browser.browser_command("reddit", "identity-3")
        self.assertIn("--class=post-apollo-reddit-identity-3", cmd)
        self.assertIn(
            f"--user-data-dir={self.root / 'post-apollo/identities/identity-3/reddit-browser'}",
            cmd)
        self.assertEqual(browser.site_criteria("reddit", "identity-3"),
                         '[class="post-apollo-reddit-identity-3"]')
        self.assertNotIn("--class=post-apollo-reddit", cmd)
        self.assertFalse((self.root / "post-apollo").exists())

    def test_flatpak_data_root_is_still_sandbox_specific(self):
        identity = "identity-8"
        prefix = ["flatpak", "run", "com.brave.Browser"]
        scoped = browser.browser_profile("x", prefix, identity)
        self.assertEqual(scoped,
                         Path.home() / ".var/app/com.brave.Browser/data/post-apollo"
                         / "identities" / identity / "x-browser")
        legacy = browser.browser_profile("x", prefix)
        self.assertEqual(legacy,
                         Path.home() / ".var/app/com.brave.Browser/data/post-apollo/x-browser")

    def test_input_values_cannot_escape_identity_namespace_or_match_other_windows(self):
        invalid = (
            "", "identity-0", "identity-01", "identity-0001",
            "identity-1000000000", "identity-1/", "../identity-1",
            "identity-1/a", "identity-1\n", "identity-1]",
            'identity-1" or "all', "identity-1\x00", "work",
            1, True, [], {},
        )
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    browser.validated_identity(value)
                with self.assertRaises(ValueError):
                    browser.site_criteria("x", value)
                with self.assertRaises(ValueError):
                    browser.browser_profile("x", ["/usr/bin/chromium"], value)
                with self.assertRaises(ValueError):
                    browser.profile_plan("x", value)
        with self.assertRaises(ValueError):
            browser.profile_plan("made-up-site", "identity-1")
        self.assertFalse((self.root / "post-apollo").exists())

    def test_exact_scoped_window_match_no_legacy_or_other_identity_fallback(self):
        # Scoped hide now uses an exact Sway con_id, not the old class-wide
        # scratchpad command. Synthetic windows must model that requirement.
        def leaf(cls, con_id):
            return {"window_properties": {"class": cls}, "id": con_id,
                    "visible": True, "nodes": []}
        tree = {
            "nodes": [
                leaf("post-apollo-x", 10),
                leaf("post-apollo-x-identity-1", 11),
                leaf("post-apollo-reddit-identity-2", 12),
            ]
        }
        with patch.object(browser, "sway_tree", return_value=tree):
            self.assertTrue(browser.site_exists("x", "identity-1"))
            self.assertFalse(browser.site_exists("x", "identity-2"))
            self.assertTrue(browser.site_exists("reddit", "identity-2"))
            self.assertFalse(browser.site_exists("reddit", "identity-1"))
            self.assertTrue(browser.site_exists("x"))
        commands = []
        with patch.object(browser, "sway_tree", return_value=tree):
            with patch.object(browser, "sway_command", side_effect=commands.append):
                browser.hide("x", "identity-1")
                browser.hide("x", "identity-2")
                browser.hide("reddit", "identity-2")
        self.assertEqual(commands, [
            '[con_id="11"] move scratchpad',
            '[con_id="12"] move scratchpad',
        ])

    def test_scoped_hide_fails_closed_without_sway_container_id(self):
        malformed = {"nodes": [
            {"window_properties": {"class": "post-apollo-x-identity-1"},
             "visible": True, "nodes": []},
        ]}
        with patch.object(browser, "sway_tree", return_value=malformed):
            with patch.object(browser, "sway_command") as command:
                with self.assertRaisesRegex(
                    RuntimeError, "Managed browser window lacks Sway con_id"
                ):
                    browser.hide("x", "identity-1")
                command.assert_not_called()

    def test_scoped_launch_requires_visible_social_and_extension_setup_stays_blocked(self):
        # Scoped show may now inspect Sway, but it must not start Chromium,
        # create a profile or claim a session without a visible Social window.
        with patch.object(browser, "sway_tree",
                          return_value={"nodes": []}) as tree:
            with patch.object(browser.subprocess, "Popen") as spawn:
                with patch.object(browser, "browser_prefix") as prefix:
                    for site in ("x", "reddit", "linechrome", "whatsappweb"):
                        with self.subTest(site=site):
                            with self.assertRaisesRegex(
                                RuntimeError, "Social window must be visible"
                            ):
                                browser.show(site, "identity-2")
                    with self.assertRaisesRegex(
                        RuntimeError, "awaits geometry integration"
                    ):
                        browser.setup("linechrome", "identity-2")
                    spawn.assert_not_called()
                    self.assertEqual(tree.call_count, 4)
                    prefix.assert_not_called()
        self.assertFalse((self.root / "post-apollo").exists())
        self.assertFalse((self.runtime / "post-apollo-social").exists())

    def test_read_only_profile_plan_does_not_claim_auth_or_migration(self):
        result = browser.profile_plan("instagram", "identity-2")
        self.assertEqual(result, {
            "identityId": "identity-2",
            "site": "instagram",
            "windowClass": "post-apollo-instagram-identity-2",
            "profileRelative": "post-apollo/identities/identity-2/instagram-browser",
            "status": "EXPLICIT_ISOLATED_MODE_REQUIRED",
            "authenticated": None,
            "launchAvailable": False,
            "migrationPerformed": False,
        })
        self.assertFalse((self.root / "post-apollo").exists())

    def test_cli_plan_and_scoped_show_fail_closed_without_starting_browser(self):
        with patch.object(sys, "argv", ["XBrowser.py", "profile", "x",
                                        "--identity", "identity-2"]):
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(browser.main(), 0)
            result = json.loads(stream.getvalue())
            self.assertEqual(result["status"], "EXPLICIT_ISOLATED_MODE_REQUIRED")
            self.assertIsNone(result["authenticated"])
        with patch.object(sys, "argv", ["XBrowser.py", "show", "x",
                                        "--identity", "identity-2"]):
            # Mock the Sway tree read separately. Mocking Popen alone also
            # intercepts subprocess.run's *own* internal Popen for swaymsg.
            with patch.object(browser, "sway_tree",
                              return_value={"nodes": []}) as tree:
                with patch.object(browser.subprocess, "Popen") as spawn:
                    with contextlib.redirect_stderr(io.StringIO()):
                        self.assertEqual(browser.main(), 1)
                    tree.assert_called_once()
                    spawn.assert_not_called()
        with patch.object(sys, "argv", ["XBrowser.py", "profile", "x",
                                        "--identity", "../identity-2"]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(browser.main(), 1)
        self.assertFalse((self.root / "post-apollo").exists())

    def test_legacy_behaviour_stays_active_and_current_social_host_unchanged(self):
        actions = []
        with patch.object(browser, "site_exists", side_effect=lambda site: site == "x"):
            with patch.object(browser, "sway_command", side_effect=actions.append):
                with patch.object(browser.subprocess, "Popen") as spawn:
                    browser.show("x")
                    spawn.assert_not_called()
        self.assertEqual(actions, [
            '[class="post-apollo-x"] move scratchpad',
            '[class="post-apollo-x"] scratchpad show',
        ])
        # The host now constructs the command before appending --identity,
        # so verify the default legacy lane and explicit opt-in separately.
        self.assertIn('Quickshell.shellPath("widgets/messanger/XBrowser.py")', HOST)
        self.assertIn('"show", browserSite]', HOST)
        self.assertIn('if (identity !== "")', HOST)
        self.assertIn('command.push("--identity", identity)', HOST)
        self.assertIn('xShowProcess.exec(command)', HOST)
        self.assertIn('property bool browserIsolationEnabled: false', HOST)
        self.assertIn('XBrowser.py"), "hide", "all"', HOST)
        self.assertIn('function showX()', HOST)
        self.assertIn('function hideX()', HOST)
        self.assertIn('function selectIdentity(id)', IDENTITIES)
        self.assertIn('if window_class != browser_window_class(site, scoped_identity):',
                      GEOMETRY)
        self.assertIn('browser_identity_id: str | None = None', GEOMETRY)
        self.assertIn('if scoped_identity is None:', GEOMETRY)
        self.assertNotIn('browserIdentityId: appSelector.identitySnapshot.activeId',
                         HOST)

if __name__ == "__main__":
    unittest.main()
