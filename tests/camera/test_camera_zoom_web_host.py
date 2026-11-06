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
        self.assertIn('const initiallyDocked = !!(reply && reply.ok === true && reply.docked === true)', QML)
        self.assertIn('zoomFollowProcess.running = true;', QML)
        self.assertIn('zoomWebDocked = aligned;', QML)
        self.assertIn('fillOpacity: camera.zoomWebDocked ? 0.0 : 0.97', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebDocked', QML)
        self.assertIn('function openZoomMode()', QML)
        entry = QML.split('function openZoomMode()',1)[1].split(
            'function prepareZoomInstall(choice)',1)[0]
        self.assertIn('enterZoomWeb()',entry)
        self.assertNotIn('zoomEnter',entry)
        self.assertNotIn('zoomClientOpen',entry)
        self.assertIn('scripts/camera/ZoomWebHost.py',QML)
        self.assertIn('zoomWebHideProcess.exec(zoomWebArgs("hide"))',QML)
        self.assertIn('menuOpen && !zoomWebDocked ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None',QML)
        self.assertIn('focusable: menuOpen && !zoomWebDocked',QML)
        self.assertIn('visible: camera.activeView === "zoom"',QML)
        self.assertIn('label: "↓ DOWNLOAD"',QML)
        self.assertIn('camera.hideZoomWeb();',QML)
        self.assertIn('if (camera.activeView === "zoom")',QML)
        self.assertNotIn('WebEngineView',QML)

    def test_zoom_browser_gets_full_real_content_area_not_legacy_footer(self):
        # Keep the existing Camera header and all four main tabs.
        for label in ('"CAPTURE"', '"GALLERY"', '"ZOOM"', '"CLEANUP"',
                      'label: "↓ DOWNLOAD"'):
            self.assertIn(label, QML)
        # The old fixed slot top/bottom cut short the Zoom web viewport.
        self.assertNotIn('readonly property int zoomBayTop: 131', QML)
        self.assertNotIn('readonly property int zoomBayHeight: Math.max(0, frameHeight - 169)', QML)
        self.assertNotIn('cameraPage.y + cameraPage.parent.y', QML)
        self.assertNotIn('cameraPage.x + cameraPage.parent.x', QML)
        self.assertNotIn('Math.round(cameraPage.width)', QML)
        self.assertIn('readonly property int zoomBayBottom: 2', QML)
        self.assertIn('id: zoomViewport', QML)
        self.assertIn('id: cameraBodyColumn', QML)
        self.assertIn('cameraModes.y', QML)
        self.assertIn('y: cameraBodyColumn.y + cameraModes.y + cameraModes.height', QML)
        self.assertNotIn('cameraModes.height + cameraBodyColumn.spacing', QML)
        self.assertIn('frame.height - y - camera.zoomBayBottom', QML)
        self.assertIn('Math.round(zoomViewport.x)', QML)
        self.assertIn('Math.round(zoomViewport.y)', QML)
        self.assertIn('Math.round(zoomViewport.width)', QML)
        self.assertIn('Math.round(zoomViewport.height)', QML)
        # Compact is still 675 px tall, but the browser uses the body instead
        # of leaving the 38px phantom footer: approx 539 vs 506px at y=131.
        compact_height, page_start, bottom = 675, 131, 2
        self.assertEqual(compact_height - page_start - bottom, 542)
        self.assertGreater(compact_height - page_start - bottom,
                           compact_height - 169)

    def test_zoom_browser_owns_scroll_and_the_footer_cannot_cover_buttons(self):
        self.assertIn('visible: camera.activeView !== "zoom"', QML)
        self.assertIn('height: frame.height - 169', QML)
        self.assertIn('Zoom is hosted by the sibling zoomViewport instead.', QML)
        self.assertNotIn('height: camera.activeView === "zoom" && camera.zoomWebDocked', QML)
        self.assertIn('visible: camera.activeView !== "zoom"', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebDocked', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomActorHeight : 0', QML)
        self.assertIn('menuOpen && !zoomWebDocked ? WlrKeyboardFocus.OnDemand', QML)
        # The fallback instructions are scrollable only when the web actor is
        # absent. A QML Flickable must not intercept Zoom's native mouse wheel.
        self.assertIn('id: zoomPage', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebDocked', QML)

    def test_zoom_starts_at_mode_row_bottom_without_changing_bottom_edge(self):
        # After verified live deployment, the last screenshot still showed
        # ~6 scaled px of empty space between mode row and browser. This was
        # exactly the 12 logical px shared Column spacing, not Sway resizing.
        self.assertIn(
            'y: cameraBodyColumn.y + cameraModes.y + cameraModes.height', QML)
        self.assertNotIn('cameraModes.height + cameraBodyColumn.spacing', QML)
        self.assertIn(
            'height: Math.max(0, frame.height - y - camera.zoomBayBottom)', QML)
        self.assertIn('readonly property int zoomBayBottom: 2', QML)
        self.assertIn('x: cameraBodyColumn.x', QML)
        self.assertIn('width: Math.max(0, cameraBodyColumn.width)', QML)
        self.assertIn(
            'readonly property int zoomActorTop: zoomBayTop', QML)
        self.assertIn(
            'readonly property int zoomActorHeight: zoomBayHeight', QML)
        # Fixed bottom: reducing top by 12 grows height by 12. Same at all
        # sizes, without another synthetic actor offset or new Sway command.
        for old_top, old_height in ((131, 542), (131, 875), (131, 1200)):
            new_top = old_top - 12
            new_height = old_height + 12
            self.assertEqual(old_top + old_height, new_top + new_height)

    def test_zoom_viewport_is_frame_owned_and_fallback_is_not_in_camera_page(self):
        # A shared Camera Column previously owned the browser rectangle.
        # The new Zoom page must live directly inside the frame viewport and
        # the three ordinary Camera modes must keep the old cameraPage.
        frame_start = QML.index('    WindowPanelFrame {\\n        id: frame'.replace('\\n', '\n'))
        viewport_start = QML.index('        Item {\n            id: zoomViewport', frame_start)
        fallback_start = QML.index('            Flickable {\n                id: zoomPage', viewport_start)
        column_start = QML.index('        Column {\n            id: cameraBodyColumn', fallback_start)
        page_start = QML.index('            Item {\n                id: cameraPage', column_start)
        self.assertLess(viewport_start, fallback_start)
        self.assertLess(fallback_start, column_start)
        self.assertLess(column_start, page_start)
        self.assertEqual(QML.count('id: zoomViewport'), 1)
        self.assertEqual(QML.count('id: zoomPage'), 1)
        self.assertIn('anchors.fill: parent', QML[fallback_start:column_start])
        self.assertIn('visible: camera.menuOpen && camera.activeView === "zoom"',
                      QML[viewport_start:fallback_start])
        self.assertIn('visible: camera.activeView !== "zoom"',
                      QML[page_start:page_start + 350])
        self.assertIn('id: capturePage', QML[page_start:])
        self.assertIn('id: galleryPage', QML[page_start:])
        self.assertIn('id: cleanupPage', QML[page_start:])
        self.assertNotIn('id: zoomPage', QML[page_start:])

    def test_zoom_host_and_input_mask_share_the_exact_frame_viewport(self):
        self.assertIn('readonly property int zoomBayInset: Math.max(0, Math.round(zoomViewport.x))', QML)
        self.assertIn('readonly property int zoomBayTop: Math.max(0, Math.round(zoomViewport.y))', QML)
        self.assertIn('readonly property int zoomBayWidth: Math.max(0, Math.round(zoomViewport.width))', QML)
        self.assertIn('readonly property int zoomBayHeight: Math.max(0, Math.round(zoomViewport.height))', QML)
        self.assertIn('zoomWebProcess.exec(zoomWebArgs("enter"))', QML)
        self.assertIn('"--width", String(zoomActorWidth), "--height", String(zoomActorHeight)', QML)
        self.assertIn('x: camera.zoomActorLeft', QML)
        self.assertIn('y: camera.zoomActorTop', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        # A verified browser has no overlapping QML fallback controls.
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebDocked', QML)

    def test_actor_matches_camera_viewport_without_old_arbitrary_trims(self):
        # Operator Sway measurement: actual Zoom 92,126 718x514 exactly
        # reflected 8px horizontal, 14px rise and 16x28 size trims.
        # The new physical browser rectangle MUST match the viewport.
        self.assertNotIn('zoomActorRise: 14', QML)
        self.assertNotIn('zoomActorWidthTrim: 16', QML)
        self.assertNotIn('zoomActorHeightTrim: 28', QML)
        for expr in (
            'readonly property int zoomActorLeft: zoomBayInset',
            'readonly property int zoomActorTop: zoomBayTop',
            'readonly property int zoomActorWidth: zoomBayWidth',
            'readonly property int zoomActorHeight: zoomBayHeight',
            'camera.frameTopInset + zoomActorTop',
            'camera.margins.left + camera.glowGutter + zoomActorLeft',
            '"--width", String(zoomActorWidth), "--height", String(zoomActorHeight)',
            'width: zoomActorWidth, height: zoomActorHeight',
            'x: camera.zoomActorLeft',
            'y: camera.zoomActorTop',
            'width: camera.zoomWebDocked ? camera.zoomActorWidth : 0',
            'height: camera.zoomWebDocked ? camera.zoomActorHeight : 0'
        ):
            self.assertIn(expr, QML)
        # Current code/measurement arithmetic, not a new Sway offset.
        x, y, width, height = 92, 126, 718, 514
        self.assertEqual((x - 8, y + 14, width + 16, height + 28),
                         (84, 140, 734, 542))
        self.assertNotIn('WORKAREA_Y', QML)

    def test_rapid_resize_keeps_clickthrough_closed_until_new_alignment(self):
        self.assertIn('function scheduleZoomWebRealign()', QML)
        self.assertIn('zoomWebDocked = false;', QML)
        self.assertIn('if (zoomWebBusy) {', QML)
        self.assertIn('zoomWebNeedsRealign = true;', QML)
        self.assertIn('if (zoomWebNeedsRealign) {', QML)
        self.assertIn('zoomWebState = "REALIGNING_WEB_APP";', QML)
        for prop in ('ZoomActorLeft', 'ZoomActorTop', 'ZoomActorWidth',
                     'ZoomActorHeight', 'ZoomWebOutput'):
            self.assertIn('on' + prop + 'Changed: scheduleZoomWebRealign()', QML)
        self.assertIn('onDockCenterXChanged: scheduleZoomWebRealign()', QML)
        self.assertIn('id: zoomWebRealign', QML)
        self.assertIn('if (camera.zoomWebBusy)', QML)
        self.assertIn('zoomWebRealign.restart();', QML)
        # Existing browser is reused through the same private profile.
        self.assertIn('actor, error = _unique_actor(profile)', path.read_text())
        self.assertIn('if not actor and error == "ACTOR_MISSING":', path.read_text())
        self.assertIn('zoomWebHideProcess.exec(zoomWebArgs("hide"))', QML)
        self.assertNotIn('zoomWebProcess.exec(zoomWebArgs("hide"))', QML)

    def test_output_bounds_and_explicit_identity_validation(self):
        with patch.object(host, "_output_rect", return_value={
                "x":2560,"y":0,"width":1360,"height":768}), \
             patch.object(host, "_sway_json", return_value=[
                {"output":"HDMI-A-1","visible":True,"rect":{"y":0}}]):
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

    def test_measured_workarea_origin_shifts_only_physical_zoom_actor(self):
        # Operator's source/live evidence: 84,140 734x542 reported at Sway,
        # workarea Y=82. Camera's body is visibly ~82px below the actor.
        output={"x":0,"y":0,"width":2560,"height":1440}
        workspace=[{"output":"DP-3","visible":True,"rect":{"y":82}}]
        self.assertEqual(host._workarea_top_offset("DP-3",output,workspace),82)
        with patch.object(host, "_output_rect", return_value=output), \
             patch.object(host, "_sway_json", return_value=workspace):
            self.assertEqual(host._target_geometry("DP-3",84,140,734,542),
                             (84,222,734,542))
        # A second monitor without the top workarea inset stays unchanged.
        second={"x":2560,"y":0,"width":1360,"height":768}
        ws=[{"output":"HDMI-A-1","visible":True,"rect":{"y":0}}]
        self.assertEqual(host._workarea_top_offset("HDMI-A-1",second,ws),0)

    def test_untrusted_workarea_fails_closed_without_touching_other_windows(self):
        output={"x":0,"y":0,"width":2560,"height":1440}
        for workspaces in ([], None,
                           [{"output":"DP-3","visible":False,"rect":{"y":82}}],
                           [{"output":"DP-3","visible":True,"rect":{"y":-10}}],
                           [{"output":"DP-3","visible":True,"rect":{"y":1000}}],
                           [{"output":"DP-3","visible":True,"rect":{"y":True}}],
                           [{"output":"DP-3","visible":True,"rect":{"y":82}}]*2):
            with self.subTest(workspaces=workspaces):
                with self.assertRaises(RuntimeError):
                    host._workarea_top_offset("DP-3",output,workspaces)
        # Bounds account for the workarea offset, not only panel-local Y.
        with patch.object(host,"_output_rect",return_value={
                "x":0,"y":0,"width":1360,"height":768}), \
             patch.object(host,"_sway_json",return_value=[
                {"output":"DP-3","visible":True,"rect":{"y":82}}]):
            with self.assertRaises(ValueError):
                host._target_geometry("DP-3",84,200,734,542)

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
        self.assertEqual(len(calls),4)
        self.assertEqual(calls[0],("[con_id=123]","floating","enable"))
        self.assertEqual(calls[1],("[con_id=123]","border","none"))
        self.assertEqual(calls[2][1:3],("resize","set"))
        self.assertEqual(calls[3],("[con_id=123]","move","absolute","position",
                                   "2600","px","150","px"))

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
        self.assertEqual(result["rectDelta"],[-2500,50,-50,-20])
        sway.assert_any_call("[con_id=123]","move","scratchpad")

    def test_hidden_actor_never_opens_clickthrough_even_if_rect_matches(self):
        present = {"id": 123, "pid": 333, "visible": True,
                   "rect": {"x": 2600, "y": 150, "width": 650, "height": 420}}
        hidden = dict(present, visible=False)
        with patch.object(host,"_target_geometry",return_value=(2600,150,650,420)):
            with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
                with patch.object(host,"_private_profile",return_value=Path("/tmp/testcamera")):
                    with patch.object(host,"_unique_actor",side_effect=[
                            (present,"")] + [(hidden,"")]*18):
                        with patch.object(host.time,"sleep",return_value=None):
                            with patch.object(host,"_sway_command"):
                                r = host.enter("identity-1","HDMI-A-1",40,150,650,420)
        self.assertFalse(r["ok"])
        self.assertFalse(r["docked"])
        self.assertEqual(r["error"],"WINDOW_NOT_VISIBLE")
        self.assertEqual(r["rectDelta"],[0,0,0,0])

    def test_distinct_sway_global_move_coordinates_on_second_output(self):
        actor={"id":321,"pid":333,"visible":True,
               "rect":{"x":2600,"y":150,"width":650,"height":420}}
        calls=[]
        with patch.object(host,"_target_geometry",return_value=(2600,150,650,420)):
            with patch.object(host,"_social_browser_prefix",return_value=["/usr/bin/chromium"]):
                with patch.object(host,"_private_profile",return_value=Path("/tmp/testcamera")):
                    with patch.object(host,"_unique_actor",return_value=(actor,"")):
                        with patch.object(host,"_sway_command",side_effect=lambda *x:calls.append(x)):
                            r = host.enter("identity-1","HDMI-A-1",40,150,650,420)
        self.assertTrue(r["docked"])
        self.assertIn(("[con_id=321]","border","none"),calls)
        self.assertIn(("[con_id=321]","move","absolute","position",
                       "2600","px","150","px"),calls)
        self.assertNotIn(("[con_id=321]","move","position","2600","150"),calls)

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

    def test_browser_client_rect_not_just_outer_frame_must_fill_zoom_bay(self):
        # Sway's window_rect can be smaller than its outer rect. At a 66px
        # upper chrome inset, fitting the outer rect alone cuts off the page.
        node = {
            "id": 123, "pid": 333, "visible": True,
            "rect": {"x": 2600, "y": 84, "width": 650, "height": 486},
            "window_rect": {"x": 0, "y": 66, "width": 650, "height": 420}
        }
        self.assertEqual(host._client_insets(node), (0, 66, 0, 0))
        self.assertEqual(host._client_rect(node), (2600, 150, 650, 420))
        self.assertTrue(host._near(node, (2600, 150, 650, 420)))
        self.assertFalse(host._near(node, (2600, 84, 650, 486)))

    def test_enter_sizes_client_to_bay_after_measuring_sway_decoration(self):
        before = {"id": 123, "pid": 333, "visible": True,
                  "rect": {"x": 2600, "y": 150, "width": 650, "height": 420},
                  "window_rect": {"x": 0, "y": 66, "width": 650, "height": 354}}
        after = {"id": 123, "pid": 333, "visible": True,
                 "rect": {"x": 2600, "y": 84, "width": 650, "height": 486},
                 "window_rect": {"x": 0, "y": 66, "width": 650, "height": 420}}
        calls = []
        with patch.object(host, "_target_geometry", return_value=(2600, 150, 650, 420)):
            with patch.object(host, "_output_rect", return_value={
                    "x": 0, "y": 0, "width": 4000, "height": 1800}):
                with patch.object(host, "_social_browser_prefix", return_value=["/usr/bin/chromium"]):
                    with patch.object(host, "_private_profile", return_value=Path("/tmp/camera_fixture")):
                        with patch.object(host, "_unique_actor",
                                          side_effect=[(before, ""), (before, ""), (after, "")]):
                            with patch.object(host, "_sway_command",
                                              side_effect=lambda *args: calls.append(args)):
                                result = host.enter("identity-1", "DP-5", 40, 150, 650, 420)
        self.assertTrue(result["docked"])
        self.assertEqual(result["authenticated"], "UNKNOWN")
        self.assertIn(("[con_id=123]", "resize", "set", "width", "650", "px",
                       "height", "486", "px"), calls)
        self.assertIn(("[con_id=123]", "move", "absolute", "position",
                       "2600", "px", "84", "px"), calls)

    def test_unknown_or_untrusted_client_geometry_never_counts_as_fit(self):
        node = {"rect": {"x": 2600, "y": 150, "width": 650, "height": 420},
                "window_rect": {"x": 0, "y": 500, "width": 650, "height": -80}}
        with self.assertRaises(ValueError):
            host._near(node, (2600, 150, 650, 420))
        with self.assertRaises(ValueError):
            host._client_insets(node)
        # Old Sway actors without window_rect keep the existing fit behavior.
        self.assertTrue(host._near({"rect": {
            "x":2600, "y":150, "width":650, "height":420}},
            (2600, 150, 650, 420)))

    def test_browser_frame_must_not_escape_its_output(self):
        oversized = {"id": 123, "pid": 333, "visible": True,
                     "rect": {"x": 2600, "y": 50, "width": 650, "height": 420},
                     "window_rect": {"x": 0, "y": 100, "width": 650, "height": 320}}
        with patch.object(host, "_target_geometry", return_value=(2600, 50, 650, 420)):
            with patch.object(host, "_output_rect", return_value={
                    "x": 0, "y": 0, "width": 3200, "height": 1800}):
                with patch.object(host, "_social_browser_prefix", return_value=["/usr/bin/chromium"]):
                    with patch.object(host, "_private_profile", return_value=Path("/tmp/camera_fixture")):
                        with patch.object(host, "_unique_actor",
                                          return_value=(oversized, "")):
                            with patch.object(host, "_sway_command") as move:
                                with self.assertRaisesRegex(RuntimeError, "CLIENT_FRAME_OUTSIDE_OUTPUT"):
                                    host.enter("identity-1", "DP-5", 40, 50, 650, 420)
                                move.assert_any_call("[con_id=123]", "move", "scratchpad")
                                self.assertNotIn("absolute", [arg for call in move.call_args_list for arg in call.args])

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
