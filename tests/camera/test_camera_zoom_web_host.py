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
        self.assertIn('fillOpacity: camera.zoomWebVisualHeld ? 0.0 : 0.97', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld', QML)
        self.assertIn('function openZoomMode()', QML)
        entry = QML.split('function openZoomMode()',1)[1].split(
            'function prepareZoomInstall(choice)',1)[0]
        self.assertIn('enterZoomWeb()',entry)
        self.assertNotIn('zoomEnter',entry)
        self.assertNotIn('zoomClientOpen',entry)
        self.assertIn('scripts/camera/ZoomWebHost.py',QML)
        self.assertIn('zoomWebHideProcess.exec(zoomWebArgs("hide"))',QML)
        self.assertIn('menuOpen && !zoomWebVisualHeld ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None',QML)
        self.assertIn('focusable: menuOpen && !zoomWebVisualHeld',QML)
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
        self.assertIn('readonly property int zoomBayBottom: 1', QML)
        self.assertIn('readonly property int zoomFrameBottomFit: 12', QML)
        self.assertIn('readonly property int zoomGuestBottomClearance: 4', QML)
        self.assertIn('id: zoomViewport', QML)
        self.assertIn('id: cameraBodyColumn', QML)
        self.assertIn('cameraModes.y', QML)
        self.assertIn('y: camera.zoomControlDeckBottom + camera.zoomDeckGap', QML)
        self.assertNotIn('cameraModes.height + cameraBodyColumn.spacing', QML)
        self.assertIn('frame.height - y - camera.zoomBayBottom', QML)
        self.assertIn('Math.round(zoomViewport.x)', QML)
        self.assertIn('Math.round(zoomViewport.y)', QML)
        self.assertIn('Math.round(zoomViewport.width)', QML)
        self.assertIn('Math.round(zoomViewport.height)', QML)
        # Keep the 687px Camera, but reserve 4px for the guest below
        # the original 1px frame inset. The browser's top is untouched.
        compact_height, page_start, bottom = 699 - 12, 92 + 3 - 13, 1 + 4
        self.assertEqual(page_start, 82)
        self.assertEqual(compact_height, 687)
        self.assertEqual(compact_height - page_start - bottom, 600)
        self.assertGreater(compact_height - page_start - bottom,
                           compact_height - 169)

    def test_zoom_browser_owns_scroll_and_the_footer_cannot_cover_buttons(self):
        self.assertIn('visible: camera.activeView !== "zoom"', QML)
        self.assertIn('height: frame.height - 169', QML)
        self.assertIn('Zoom is hosted by the sibling zoomViewport instead.', QML)
        self.assertNotIn('height: camera.activeView === "zoom" && camera.zoomWebDocked', QML)
        self.assertIn('visible: camera.activeView !== "zoom"', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0', QML)
        self.assertIn('menuOpen && !zoomWebVisualHeld ? WlrKeyboardFocus.OnDemand', QML)
        # The fallback instructions are scrollable only when the web actor is
        # absent. A QML Flickable must not intercept Zoom's native mouse wheel.
        self.assertIn('id: zoomPage', QML)
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld', QML)

    def test_deck_containment_keeps_default_buttons_and_browser_input_below_them(self):
        self.assertNotIn('zoomVisualTopOverlap', QML)
        self.assertNotIn('zoomTopNudge', QML)
        self.assertIn('readonly property int zoomDeckGap: 3', QML)
        self.assertIn('readonly property int zoomBrowserRise: 13', QML)
        self.assertIn('readonly property int zoomControlDeckBottom: Math.max(', QML)
        self.assertIn('cameraBodyColumn.y + cameraModes.y + cameraModes.height', QML)
        self.assertIn('y: camera.zoomControlDeckBottom + camera.zoomDeckGap', QML)
        self.assertIn('zoomActorTop, zoomControlDeckBottom)', QML)
        self.assertIn('height: 42', QML)
        self.assertIn('height: 34', QML)
        self.assertIn('Math.min(784, viewportWidth - 2 * glowGutter)', QML)
        self.assertIn('Math.min(699, availableFrameHeight)', QML)
        self.assertIn('frame.height - y - camera.zoomBayBottom', QML)
        self.assertIn('- camera.zoomGuestBottomClearance)', QML)
        self.assertIn('readonly property int frameHeightBase:', QML)
        self.assertIn('camera.activeView === "zoom" ? zoomFrameBottomFit : 0', QML)
        self.assertNotIn('readonly property int zoomWebBottomTrim:', QML)
        self.assertIn('width: Math.max(0, frame.width - 2 * camera.zoomWebEdgeInset)', QML)
        self.assertIn('readonly property int zoomActorTop: zoomBayTop', QML)
        self.assertIn('readonly property int zoomActorHeight: zoomBayHeight', QML)
        self.assertIn('anchors.margins: camera.activeView === "zoom" ? 12 : 18', QML)
        self.assertIn('anchors.topMargin: compactZoomDeck ? 8', QML)
        self.assertIn('spacing: compactZoomDeck ? 4', QML)
        self.assertIn('height: cameraBodyColumn.compactZoomDeck ? 32 : 37', QML)
        # Browser actor may sit 10px beneath Camera's opaque deck, but
        # input still starts at the real button boundary.
        compact_deck_end = 8 + 32 + 4 + 2 + 4 + 42
        browser_top = compact_deck_end + 3 - 13
        input_top = max(browser_top, compact_deck_end)
        self.assertEqual((compact_deck_end, browser_top, input_top), (92, 82, 92))
        self.assertEqual((699 - 12) - browser_top - 1 - 4, 600)
        self.assertEqual(600 - (input_top - browser_top), 590)
        self.assertEqual(109 - compact_deck_end, 17) # buttons remain raised
        self.assertEqual(12 + 37 + 8 + 2 + 8 + 42 + 3 - 13, 99)

    def test_opaque_zoom_deck_seals_spare_row_pixels_without_moving_browser(self):
        # The matte covers ALL mode-row pixels independently of the raised
        # guest. Camera's input cutout never includes the live mode controls.
        self.assertIn('id: zoomModeDeckMatte', QML)
        self.assertEqual(QML.count('id: zoomModeDeckMatte'), 1)
        view = QML.index('id: zoomViewport')
        matte = QML.index('id: zoomModeDeckMatte')
        controls = QML.index('id: cameraBodyColumn')
        self.assertLess(view, matte)
        self.assertLess(matte, controls)
        deck = QML[matte:controls]
        for token in (
            'x: 0',
            'y: cameraBodyColumn.y + cameraModes.y',
            'width: frame.width',
            'height: Math.max(0, camera.zoomControlDeckBottom - y + 1)',
            'color: Colors.black',
            'visible: camera.menuOpen && camera.activeView === "zoom"',
            '&& camera.zoomWebVisualHeld'
        ):
            self.assertIn(token, deck)
        self.assertNotIn('MouseArea', deck)
        self.assertNotIn('TapHandler', deck)
        self.assertNotIn('Region.Intersection.Subtract', deck)
        self.assertIn('height: 42', QML)
        self.assertIn('height: 34', QML)
        self.assertIn(
            'y: camera.zoomControlDeckBottom + camera.zoomDeckGap', QML)
        self.assertIn('readonly property int zoomActorTop: zoomBayTop', QML)
        self.assertIn('readonly property int zoomActorHeight: zoomBayHeight', QML)

    def test_zoom_opaque_perimeter_seals_only_inside_camera_frame(self):
        # SurfaceFrame normally uses transparent fill while the external
        # Sway actor is visually held. Four QML backing regions must cover
        # the strips outside that actor without painting over Zoom.
        self.assertIn('fillOpacity: camera.zoomWebVisualHeld ? 0.0 : 0.97', QML)
        self.assertIn('clipContent: camera.zoomWebVisualHeld', QML)
        self.assertIn('id: zoomWebLeftEdgeSeal', QML)
        self.assertIn('id: zoomWebRightEdgeSeal', QML)
        left = QML.split('id: zoomWebLeftEdgeSeal', 1)[1].split(
            'id: zoomWebRightEdgeSeal', 1)[0]
        right = QML.split('id: zoomWebRightEdgeSeal', 1)[1].split(
            'id: zoomViewport', 1)[0]
        for region in (left, right):
            self.assertIn('y: camera.zoomActorTop', region)
            self.assertIn('height: Math.max(0, camera.zoomActorHeight)', region)
            self.assertIn('color: Colors.black', region)
            self.assertIn('visible: camera.zoomWebVisualHeld', region)
            self.assertNotIn('MouseArea', region)
            self.assertNotIn('TapHandler', region)
        self.assertIn('x: 0', left)
        self.assertIn('width: Math.max(0, camera.zoomActorLeft)', left)
        self.assertIn('x: camera.zoomActorLeft + camera.zoomActorWidth', right)
        self.assertIn('width: Math.max(0, frame.width - x)', right)
        self.assertIn('y: camera.zoomActorTop + camera.zoomActorHeight', QML)
        self.assertIn('height: Math.max(0, parent.height - y)', QML)
        # Boundary arithmetic for all three current Camera sizes. The
        # perimeter fills frame-minus-actor exactly, never outside frame.
        for frame_w, frame_h, actor_top in (
                (784, 687, 82), (1000, 1001, 99), (2536, 1333, 99)):
            actor_left, actor_width = 2, frame_w - 4
            # The frame stays fixed; the guest now ends five pixels inside.
            actor_bottom = frame_h - 5
            self.assertEqual(actor_left + actor_width + 2, frame_w)
            self.assertEqual(actor_top + (actor_bottom - actor_top) + 5,
                             frame_h)
            self.assertGreaterEqual(actor_top, 0)
            self.assertLessEqual(actor_bottom, frame_h)
            self.assertEqual((actor_left, frame_w -
                              (actor_left + actor_width)), (2, 2))
        # Keep trusted actor placement, click-through and the compact buttons.
        self.assertIn('readonly property int zoomBrowserRise: 13', QML)
        self.assertIn('zoomActorTop, zoomControlDeckBottom)', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        self.assertIn('height: 34', QML)
        self.assertIn('height: 42', QML)

    def test_zoom_client_fills_frame_and_resizes_from_single_viewport(self):
        # No screen-size-specific hardcoded actor dimensions or browser CSS
        # tricks. This is the one frame-geometry source for host and follower.
        self.assertIn('readonly property int zoomWebEdgeInset: 2',QML)
        self.assertIn('x: camera.zoomWebEdgeInset',QML)
        self.assertIn(
            'width: Math.max(0, frame.width - 2 * camera.zoomWebEdgeInset)',QML)
        self.assertIn('readonly property int zoomBayBottom: 1',QML)
        self.assertIn('readonly property int zoomFrameBottomFit: 12',QML)
        self.assertIn('readonly property int zoomGuestBottomClearance: 4',QML)
        self.assertIn('frame.height - y - camera.zoomBayBottom',QML)
        self.assertIn('- camera.zoomGuestBottomClearance)',QML)
        self.assertIn('readonly property int frameHeightBase:',QML)
        self.assertIn('camera.activeView === "zoom" ? zoomFrameBottomFit : 0',QML)
        self.assertIn('readonly property int zoomActorLeft: zoomBayInset',QML)
        self.assertIn('readonly property int zoomActorTop: zoomBayTop',QML)
        self.assertIn('readonly property int zoomActorWidth: zoomBayWidth',QML)
        self.assertIn('readonly property int zoomActorHeight: zoomBayHeight',QML)
        self.assertIn('width: zoomActorWidth, height: zoomActorHeight',QML)
        self.assertIn('"--width", String(zoomActorWidth), "--height", String(zoomActorHeight)',QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0',QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0',QML)
        # Representative panels all obey the same fitted rectangle rule;
        # this does not assert native Sway placement or browser page zoom.
        for frame_width, frame_height, top, expect_width, expect_height in (
                (784, 687, 82, 780, 600),
                (1000, 1001, 99, 996, 897),
                (2536, 1333, 99, 2532, 1229)):
            self.assertEqual(frame_width - 2 * 2, expect_width)
            self.assertEqual(frame_height - top - 1 - 4, expect_height)
            # Five pixels including the 1px frame inset; measured actor
            # bottom is additionally checked by the host verifier.
            self.assertEqual(frame_height - (top + expect_height), 5)
        # Preserve all four controls and the same header navigation.
        self.assertIn('height: 34',QML)
        self.assertIn('height: 42',QML)
        self.assertIn('label: "↓ DOWNLOAD"',QML)
        self.assertNotIn('--force-device-scale-factor',QML)

    def test_compact_zoom_deck_moves_chrome_not_browser_under_tabs(self):
        # Historical operator measurement (92px local top) is preserved as
        # a comparable baseline, not claimed as current native acceptance.
        # Compact buttons move up 17px; the browser sits 3px below the deck.
        self.assertNotIn('zoomTopNudge', QML)
        self.assertIn('readonly property int zoomDeckGap: 3', QML)
        self.assertIn('readonly property int zoomBrowserRise: 13', QML)
        self.assertIn('               - camera.zoomBrowserRise', QML)
        self.assertIn('zoomActorTop, zoomControlDeckBottom)', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0', QML)
        self.assertIn('height: 34', QML)
        self.assertIn('height: 42', QML)
        self.assertEqual(109 - (8+32+4+2+4+42),17)
        self.assertEqual(8+32+4+2+4+42+3-13,82)
        self.assertEqual((699-12)-82-1-4,600)

    def test_expanded_zoom_reserves_real_deck_above_finance_content(self):
        self.assertIn('readonly property int zoomDeckReserve: Math.max(', QML)
        self.assertIn('zoomControlDeckBottom + zoomDeckGap + zoomBayBottom', QML)
        self.assertIn('readonly property int availableFrameHeight: Math.max(', QML)
        self.assertIn('viewportHeight - frameTopInset - bottomScreenGap', QML)
        self.assertIn('financeSize.height + zoomDeckReserve', QML)
        self.assertIn('readonly property int frameHeightBase:', QML)
        self.assertIn('readonly property int frameHeight: Math.max(', QML)
        self.assertIn('camera.activeView === "zoom" ? zoomFrameBottomFit : 0', QML)
        self.assertIn('camera.activeView === "zoom" && chassisLevel === "expanded"', QML)
        self.assertIn('Math.min(availableFrameHeight,', QML)
        self.assertNotIn('zoomTopNudge', QML)
        self.assertIn('height: 42', QML)
        self.assertIn('height: 34', QML)
        self.assertIn('y: camera.zoomControlDeckBottom + camera.zoomDeckGap', QML)
        self.assertIn('zoomActorTop, zoomControlDeckBottom)', QML)
        header = 12 + 37 + 8 + 2 + 8 + 42
        gap, bottom = 3, 1
        chrome = header + gap + bottom
        self.assertEqual(chrome,113)
        expanded = min(1440 - 9 - 8, 900 + chrome)
        self.assertEqual(expanded,1013)
        self.assertEqual(expanded - header - gap - bottom,900)
        self.assertEqual((expanded - 12) - (header + gap - 13) - bottom - 4,897)
        self.assertEqual(expanded - 12,1001)
        for screen_height, base_height in ((768,751),(1080,900),(1440,900)):
            available=screen_height-9-8
            self.assertLessEqual(min(available,base_height+chrome), available)
        # Finance baseline remains intact for other Camera modes;
        # the shorter Zoom frame has even more workarea clearance.
        fullscreen_frame = 1345
        physical_bottom = 82 + 9 + fullscreen_frame - bottom
        self.assertEqual(physical_bottom,1435)
        zoom_frame = fullscreen_frame - 12
        self.assertEqual(82 + 9 + zoom_frame - bottom,1423)
        rejected_frame = min(1440 - 9 - 8,1345 + chrome)
        self.assertEqual(rejected_frame,1423)
        self.assertGreater(82 + 9 + rejected_frame - bottom,1440)
        # Compact deck moves UP, native viewport is now below buttons.
        compact_end=8+32+4+2+4+42
        self.assertEqual(compact_end,92)
        self.assertEqual((699 - 12) - (compact_end + gap - 13) - bottom - 4,600)

    def test_resize_retains_verified_visual_without_exposing_unverified_input(self):
        self.assertIn('property bool zoomWebVisualHeld: false', QML)
        self.assertIn('zoomWebDocked = aligned;', QML)
        self.assertIn('zoomWebVisualHeld = true;', QML)
        self.assertIn('zoomWebVisualHeld = false;', QML)
        self.assertIn('reply.state === "MISSING"', QML)
        self.assertIn('reply.state === "UNVERIFIED"', QML)
        self.assertIn('reply.state === "FAILED"', QML)
        self.assertIn('zoomWebFollowTargetDebounce.restart();', QML)
        self.assertIn('id: zoomWebFollowTargetDebounce', QML)
        self.assertIn('interval: 90', QML)
        self.assertIn('onTriggered: camera.sendZoomFollowTarget()', QML)
        self.assertIn('zoomWebFollowTargetDebounce.stop();', QML)
        self.assertIn('fillOpacity: camera.zoomWebVisualHeld ? 0.0 : 0.97', QML)
        self.assertIn(
            'visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld', QML)
        self.assertIn('width: camera.zoomWebDocked ? camera.zoomActorWidth : 0', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        # The fallback must not reappear on CHECKING/MISALIGNED if the actor
        # had already passed Sway origin/geometry validation.
        follow = QML.split('function consumeZoomFollow(raw)',1)[1].split(
            'function scheduleZoomWebRealign()',1)[0]
        self.assertIn('if (aligned)',follow)
        trust_loss = follow.split('} else if (reply.state === "MISSING"',1)[1].split('}',1)[0]
        self.assertIn('zoomWebVisualHeld = false;',trust_loss)
        transient = follow.split('// CHECKING/MISALIGNED',1)[1].split('zoomWebState',1)[0]
        self.assertNotIn('zoomWebVisualHeld = false;',transient)
        self.assertIn('reply.state === "MISSING"',follow)
        self.assertIn('reply.state === "UNVERIFIED"',follow)
        self.assertIn('reply.state === "FAILED"',follow)

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

    def test_zoom_host_follows_viewport_and_cutout_stays_below_mode_buttons(self):
        self.assertIn('readonly property int zoomBayInset: Math.max(0, Math.round(zoomViewport.x))', QML)
        self.assertIn('readonly property int zoomBayTop: Math.max(0, Math.round(zoomViewport.y))', QML)
        self.assertIn('readonly property int zoomBayWidth: Math.max(0, Math.round(zoomViewport.width))', QML)
        self.assertIn('readonly property int zoomBayHeight: Math.max(0, Math.round(zoomViewport.height))', QML)
        self.assertIn('zoomWebProcess.exec(zoomWebArgs("enter"))', QML)
        self.assertIn('"--width", String(zoomActorWidth), "--height", String(zoomActorHeight)', QML)
        self.assertIn('x: camera.zoomActorLeft', QML)
        self.assertIn('y: camera.zoomInputTop', QML)
        self.assertIn('height: camera.zoomWebDocked ? camera.zoomInputHeight : 0', QML)
        self.assertIn('zoomInputTop: Math.max(', QML)
        self.assertIn('zoomInputHeight: Math.max(', QML)
        self.assertIn('intersection: Intersection.Subtract', QML)
        # A verified browser has no overlapping QML fallback controls.
        self.assertIn('visible: camera.activeView === "zoom" && !camera.zoomWebVisualHeld', QML)

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
            'y: camera.zoomInputTop',
            'width: camera.zoomWebDocked ? camera.zoomActorWidth : 0',
            'height: camera.zoomWebDocked ? camera.zoomInputHeight : 0'
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
        self.assertEqual(len(calls),6)
        self.assertEqual(calls[0],("[con_id=123]","floating","enable"))
        self.assertEqual(calls[1],("[con_id=123]","border","none"))
        self.assertEqual(calls[2],("[con_id=123]","shadows","disable"))
        self.assertEqual(calls[3][1:3],("resize","set"))
        self.assertEqual(calls[4],("[con_id=123]","move","absolute","position",
                                   "2600","px","150","px"))
        self.assertEqual(calls[5],("[con_id=123]","opacity","set","1"))
        self.assertTrue(result["shadowContained"])

    def test_optional_swayfx_shadows_command_only_targets_verified_zoom(self):
        actor={"id":123,"pid":333,"visible":True,"window_properties":{"class":host.ZOOM_CLASS},
               "rect":{"x":2600,"y":150,"width":650,"height":420}}
        calls=[]
        def deny_shadows(*args):
            calls.append(args)
            if args[1:]==("shadows","disable"):
                raise RuntimeError("SWAY_COMMAND_DENIED")
        with patch.object(host, "_target_geometry", return_value=(2600,150,650,420)):
            with patch.object(host, "_social_browser_prefix", return_value=["/usr/bin/chromium"]):
                with patch.object(host, "_private_profile", return_value=Path("/tmp/camera_test")):
                    with patch.object(host, "_unique_actor", return_value=(actor,"")):
                        with patch.object(host, "_sway_command", side_effect=deny_shadows):
                            result=host.enter("identity-1","HDMI-A-1",40,150,650,420)
        # Unsupported vanilla-Sway effects must not break working Zoom
        # docking or make a false promise that the shadow was suppressed.
        self.assertTrue(result["ok"])
        self.assertTrue(result["docked"])
        self.assertFalse(result["shadowContained"])
        shadow_calls=[x for x in calls if len(x)>=3 and x[1]=="shadows"]
        self.assertEqual(shadow_calls,[("[con_id=123]","shadows","disable")])
        self.assertFalse(any("for_window" in x or "shadows enable" in x for x in calls))
        self.assertIn(("[con_id=123]","move","absolute","position",
                       "2600","px","150","px"),calls)

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

    def test_actual_client_bottom_cannot_escape_bay_despite_sway_tolerance(self):
        target = (68, 173, 780, 600)
        exact = {"rect": {"x": 68, "y": 173, "width": 780, "height": 600}}
        self.assertTrue(host._near(exact, target))
        # Previously accepted: 4px of y error + 4px of height error.
        too_tall = {"rect": {"x": 68, "y": 177, "width": 780, "height": 604}}
        self.assertFalse(host._near(too_tall, target))
        one_pixel_past = {"rect": {"x": 68, "y": 173, "width": 780, "height": 601}}
        self.assertFalse(host._near(one_pixel_past, target))
        one_pixel_short = {"rect": {"x": 68, "y": 173, "width": 780, "height": 599}}
        self.assertTrue(host._near(one_pixel_short, target))
        too_short = {"rect": {"x": 68, "y": 173, "width": 780, "height": 598}}
        self.assertFalse(host._near(too_short, target))
        self.assertIn('target_bottom - 1 <= actual_bottom <= target_bottom',
                      (ROOT / "scripts/camera/ZoomWebHost.py").read_text())

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
