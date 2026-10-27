"""Offline cross-identity browser handoff and secure profile preparation.

Only synthetic Sway trees and private temporary runtime directories are used.
No desktop browser, provider account, Sway compositor or user profile is touched.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BROWSER_PATH = ROOT / "widgets/messanger/XBrowser.py"
GEOMETRY_PATH = ROOT / "widgets/messanger/DiscordGeometry.py"
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
UI = (ROOT / "widgets/messanger/AppSelector.qml").read_text()
spec = importlib.util.spec_from_file_location("identity_live_browser", BROWSER_PATH)
browser = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(browser)
spec = importlib.util.spec_from_file_location("identity_live_geometry", GEOMETRY_PATH)
geometry = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(geometry)


def browser_node(cls: str, cid: int, *, visible: bool = True):
    return {"window_properties": {"class": cls}, "id": cid,
            "visible": visible, "rect": {"x": 111, "y": 15,
                                         "width": 590, "height": 650}}


def sway_tree(*windows):
    return {"nodes": [
        {"name": "QS_SOCIAL_MENU", "visible": True, "id": 1,
         "rect": {"x": 0, "y": 0, "width": 700, "height": 700}},
        *windows,
    ]}


class IdentityLiveBrowserTests(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory(prefix="apollo-browser-handoff-")
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        env = patch.dict(os.environ, {
            "XDG_DATA_HOME": str(self.root / "data"),
            "XDG_RUNTIME_DIR": str(self.runtime),
            "POST_APOLLO_X_BROWSER": "/usr/bin/chromium",
        })
        env.start()
        self.addCleanup(env.stop)

    def test_existing_scoped_window_focuses_only_selected_identity(self):
        tree = sway_tree(
            browser_node("post-apollo-x", 10),
            browser_node("post-apollo-x-identity-1", 11),
            browser_node("post-apollo-x-identity-2", 12, visible=False),
        )
        calls = []
        with patch.object(browser, "sway_tree", return_value=tree):
            with patch.object(browser, "sway_command", side_effect=calls.append):
                with patch.object(browser.subprocess, "Popen") as spawned:
                    browser.show("x", "identity-2")
                    spawned.assert_not_called()
        self.assertEqual(calls, [
            '[con_id="10"] move scratchpad',
            '[con_id="11"] move scratchpad',
            '[con_id="12"] move scratchpad',
            '[con_id="12"] scratchpad show',
        ])
        self.assertFalse((self.root / "data/post-apollo").exists())
        saved = browser.load_selection(browser.selection_runtime())
        self.assertEqual(saved["identityId"], "identity-2")
        self.assertEqual(saved["site"], "x")
        self.assertEqual(stat.S_IMODE(
            (self.runtime/"post-apollo-social"/"browser-selection.json").stat().st_mode),
            0o600)

    def test_new_isolated_profile_gets_owner_only_dir_without_copying_legacy(self):
        legacy = self.root/"data"/"post-apollo"/"x-browser"
        legacy.mkdir(parents=True, mode=0o700)
        (legacy/"old-cookies.marker").write_text("leave untouched")
        launched = []
        def observed():
            windows = []
            if launched:
                windows.append(browser_node("post-apollo-x-identity-2", 30))
            return sway_tree(*windows)
        with patch.object(browser, "sway_tree", side_effect=observed):
            with patch.object(browser, "browser_prefix", return_value=["/usr/bin/chromium"]):
                with patch.object(browser.subprocess, "Popen",
                                  side_effect=lambda cmd, **kw: launched.append(cmd)):
                    with patch.object(browser, "sway_command"):
                        with patch.object(browser.time, "sleep"):
                            browser.show("x", "identity-2")
        self.assertEqual(len(launched), 1)
        cmd = launched[0]
        self.assertIn("--class=post-apollo-x-identity-2", cmd)
        profile = self.root/"data/post-apollo/identities/identity-2/x-browser"
        self.assertIn(f"--user-data-dir={profile}", cmd)
        self.assertEqual((legacy/"old-cookies.marker").read_text(), "leave untouched")
        self.assertFalse((profile/"old-cookies.marker").exists())
        for path in (profile, profile.parent, profile.parent.parent):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)

    def test_switching_identities_invalidates_previous_launch_token(self):
        observed = sway_tree(
            browser_node("post-apollo-x-identity-1", 11),
            browser_node("post-apollo-x-identity-2", 12),
        )
        with patch.object(browser, "sway_tree", return_value=observed):
            with patch.object(browser, "sway_command"):
                browser.show("x", "identity-1")
                old = browser.load_selection(browser.selection_runtime())
                browser.show("x", "identity-2")
        self.assertNotEqual(
            browser.load_selection(browser.selection_runtime())["token"],
            old["token"])
        self.assertFalse(browser.selection_is_current(
            "x", "identity-1", old["token"]))
        with patch.object(browser, "sway_tree", return_value=observed):
            with patch.object(browser, "sway_command") as command:
                with self.assertRaisesRegex(RuntimeError, "STALE_BROWSER_SELECTION"):
                    browser.current_sway_command(
                        "x", "identity-1", old["token"],
                        {"class": "post-apollo-x-identity-1", "conId": 11},
                        "scratchpad show")
                command.assert_not_called()

    def test_scoped_hide_only_hides_its_own_window(self):
        observed = sway_tree(
            browser_node("post-apollo-x-identity-1", 41),
            browser_node("post-apollo-x-identity-2", 42),
        )
        browser.claim_selection("x", "identity-2")
        calls = []
        with patch.object(browser, "sway_tree", return_value=observed):
            with patch.object(browser, "sway_command", side_effect=calls.append):
                browser.hide("x", "identity-1")
        self.assertEqual(calls, ['[con_id="41"] move scratchpad'])
        self.assertEqual(browser.load_selection(browser.selection_runtime())["identityId"],
                         "identity-2")

    def test_unsafe_profile_symlink_refused_before_launch(self):
        folder = self.root/"data/post-apollo"
        folder.mkdir(parents=True)
        outside = self.root/"outside"
        outside.mkdir()
        (folder/"identities").symlink_to(outside, target_is_directory=True)
        with patch.object(browser, "sway_tree", return_value=sway_tree()):
            with patch.object(browser, "browser_prefix",
                              return_value=["/usr/bin/chromium"]):
                with patch.object(browser.subprocess, "Popen") as spawn:
                    with self.assertRaisesRegex(RuntimeError,
                                                "Unsafe isolated profile directory"):
                        browser.show("x", "identity-1")
                    spawn.assert_not_called()
        self.assertEqual(list(outside.iterdir()), [])

    def test_unavailable_social_or_duplicate_class_blocks_before_claim(self):
        without_social = {"nodes": [browser_node("post-apollo-x-identity-2", 11)]}
        duplicate = sway_tree(browser_node("post-apollo-x-identity-2", 12),
                              browser_node("post-apollo-x-identity-2", 13))
        for observed in (without_social, duplicate):
            with patch.object(browser, "sway_tree", return_value=observed):
                with patch.object(browser.subprocess, "Popen") as spawn:
                    with self.assertRaises(RuntimeError):
                        browser.show("x", "identity-2")
                    spawn.assert_not_called()
        self.assertFalse((self.runtime/"post-apollo-social").exists())

    def test_invalid_identity_and_runtime_state_do_not_reveal_provider(self):
        with patch.object(browser.subprocess, "Popen") as spawn:
            for identity in ("../identity-1", "identity-0", "identity-1]"):
                with self.assertRaises(ValueError):
                    browser.show("x", identity)
            spawn.assert_not_called()
        self.runtime.chmod(0o755)
        with self.assertRaisesRegex(RuntimeError, "Unsafe browser runtime directory"):
            browser.claim_selection("x", "identity-1")
        self.assertFalse((self.runtime/"post-apollo-social").exists())

    def test_preceding_request_cannot_reveal_after_newer_claim(self):
        observed = sway_tree(browser_node("post-apollo-x-identity-1", 55))
        original = browser.claim_selection
        def supersede(site, identity):
            token = original(site, identity)
            original("x", "identity-2")
            return token
        with patch.object(browser, "sway_tree", return_value=observed):
            with patch.object(browser, "claim_selection", side_effect=supersede):
                with patch.object(browser, "sway_command") as cmd:
                    with self.assertRaisesRegex(RuntimeError, "STALE_BROWSER_SELECTION"):
                        browser.show("x", "identity-1")
                    cmd.assert_not_called()

    def test_scoped_geometry_requires_confirmed_con_id(self):
        bridge = geometry.Bridge(0.1)
        bridge.x_selected = True
        bridge.x_ready = True
        bridge.select_browser_scope("x", "identity-2")
        bridge.x_ready = True
        bridge.scoped_browser_con_id = 77
        message = {"target": "x", "browserIdentityId": "identity-2",
                   "windowClass": "post-apollo-x-identity-2",
                   "conId": 77, "x": 110, "y": 1,
                   "width": 700, "height": 600}
        bridge.queue_sync(message)
        self.assertEqual(bridge.pending_sync["x"]["scopeIdentity"], "identity-2")
        for wrong in (
            {"conId": 78}, {"browserIdentityId": "identity-1"},
            {"windowClass": "post-apollo-x-identity-1"},
            {"target": "social"},
        ):
            bridge.pending_sync.clear()
            bridge.queue_sync({**message, **wrong})
            self.assertEqual(bridge.pending_sync, {})
        bridge.select_browser_scope("x", "identity-3")
        self.assertEqual(bridge.pending_sync, {})

    def test_host_has_explicit_toggle_and_saved_identity_guard(self):
        for marker in (
            "browserIsolationEnabled: false",
            "function reconcilePersistedBrowserIdentity()",
            "if (!snapshot.writable || !validBrowserIdentity(snapshot.activeId)",
            "isolatedBrowserModeActive: messagingWindow.browserIsolationEnabled",
            "onIdentitySnapshotChanged:",
            "onIsolatedBrowserModeToggleRequested:",
            '"show", browserSite',
            'command.push("--identity", identity)',
            "xShowProcess.launchIdentityId !==",
            "payload.browserIdentityId = browserActiveIdentityId",
            "scopedBrowserConId = cid",
            "hideScopedIdentity(oldIdentity)",
        ):
            self.assertIn(marker, HOST)
        for marker in (
            'label: appSelector.isolatedBrowserModeActive',
            '"USE LEGACY BROWSERS" : "USE ISOLATED BROWSERS"',
            'signal isolatedBrowserModeToggleRequested()',
            'appSelector.isolatedBrowserModeToggleRequested()',
            'appSelector.identitySnapshot.writable',
        ):
            self.assertIn(marker, UI)

if __name__ == "__main__":
    unittest.main()
