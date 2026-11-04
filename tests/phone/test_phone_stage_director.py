"""PHONE Stage Director: scope to one exact foot terminal and observed Sway fit."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

PATH = (Path(__file__).resolve().parents[2] / "services/phone"
        / "PhoneStageDirector.py")
SPEC = importlib.util.spec_from_file_location("social_phone_stage", PATH)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


def tree(*, app_id=stage.STAGE_APP_ID, foot_pid=4321, foot_id=9901,
         foot_executable="foot", social_name=stage.SOCIAL_TITLE,
         social_visible=True, actual=None, foot_visible=True, duplicate=False):
    social = {
        "name": social_name,
        "visible": social_visible,
        "rect": {"x": 700, "y": 40, "width": 900, "height": 700},
        "nodes": [], "floating_nodes": [],
    }
    foot = {
        "id": foot_id, "pid": foot_pid, "app_id": app_id,
        "visible": foot_visible,
        "rect": actual or {"x": 1090, "y": 370, "width": 480, "height": 300},
        "window_rect": {"x": 0, "y": 0, "width": 480, "height": 300},
        "nodes": [], "floating_nodes": [],
    }
    children = [social, foot]
    if duplicate:
        children.append({**foot, "id": foot_id + 1})
    return {"nodes": children, "floating_nodes": []}


class PhoneStageTests(unittest.TestCase):
    def locked(self, result):
        self.assertEqual(result["schema"], stage.SCHEMA)
        self.assertEqual(result["execution"], "STAGE_ONLY")
        self.assertEqual(result["trustedPhoneLink"], "UNVERIFIED")
        self.assertIs(result["contentAccessEnabled"], False)
        self.assertIs(type(result["verifiedHole"]), bool)
        self.assertEqual(set(result), {
            "schema", "execution", "state", "verifiedHole",
            "trustedPhoneLink", "contentAccessEnabled",
        })

    def test_exact_foot_actor_moves_only_to_social_local_bay(self):
        execute = Mock()
        result = stage.operation("sync", local=(390, 330, 470, 290),
                                 tree=tree(), executable=lambda pid: "foot",
                                 execute=execute)
        self.locked(result)
        self.assertEqual(result["state"], "POSITION_REQUESTED")
        self.assertFalse(result["verifiedHole"])
        execute.assert_called_once_with(
            "[con_id=9901] floating enable, border none, "
            "resize set width 470 px height 290 px, "
            "move absolute position 1090 px 370 px"
        )

    def test_only_observed_exact_content_opens_cutout(self):
        execute = Mock()
        target = {"x": 1090, "y": 370, "width": 470, "height": 290}
        t = tree(actual=target)
        t["nodes"][1]["window_rect"] = {
            "x": 0, "y": 0, "width": 470, "height": 290}
        result = stage.operation("sync", local=(390, 330, 470, 290),
                                 tree=t, executable=lambda pid: "foot",
                                 execute=execute)
        self.locked(result)
        self.assertEqual(result["state"], "ALIGNED")
        self.assertTrue(result["verifiedHole"])
        execute.assert_not_called()

    def test_partial_or_stale_window_never_claims_stage_cutout(self):
        execute = Mock()
        t = tree(actual={"x": 1090, "y": 370, "width": 470, "height": 290})
        t["nodes"][1]["window_rect"] = {
            "x": 4, "y": 4, "width": 450, "height": 280}
        result = stage.operation("sync", local=(390, 330, 470, 290),
                                 tree=t, executable=lambda pid: "foot",
                                 execute=execute)
        self.locked(result)
        self.assertEqual(result["state"], "POSITION_REQUESTED")
        self.assertFalse(result["verifiedHole"])
        execute.assert_called_once()

    def test_no_other_foot_process_or_browser_window_moved(self):
        cases = (
            tree(app_id="foot"),
            tree(social_name="OTHER"),
            tree(social_visible=False),
            tree(duplicate=True),
            tree(foot_visible=False),
        )
        for data in cases:
            with self.subTest(data=data):
                execute = Mock()
                result = stage.operation(
                    "sync", local=(390, 330, 470, 290),
                    tree=data, executable=lambda pid: "foot",
                    execute=execute)
                self.locked(result)
                self.assertNotEqual(result["state"], "ALIGNED")
                execute.assert_not_called()

    def test_unrelated_executable_cannot_be_moved_or_closed(self):
        t = tree()
        execute = Mock()
        for action in ("sync", "close"):
            result = stage.operation(action, local=(390, 330, 470, 290),
                                     tree=t,
                                     executable=lambda pid: "kitty",
                                     execute=execute)
            self.locked(result)
            self.assertEqual(result["state"], "ACTOR_NOT_FOUND")
        execute.assert_not_called()

    def test_outside_social_window_refuses_to_move(self):
        t = tree()
        execute = Mock()
        for local in ((390, 330, 510, 290), (0, 650, 400, 120),
                      (-1, 100, 250, 250), (0, 0, 199, 200),
                      (0, 0, 300, 100), (10, 20, 0, 200),
                      (True, 20, 400, 250), (1.0, 20, 400, 250),
                      ("100", 20, 400, 250), None):
            with self.subTest(local=local):
                result = stage.operation(
                    "sync", local=local, tree=t,
                    executable=lambda pid: "foot", execute=execute)
                self.locked(result)
                self.assertEqual(result["state"], "REFUSED")
        execute.assert_not_called()

    def test_close_only_own_exact_actor_after_user_exits_setup(self):
        execute = Mock()
        result = stage.operation("close", tree=tree(),
                                 executable=lambda pid: "foot",
                                 execute=execute)
        self.locked(result)
        self.assertEqual(result["state"], "CLOSE_REQUESTED")
        execute.assert_called_once_with("[con_id=9901] kill")

    def test_sway_error_does_not_open_cutout_or_leak_private_window_text(self):
        result = stage.operation(
            "sync", local=(390, 330, 470, 290),
            tree=tree(), executable=lambda pid: "foot",
            execute=Mock(side_effect=ValueError("PRIVATE PHONE")),
        )
        self.locked(result)
        self.assertEqual(result["state"], "UNAVAILABLE")
        self.assertNotIn("PRIVATE", str(result))

    def test_absent_tree_will_not_target_arbitrary_window(self):
        execute = Mock()
        result = stage.operation("sync", local=(390, 330, 470, 290),
                                 tree={}, execute=execute)
        self.locked(result)
        self.assertEqual(result["state"], "ACTOR_NOT_FOUND")
        execute.assert_not_called()

    def test_no_implicit_console_or_pairing_command(self):
        script = PATH.read_text()
        for name in ("pair-setup", "bluetoothctl", "systemctl start",
                     "subprocess.Popen(", "shell=True",
                     "os.system(", "getMessages(", "sendMessage("):
            with self.subTest(name=name):
                self.assertNotIn(name, script)


if __name__ == "__main__":
    unittest.main()
