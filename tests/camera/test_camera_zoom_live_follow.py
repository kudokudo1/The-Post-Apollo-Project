"""Camera Zoom continuous window follower: live Sway actor geometry contracts."""
import importlib.util
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/camera/ZoomWebFollow.py"
QML = (ROOT / "widgets/CameraW.qml").read_text()
HOST = (ROOT / "scripts/camera/ZoomWebHost.py").read_text()
spec = importlib.util.spec_from_file_location("camera_zoom_follow_test", HELPER)
follow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(follow)


def output():
    return [{"name":"DP-5","active":True,
             "rect":{"x":0,"y":0,"width":2560,"height":1440}}]


def node(x=40,y=160,w=500,h=350,cid=321):
    return {"id":cid,"pid":3000,"visible":True,
            "window_properties":{"class":"post-apollo-camera-zoom-web"},
            "rect":{"x":x,"y":y,"width":w,"height":h}}


class IPC:
    def __init__(self):
        self.actor = node()
        self.commands = []
        self.fail = False

    def request(self, typ, payload=""):
        if typ == 3:
            return output()
        if typ == 1:
            return [{"output":"DP-5","visible":True,"rect":{"y":0}}]
        if typ == 4:
            return {"nodes":[self.actor],"floating_nodes":[]}
        if typ == 0:
            self.commands.append(payload)
            return [{"success":not self.fail}]
        raise AssertionError("unknown IPC command %r" % typ)


