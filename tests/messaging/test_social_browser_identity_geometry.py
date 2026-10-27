"""Passive identity-aware Sway geometry bridge contract.

This runs against the real DiscordGeometry.py in memory with synthetic Sway
trees. There is no live compositor, login provider, filesystem mutation,
browser process, or desktop deployment.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "widgets/messanger/DiscordGeometry.py"
BROWSER = ROOT / "widgets/messanger/XBrowser.py"
HOST = (ROOT / "widgets/messanger/MessagingW.qml").read_text()
IDENTITY_STORE = (ROOT / "services/social/SocialIdentityStore.qml").read_text()
spec = importlib.util.spec_from_file_location("scoped_geometry", BRIDGE)
assert spec and spec.loader
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
spec2 = importlib.util.spec_from_file_location("scoped_browser", BROWSER)
assert spec2 and spec2.loader
browser = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(browser)


def node(cls: str, cid: int, *, visible: bool = True, focused: bool = False,
         x: int = 120, width: int = 480):
    return {
        "window_properties": {"class": cls},
        "id": cid,
        "visible": visible,
        "focused": focused,
        "rect": {"x": x, "y": 21, "width": width, "height": 650},
    }


def tree(*children):
    return {"visible": True, "nodes": [
        {"visible": True, "name": "QS_SOCIAL_MENU",
         "rect": {"x": 10, "y": 20, "width": 690, "height": 650},
         "focused": False},
        *children,
    ]}


class GeometryIdentityBoundary(unittest.TestCase):
    def test_exact_window_class_agrees_with_existing_profile_boundary(self):
        for site in browser.ALL_SITES:
            self.assertEqual(g.browser_window_class(site),
                             browser.site_window_class(site))
            for identity in ("identity-1", "identity-2", "identity-999999999"):
                self.assertEqual(g.browser_window_class(site, identity),
                                 browser.site_window_class(site, identity))
        self.assertEqual(set(g.BROWSER_SITES), set(browser.ALL_SITES))

    def test_reject_invalid_identity_and_window_names_before_matching(self):
        invalid = ("", "default", "identity-0", "identity-01",
                   "identity-1000000000", "identity-1/../identity-2",
                   "identity-1\n", "identity-1]", "../identity-1",
                   'identity-2"] focus', True, 3, [], {})
        for identity in invalid:
            with self.subTest(identity=identity):
                with self.assertRaises(ValueError):
                    g.validate_browser_identity(identity)
                with self.assertRaises(ValueError):
                    g.browser_window_class("x", identity)
                with self.assertRaises(ValueError):
                    g.snapshot_from_tree(tree(), identity)
                with self.assertRaises(ValueError):
                    g.sway_criteria("x", 99, identity)
        with self.assertRaises(ValueError):
            g.browser_window_class("made-up-site", "identity-2")
        self.assertIsNone(g.validate_browser_identity(None))

    def test_hidden_scope_discovery_exact_identity_no_legacy_fallback(self):
        sample = tree(
            node("post-apollo-x", 10, focused=True),
            node("post-apollo-x-identity-1", 11, visible=False),
            node("post-apollo-x-identity-2", 12),
            node("post-apollo-reddit-identity-1", 13),
            node("post-apollo-reddit-identity-2", 14),
            node("post-apollo-x-identity-2-extra", 15),
        )
        first = g.snapshot_from_tree(sample, "identity-1")
        second = g.snapshot_from_tree(sample, "identity-2")
        legacy = g.snapshot_from_tree(sample)
        self.assertEqual(first["x"]["conId"], 11)
        self.assertFalse(first["x"]["visible"])
        self.assertEqual(first["x"]["browserIdentityId"], "identity-1")
        self.assertEqual(first["x"]["windowClass"], "post-apollo-x-identity-1")
        self.assertEqual(first["reddit"]["conId"], 13)
        self.assertEqual(second["x"]["conId"], 12)
        self.assertEqual(second["reddit"]["conId"], 14)
        self.assertEqual(legacy["x"]["rect"]["x"], 120)
        self.assertNotIn("conId", legacy["x"])
        self.assertNotIn("browserIdentityId", legacy["x"])
        self.assertIsNone(first["instagram"])
        self.assertIsNone(second["instagram"])

    def test_duplicate_scoped_class_and_unverified_container_fail_closed(self):
        same = tree(node("post-apollo-x-identity-2", 40),
                    node("post-apollo-x-identity-2", 41, width=999))
        self.assertIsNone(g.snapshot_from_tree(same, "identity-2")["x"])
        self.assertIsNotNone(g.snapshot_from_tree(same)["social"])
        for invalid_con_id in (None, 0, -1, "40", True):
            candidate = node("post-apollo-x-identity-2", 44)
            candidate["id"] = invalid_con_id
            self.assertIsNone(g.snapshot_from_tree(tree(candidate), "identity-2")["x"])

    def test_scoped_commands_require_class_and_verified_con_id(self):
        self.assertEqual(g.sway_criteria("x"),
                         '[class="post-apollo-x"]')
        self.assertEqual(g.sway_criteria("reddit", 81, "identity-2"),
                         '[con_id="81"]')
        with self.assertRaises(ValueError):
            g.sway_criteria("x", None, "identity-2")
        with self.assertRaises(ValueError):
            g.sway_criteria("x", 0, "identity-2")
        with self.assertRaises(ValueError):
            g.sway_criteria("x", True, "identity-2")
        with self.assertRaises(ValueError):
            g.sway_criteria("social", 81, "identity-2")
        with self.assertRaises(ValueError):
            g.sway_criteria("discord", 81, "identity-2")
        original = {
            "op": "sync", "target": "reddit", "conId": 81,
            "browserIdentityId": "identity-2",
            "windowClass": "post-apollo-reddit-identity-2",
            "x": 120, "y": 20, "width": 640, "height": 600, "focus": False,
        }
        command = g.build_sync_command(original)
        self.assertIn('[con_id="81"] resize set width 640 px', command)
        self.assertNotIn('post-apollo-reddit"', command)
        for alteration in (
            {"windowClass": "post-apollo-reddit-identity-1"},
            {"windowClass": "post-apollo-reddit"},
            {"target": "social"},
            {"target": "discord"},
            {"conId": None},
            {"conId": "81"},
            {"conId": -81},
        ):
            with self.subTest(alteration=alteration):
                with self.assertRaises(ValueError):
                    g.build_sync_command({**original, **alteration})
        self.assertIn('[class="post-apollo-reddit"]',
                      g.build_sync_command({**original,
                                            "browserIdentityId": None,
                                            "windowClass": "post-apollo-reddit"}))
        # Vesktop's real con_id requirement stays unchanged.
        self.assertEqual(g.sway_criteria("discord", 82), '[con_id="82"]')

    def test_scoped_transition_invalidates_readiness_pending_sync_and_old_focus(self):
        bridge = g.Bridge(0.1)
        bridge.x_selected = True
        bridge.x_ready = True
        bridge.x_docked = True
        bridge.pending_sync = {
            "x": {"target": "x"},
            "reddit": {"target": "reddit"},
            "social": {"target": "social"},
            "discord": {"target": "discord"},
        }
        bridge.immediate_commands.append('[class="post-apollo-x"] focus')
        bridge.immediate_commands.append('[con_id="900"] focus')
        bridge.select_browser_scope("x", "identity-2")
        self.assertEqual(bridge.browser_identity_id, "identity-2")
        self.assertFalse(bridge.x_ready)
        self.assertFalse(bridge.x_docked)
        self.assertIsNone(bridge.scoped_browser_con_id)
        self.assertEqual(list(bridge.pending_sync), ["discord"])
        self.assertEqual(list(bridge.immediate_commands), ['[con_id="900"] focus'])
        bridge.x_ready = True
        bridge.x_docked = True
        bridge.select_browser_scope("x", "identity-2")
        self.assertTrue(bridge.x_ready)  # A duplicate mode is not a new switch.
        bridge.select_browser_scope("x", "identity-3")
        self.assertFalse(bridge.x_ready)
        self.assertFalse(bridge.x_docked)
        self.assertEqual(bridge.browser_identity_id, "identity-3")
        bridge.select_browser_scope("x", None)
        self.assertIsNone(bridge.browser_identity_id)
        self.assertFalse(bridge.x_ready)

    def test_switching_legacy_sites_remains_unchanged(self):
        bridge = g.Bridge(0.1)
        bridge.x_ready = True
        bridge.x_docked = True
        bridge.pending_sync["social"] = {"target": "social"}
        bridge.select_browser_scope("reddit", None)
        self.assertEqual(bridge.browser_site, "reddit")
        self.assertTrue(bridge.x_ready)
        self.assertTrue(bridge.x_docked)
        self.assertIn("social", bridge.pending_sync)
        bridge.select_browser_scope("invalid-site", None)
        self.assertEqual(bridge.browser_site, "x")

    def test_scoped_selection_never_moves_a_provider_or_host(self):
        bridge = g.Bridge(0.1)
        bridge.x_selected = True
        bridge.select_browser_scope("x", "identity-2")
        bridge.x_ready = True
        bridge.x_docked = True
        movements = []
        bridge.queue_sync = movements.append
        snapshot = {
            "social": {"rect": {"x": 1, "y": 2, "width": 600, "height": 700},
                       "focused": False},
            "x": {"rect": {"x": 120, "y": 2, "width": 480, "height": 700},
                  "conId": 23, "browserIdentityId": "identity-2",
                  "windowClass": "post-apollo-x-identity-2",
                  "focused": True, "visible": True},
        }
        result = bridge.fast_follow(snapshot)
        self.assertIsNone(result["fastLeader"])
        self.assertIsNone(result["shared"])
        self.assertEqual(movements, [])
        # Call the real guarded implementation rather than the spy.
        del bridge.queue_sync
        bridge.queue_sync({"target":"x","x":0,"y":0,"width":100,"height":100})
        bridge.queue_sync({"target":"social","x":0,"y":0,"width":100,"height":100})
        bridge.queue_sync({"target":"x","browserIdentityId":"identity-2",
                           "x":0,"y":0,"width":100,"height":100})
        self.assertEqual(bridge.pending_sync,{})
        bridge.queue_sync({"target":"discord","x":0,"y":0,"width":100,"height":100})
        self.assertEqual(bridge.pending_sync,{})  # Unknown Discord con_id.

    def test_scope_only_snapshot_output_and_con_id_change_invalidate_docking(self):
        bridge = g.Bridge(0.1)
        bridge.x_selected = True
        bridge.select_browser_scope("x", "identity-2")
        record = tree(
            node("post-apollo-x", 40, focused=True),
            node("post-apollo-x-identity-2", 51, visible=False),
            node("post-apollo-x-identity-1", 52),
        )
        bridge.poll_ipc.request = lambda _op: record
        with contextlib.redirect_stdout(io.StringIO()) as output:
            bridge.emit_snapshot(force=True)
        payload=json.loads(output.getvalue().strip())
        self.assertEqual(payload["x"]["conId"], 51)
        self.assertFalse(payload["x"]["visible"])
        self.assertEqual(payload["x"]["browserIdentityId"], "identity-2")
        self.assertEqual(bridge.scoped_browser_con_id, 51)
        bridge.x_ready = True
        bridge.x_docked = True
        record["nodes"][2]["id"] = 53
        with contextlib.redirect_stdout(io.StringIO()):
            bridge.emit_snapshot(force=True)
        self.assertEqual(bridge.scoped_browser_con_id, 53)
        self.assertFalse(bridge.x_ready)
        self.assertFalse(bridge.x_docked)
        bridge.x_ready = True
        bridge.x_docked = True
        record["nodes"][2]["window_properties"]["class"] = "post-apollo-x-identity-1"
        with contextlib.redirect_stdout(io.StringIO()):
            bridge.emit_snapshot(force=True)
        self.assertIsNone(bridge.scoped_browser_con_id)
        self.assertFalse(bridge.x_ready)
        self.assertFalse(bridge.x_docked)

    def test_invalid_mode_stays_on_previous_identity_without_legacy_fallback(self):
        bridge = g.Bridge(0.1)
        bridge.select_browser_scope("reddit", "identity-2")
        lines = "\n".join([
            json.dumps({"op":"mode","browserIdentityId":"../identity-1",
                        "browserSite":"x","xReady":True}),
            json.dumps({"op":"mode","browserIdentityId":"identity-3",
                        "browserSite":"no-such-site","xReady":True}),
            "",
        ])
        with patch("sys.stdin", io.StringIO(lines)):
            with contextlib.redirect_stderr(io.StringIO()):
                bridge.stdin_loop()
        self.assertEqual(bridge.browser_site, "reddit")
        self.assertEqual(bridge.browser_identity_id, "identity-2")
        self.assertFalse(bridge.x_ready)

    def test_scoped_focus_refused_legacy_focus_kept(self):
        bridge = g.Bridge(0.1)
        bridge.select_browser_scope("x", "identity-1")
        with patch("sys.stdin", io.StringIO('{"op":"focusX"}\n')):
            bridge.stdin_loop()
        self.assertEqual(list(bridge.immediate_commands), [])
        self.assertTrue(bridge.sample_event.is_set())
        bridge.sample_event.clear()
        bridge.select_browser_scope("x", None)
        with patch("sys.stdin", io.StringIO('{"op":"focusX"}\n')):
            bridge.stdin_loop()
        self.assertEqual(list(bridge.immediate_commands),
                         ['[class="post-apollo-x"] focus'])

    def test_no_host_automatic_scope_activation(self):
        self.assertIn('function showX()', HOST)
        self.assertIn('function hideX()', HOST)
        self.assertIn('"show", browserSite', HOST)
        self.assertNotIn('"show", browserSite, "--identity"', HOST)
        self.assertIn("function selectIdentity(id)", IDENTITY_STORE)
        self.assertNotIn("browserIdentityId: appSelector.identitySnapshot.activeId",
                         HOST)
        self.assertIn("Identity-scoped browser launch awaits geometry integration",
                      BROWSER.read_text())

if __name__ == "__main__":
    unittest.main()
