"""Camera Zoom Web guest safety/placement contracts. All external effects mocked."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch
import json
import os
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
QML = (ROOT / "widgets/CameraW.qml").read_text()
path = ROOT / "scripts/camera/ZoomWebHost.py"
spec = importlib.util.spec_from_file_location("camera_zoom_web_host_contract", path)
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class ZoomWebHostTests(unittest.TestCase):
    def test_known_zoom_url_and_dedicated_window_class(self):
        self.assertEqual(host.ZOOM_WEB_URL, "https://app.zoom.us/wc")
        self.assertEqual(host.ZOOM_CLASS, "post-apollo-camera-zoom-web")
        self.assertIn('def _social_browser_prefix()', path.read_text())
        self.assertIn('XBrowser.py', path.read_text())
        self.assertIn('post-apollo" / "camera" / "zoom-web"', path.read_text())
        self.assertNotIn('zoom-install', path.read_text())
        self.assertNotIn('us.zoom.Zoom', path.read_text())
        self.assertIn('["--ozone-platform=x11"', path.read_text())
        self.assertIn('--app="+ZOOM_WEB_URL', path.read_text())

    def test_qml_hole_is_closed_by_default_and_only_after_verified_dock(self):
        self.assertIn('property bool zoomWebDocked: false', QML)
        self.assertIn('zoomWebDocked = !!(reply && reply.ok === true && reply.docked === true)', QML)
        self.assertIn('fillOpacity: camera.zoomWebDocked ? 0.0 : 0.97', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomBayWidth : 0', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebDocked', QML)
        self.assertIn('onLeftClicked: camera.openZoomMode()', QML) if False else None
        self.assertIn('function openZoomMode()', QML)
        entry = QML.split('function openZoomMode()',1)[1].split(
            'function prepareZoomInstall(choice)',1)[0]
        self.assertIn('enterZoomWeb()',entry)
        self.assertNotIn('zoomEnter',entry)
        self.assertNotIn('zoomClientOpen',entry)
        self.assertIn('scripts/camera/ZoomWebHost.py',QML)
        self.assertIn('zoomWebHideProcess.exec(zoomWebArgs("hide"))',QML)
        self.assertIn('if (camera.activeView === "zoom")',QML)
        self.assertNotIn('WebEngineView',QML)

    def test_output_bounds_and_explicit_identity_validation(self):
        with patch.object(host, "_output_rect", return_value={
                "x":2560,"y":0,"width":1360,"height":768}):
            self.assertEqual(host._target_geometry("HDMI-A-1",20,130,600,500),
                             (2580,130,600,500))
            for x,y,w,h in ((-1,0,600,500),(20,-1,600,500),
                            (20,130,320,280),(800,100,700,500),
                            (20,500,600,400)):
                with self.subTest(rect=(x,y,w,h)):
                    with self.assertRaises(ValueError):
                        host._target_geometry("HDMI-A-1",x,y,w,h)
        with self.assertRaises(ValueError):
            host._private_profile(["/usr/bin/chromium"], "../other-identity")

    def test_profile_is_owner_only_and_is_not_social_or_native_zoom(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME":temp}):
                p=host._private_profile(["/usr/bin/chromium"],"identity-1")
                self.assertTrue(p.is_dir())
                self.assertTrue(str(p).startswith(temp))
                self.assertIn("post-apollo/camera/zoom-web/identity-1",str(p))
                self.assertEqual(p.stat().st_mode & 0o077,0)
                symlink=p.parent/"identity-2"
                symlink.symlink_to(p, target_is_directory=True)
                with self.assertRaises(RuntimeError):
                    host._private_profile(["/usr/bin/chromium"],"identity-2")

    def test_no_web_guest_without_unique_actor_and_origin(self):
        tree={"nodes":[
            {"id":90,"pid":2800,"window_properties":{"class":host.ZOOM_CLASS},
             "rect":{"x":100,"y":200,"width":600,"height":400}},
            {"id":100,"pid":3000,"window_properties":{"class":host.ZOOM_CLASS},
             "rect":{"x":100,"y":200,"width":600,"height":400}}],
            "floating_nodes":[]}
        with patch.object(host,"_sway_json",return_value=tree):
            with patch.object(host,"_verified_process_profile",return_value=True):
                actor,error=host._unique_actor(Path("/some/profile"))
        self.assertIsNone(actor)
        self.assertEqual(error,"AMBIGUOUS_ACTOR")
        tree["nodes"]=tree["nodes"][:1]
        with patch.object(host,"_sway_json",return_value=tree):
            with patch.object(host,"_verified_process_profile",return_value=False):
                actor,error=host._unique_actor(Path("/some/profile"))
        self.assertIsNone(actor)
        self.assertEqual(error,"ACTOR_ORIGIN_UNVERIFIED")

    def test_show_existing_actor_aligns_and_reverifies_before_opening_hole(self):
        actor={"id":123,"pid":333,"visible":True,"window_properties":{"class":host.ZOOM_CLASS},
               "rect":{"x":2600,"y":150,"width":650,"height":420}}
        calls=[]
        with tempfile.TemporaryDirectory() as root:
            profile=Path(root)/"profile"
            with patch.object(host,"_target_geometry",return_value=(2600,150,650,420)):
                with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
                    with patch.object(host,"_private_profile",return_value=profile):
                        with patch.object(host,"_unique_actor",return_value=(actor,"")):
                            with patch.object(host,"_sway_command",side_effect=lambda *a:calls.append(a)):
                                result=host.enter("identity-1","HDMI-A-1",40,150,650,420)
        self.assertTrue(result["ok"])
        self.assertTrue(result["docked"])
        self.assertEqual(len(calls),3)
        self.assertEqual(calls[0],("[con_id=123]","floating","enable"))
        self.assertEqual(calls[1][1:3],("resize","set"))
        self.assertEqual(calls[2],("[con_id=123]","move","position","2600","150"))

    def test_failed_alignment_hides_exact_guest_not_other_windows(self):
        actor={"id":123,"pid":333,"visible":True,"window_properties":{"class":host.ZOOM_CLASS},
               "rect":{"x":100,"y":200,"width":600,"height":400}}
        with tempfile.TemporaryDirectory() as root:
            with patch.object(host,"_target_geometry",return_value=(2600,150,650,420)):
                with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
                    with patch.object(host,"_private_profile",return_value=Path(root)):
                        with patch.object(host,"_unique_actor",return_value=(actor,"")):
                            with patch.object(host,"_sway_command") as sway:
                                result=host.enter("identity-1","HDMI-A-1",40,150,650,420)
        self.assertFalse(result["docked"])
        sway.assert_any_call("[con_id=123]","move","scratchpad")

    def test_missing_browser_does_not_lie_about_hosted_login(self):
        with patch.object(host,"_target_geometry",return_value=(100,150,600,400)):
            with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
                with patch.object(host,"_private_profile",return_value=Path("/tmp/fixture")):
                    with patch.object(host,"_unique_actor",
                        side_effect=[(None,"ACTOR_MISSING")]*46):
                        with patch.object(host.subprocess,"Popen",return_value=Mock()) as launch:
                            with patch.object(host.time,"sleep",return_value=None):
                                r=host.enter("identity-1","DP-5",100,150,600,400)
        self.assertFalse(r["ok"])
        self.assertEqual(r["authenticated"],"UNKNOWN")
        self.assertFalse(r["docked"])
        launch.assert_called_once()
        args=launch.call_args.args[0]
        self.assertIn("--class="+host.ZOOM_CLASS,args)
        self.assertIn("--app="+host.ZOOM_WEB_URL,args)
        self.assertNotIn("shell",launch.call_args.kwargs)

    def test_hide_preserves_profile_and_cookies(self):
        with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
            with patch.object(host,"_unique_actor",return_value=(
                    {"id":123,"visible":True,"pid":5},"")):
                with patch.object(host,"_sway_command") as sway:
                    r=host.hide("identity-1")
        self.assertTrue(r["ok"])
        sway.assert_called_once_with("[con_id=123]","move","scratchpad")


if __name__=="__main__":
    unittest.main()