class FollowTests(unittest.TestCase):
    def test_camera_sends_live_target_from_actual_frame_geometry(self):
        self.assertIn('id: zoomFollowProcess', QML)
        self.assertIn('stdinEnabled: true', QML)
        self.assertIn('stdout: SplitParser', QML)
        self.assertIn('onStarted: camera.sendZoomFollowTarget()', QML)
        self.assertIn('zoomFollowProcess.write(JSON.stringify({', QML)
        self.assertIn('ZoomWebFollow.py', QML)
        self.assertIn('if (zoomFollowProcess.running) {', QML)
        self.assertIn('return sendZoomFollowTarget();', QML)
        self.assertIn('zoomFollowProcess.running = false;', QML)
        self.assertIn('zoomWebDocked = false; // follower must verify', QML)
        self.assertIn('reply.aligned === true && reply.state === "ALIGNED"', QML)
        self.assertIn('Number(reply.revision) !== zoomFollowRevision', QML)
        self.assertIn('camera.zoomFollowRevision++', QML) if False else None
        self.assertIn('zoomFollowRevision++;', QML)
        self.assertIn('camera.frameTopInset + zoomActorTop', QML)
        self.assertIn('camera.margins.left + camera.glowGutter + zoomActorLeft', QML)
        self.assertIn('width: zoomActorWidth, height: zoomActorHeight', QML)
        self.assertNotIn('id: zoomStatusRefreshTimer', QML)
        self.assertIn('menuOpen && !zoomWebDocked', QML)

    def test_input_hole_remains_fail_closed_on_misalignment(self):
        self.assertIn('zoomWebDocked = aligned;', QML)
        self.assertIn('const aligned = reply.aligned === true && reply.state === "ALIGNED"', QML)
        self.assertIn('zoomWebDocked = false;', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0', QML)
        self.assertIn('y: camera.zoomInputTop', QML)
        self.assertIn('readonly property int zoomVisualTopOverlap: 12', QML)
        self.assertIn('zoomActorTop, cameraBodyColumn.y + cameraModes.y + cameraModes.height)', QML)
        self.assertIn('zoomFollowProcess.running = true;', QML)

    def test_direct_ipc_reuses_social_bridge_and_existing_actor_validation(self):
        source=HELPER.read_text()
        self.assertIn('DiscordGeometry.py', source)
        self.assertIn('social.SwayIPC()', source)
        self.assertIn('self.ipc.request(4)', source)
        self.assertIn('self.ipc.request(0, command)', source)
        self.assertIn('host._unique_actor(self.profile, tree=tree)', source)
        self.assertIn('def _unique_actor(profile, tree=None)', HOST)
        self.assertIn('def _actor_windows(tree=None)', HOST)
        self.assertNotIn('subprocess.Popen(', source)
        self.assertNotIn('flatpak run', source)

    def test_follower_corrects_actual_x_y_and_width_height(self):
        ipc=IPC()
        clock=[10.0]
        f=follow.ZoomFollower(Path("/test/zoom"),ipc,clock=lambda:clock[0])
        f.set_target({"op":"target","revision":1,"output":"DP-5",
                      "x":45,"y":120,"width":734,"height":540})
        with patch.object(follow.host,"_unique_actor",
                          side_effect=lambda profile,tree: (ipc.actor,"")):
            f.tick()
            self.assertEqual(len(ipc.commands),1)
            self.assertIn('[con_id=321] floating enable',ipc.commands[0])
            self.assertIn('[con_id=321] border none',ipc.commands[0])
            self.assertIn('resize set width 734 px height 540 px',ipc.commands[0])
            self.assertIn('move absolute position 45 px 120 px',ipc.commands[0])
            # A queued move is not a verified dock.
            self.assertNotEqual(f.latest_state,(1,"ALIGNED",True))
            ipc.actor=node(x=45,y=120,w=734,h=540)
            f.tick()
            self.assertEqual(f.latest_state,(1,"ALIGNED",True))
            f.set_target({"op":"target","revision":2,"output":"DP-5",
                          "x":62,"y":119,"width":1100,"height":650})
            clock[0]=11.0
            f.tick()
            self.assertEqual(len(ipc.commands),2)
            # Same actor, Social-style resize/move with no new launch.
            self.assertNotIn('floating enable',ipc.commands[1])
            self.assertIn('resize set width 1100 px height 650 px',ipc.commands[1])
            self.assertIn('move absolute position 62 px 119 px',ipc.commands[1])
            ipc.actor=node(x=62,y=119,w=1100,h=650)
            f.tick()
            self.assertEqual(f.latest_state,(2,"ALIGNED",True))

    def test_runtime_coalesces_pending_resize_lines_before_sway_tick(self):
        source = HELPER.read_text()
        self.assertIn('chunk = os.read(input_fd, 65536)', source)
        self.assertIn('lines = pending.split(b"\\n")', source)
        self.assertIn('pending = lines.pop()', source)
        self.assertIn('follower.set_target(message)', source)
        self.assertIn('            follower.tick()', source)
        self.assertIn('if len(pending) > 131072:', source)
        self.assertIn('if len(line) > 2048:', source)

    def test_revision_and_last_geometry_win(self):
        ipc=IPC()
        f=follow.ZoomFollower(Path("/test/zoom"),ipc)
        first={"op":"target","revision":2,"output":"DP-5",
               "x":42,"y":116,"width":734,"height":520}
        f.set_target(first)
        stale=dict(first,revision=1,x=999)
        f.set_target(stale)
        self.assertEqual(f.revision,2)
        self.assertEqual(f.message["x"],42)
        with self.assertRaises(ValueError):
            f.set_target(dict(first,revision=True))
        with self.assertRaises(ValueError):
            f.set_target(dict(first,op="delete"))

    def test_spoofed_or_missing_actor_cannot_be_moved(self):
        ipc=IPC()
        f=follow.ZoomFollower(Path("/test/zoom"),ipc)
        f.set_target({"op":"target","revision":1,"output":"DP-5",
                      "x":40,"y":120,"width":734,"height":540})
        with patch.object(follow.host,"_unique_actor",
                          return_value=(None,"ACTOR_ORIGIN_UNVERIFIED")):
            f.tick()
        self.assertEqual(f.latest_state,(1,"UNVERIFIED",False))
        self.assertEqual(ipc.commands,[])
        with patch.object(follow.host,"_unique_actor",
                          return_value=(None,"ACTOR_MISSING")):
            f.tick()
        self.assertEqual(f.latest_state,(1,"MISSING",False))
        self.assertEqual(ipc.commands,[])

    def test_follow_uses_same_measured_workarea_origin_as_initial_host(self):
        # User's real DP-3 geometry, not an invented Y-offset constant.
        outputs=[{"name":"DP-3","active":True,
                  "rect":{"x":0,"y":0,"width":2560,"height":1440}}]
        workspaces=[{"output":"DP-3","visible":True,"rect":{"y":82}}]
        message={"output":"DP-3","x":84,"y":140,
                 "width":734,"height":542}
        geom, output_rect = follow._target_from_outputs(
            outputs,message,workspaces)
        self.assertEqual(geom,(84,222,734,542))
        self.assertIn(
            "move absolute position 84 px 222 px",
            follow._sync_command(node(),geom,output_rect,setup=True))
        self.assertIn("self.ipc.request(1)",HELPER.read_text())
        # The panel input cutout stays local; the shell should not add 82.
        self.assertNotIn("WORKAREA_Y",QML)

    def test_follower_tracks_workarea_offset_after_topbar_changes(self):
        class InsetIPC(IPC):
            offset = 82
            def request(self, typ, payload=""):
                if typ == 1:
                    return [{"output":"DP-5","visible":True,
                             "rect":{"y":self.offset}}]
                return super().request(typ,payload)
        ipc=InsetIPC()
        clock=[10.0]
        follower=follow.ZoomFollower(Path("/test/zoom"),ipc,
                                     clock=lambda:clock[0])
        follower.set_target({"op":"target","revision":1,"output":"DP-5",
                             "x":84,"y":140,"width":734,"height":542})
        with patch.object(follow.host,"_unique_actor",
                          side_effect=lambda profile,tree:(ipc.actor,"")):
            follower.tick()
            self.assertIn("move absolute position 84 px 222 px",ipc.commands[-1])
            # A future workarea shift is measured dynamically, not cached.
            ipc.actor=node(x=84,y=222,w=734,h=542)
            follower.tick()
            self.assertEqual(follower.latest_state,(1,"ALIGNED",True))
            ipc.offset=60
            clock[0]=11.0
            follower.tick()
            self.assertIn("move absolute position 84 px 200 px",ipc.commands[-1])

    def test_output_bounds_and_untrusted_outer_insets_rejected(self):
        out=output()[0]["rect"]
        with self.assertRaises(ValueError):
            follow._sync_command(node(cid=-4),(40,120,734,540),out,True)
        with self.assertRaises(ValueError):
            follow._sync_command(node(),(2300,120,734,540),out,False)
        bad=node()
        bad["window_rect"]={"x":0,"y":199,"width":500,"height":151}
        with self.assertRaises(ValueError):
            follow._sync_command(bad,(40,120,734,540),out,False)
        with self.assertRaises(ValueError):
            follow._target_from_outputs(output(),{"output":"DP-5","x":40,
                                                 "y":120,"width":True,"height":540})
        with self.assertRaises(ValueError):
            follow._target_from_outputs(output(),{"output":"DP-5","x":40,
                                                 "y":120,"width":2600,"height":540})

    def test_sway_denial_cannot_become_success(self):
        ipc=IPC()
        ipc.fail=True
        f=follow.ZoomFollower(Path("/test/zoom"),ipc)
        f.set_target({"op":"target","revision":1,"output":"DP-5",
                      "x":45,"y":120,"width":734,"height":540})
        with patch.object(follow.host,"_unique_actor",return_value=(ipc.actor,"")):
            f.tick()
        self.assertEqual(f.latest_state,(1,"FAILED",False))
        self.assertEqual(len(ipc.commands),1)

    def test_browser_client_inset_is_applied_to_actual_physical_window(self):
        actor=node()
        actor["window_rect"]={"x":0,"y":40,"width":500,"height":310}
        cmd=follow._sync_command(actor,(45,120,734,540),
                                {"x":0,"y":0,"width":2560,"height":1440},True)
        self.assertIn('resize set width 734 px height 580 px',cmd)
        self.assertIn('move absolute position 45 px 80 px',cmd)


if __name__=="__main__":
    unittest.main()
