"""ForestW V0 source-scoped guards. Native Qt/Wayland acceptance is separate."""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


class ForestLauncherContract(unittest.TestCase):
    def test_dock_uses_shared_component_and_click_toggle(self):
        text = (ROOT / "modules/Forest.qml").read_text()
        self.assertIn("DockButton {", text)
        self.assertIn("onLeftClicked: toggleRequested()", text)
        self.assertIn("open: menuOpen", text)

    def test_standalone_mapped_window_and_closed_mask(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        for phrase in ("PanelWindow {", "WindowPanelFrame {", "visible: true",
                       "root.menuOpen ? root.frameWidth : 0",
                       "root.menuOpen ? root.frameHeight : 0",
                       "WlrKeyboardFocus.OnDemand",
                       "onCloseRequested: root.menuOpen = false"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        self.assertNotIn("WlrKeyboardFocus.Exclusive", text)

    def test_no_active_ai_or_host_mutation_in_scaffold(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        for prohibited in ("Process {", "HttpRequest", "agent turn",
                           "agent session-create", "OllamaChat",
                           "onCompleted: run", "Quickshell.exec"):
            with self.subTest(prohibited=prohibited):
                self.assertNotIn(prohibited, text)
        self.assertIn("ADAPTER NOT CONNECTED", text)

    def test_dock_is_wired_in_shell_only_once(self):
        text = (ROOT / "shell.qml").read_text()
        self.assertEqual(text.count("id: forestHost"), 1)
        self.assertEqual(text.count("id: forestButton"), 1)
        self.assertEqual(text.count("id: forestWindow"), 1)
        self.assertIn("onToggleRequested: forestWindow.toggle()", text)
        # One Forest host inside the standard 8px left Row after To-do.
        left = text.split("// ===== LEFT MODULES", 1)[1].split(
            "// ===== CENTER MODULE", 1)[0]
        self.assertIn("spacing: 8", left)
        self.assertIn("id: forestHost", left)
        self.assertLess(left.index("id: tasksHost"), left.index("id: forestHost"))
        self.assertIn("dockCenterX: shellRoot.margins.left + leftModules.x", left)
        self.assertIn("+ forestHost.x + forestButton.width / 2", left)
        self.assertNotIn("anchors.right: apolloHubHost.left", text)
        self.assertNotIn("anchors.left: apolloHubHost.right", text)
        self.assertEqual(text.count("id: forestHost"), 1)

    def test_ai_palette_and_compact_decorated_icon(self):
        text = (ROOT / "modules/Forest.qml").read_text()
        for required in ('text: "🏕"', 'text: "࣪݁✧"', 'text: "๋⭑"',
                         "GohuText {", "textFormat: Text.PlainText",
                         "readonly property int iconPadding: 10",
                         "readonly property color starColor: dock.open ? Colors.magenta : Colors.white",
                         "implicitWidth: 50", "implicitHeight: 50",
                         "width: dock.width - 2 * dock.iconPadding",
                         "height: dock.height - 2 * dock.iconPadding",
                         "anchors.centerIn: parent",
                         "contentGlowSource: tentFace",
                         "normalForegroundColor: Colors.green",
                         "normalDockGlowColor: Colors.green",
                         "normalContentGlowColor: Colors.green",
                         "openForegroundColor: Colors.magenta",
                         "openGlowColor: Colors.magenta"):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn("NotoText {", text)
        self.assertEqual(text.count("GohuText {"), 3)
        self.assertEqual(text.count("color: dock.starColor"), 2)
        self.assertEqual(text.count("id: tentFace"), 1)
        self.assertEqual(text.count("color: dock.foregroundColor"), 1)
        self.assertNotIn("anchors.verticalCenterOffset", text)
        # Geometry constraint: a 50px square with 10px insets yields
        # a centered 30px square on both axes. Text ink needs live review.
        dock = 50
        pad = 10
        artwork = dock - 2 * pad
        self.assertEqual((dock - artwork) / 2, pad)
        self.assertEqual(artwork, 30)

    def test_tree_selector_uses_local_outline_svg_assets(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn('iconPath: "../assets/forest/cherry-outline.svg"', view)
        self.assertIn('iconPath: "../assets/forest/maple-outline.svg"', view)
        self.assertIn("source: Qt.resolvedUrl(modelData.iconPath)", view)
        self.assertIn("fillMode: Image.PreserveAspectFit", view)
        self.assertIn("width: 26", view)
        self.assertIn("height: 26", view)
        self.assertIn("text: modelData.name", view)
        self.assertIn("onClicked: root.selectedTreeIndex = index", view)
        self.assertIn("index === root.selectedTreeIndex ? Colors.magenta : Colors.white", view)
        self.assertNotIn("modelData.mark", view)
        self.assertNotIn('mark: "🍁"', view)
        self.assertNotIn('mark: "✿"', view)

        # Forest-specific icon identity: foreground and halo are different
        # color axes, with the effect sampling its sibling Image.
        self.assertIn("TextHashGlow {", view)
        self.assertIn("id: treeGlyphGlow", view)
        self.assertIn("safeSource: treeGlyph", view)
        self.assertIn("requestedVisible: root.menuOpen", view)
        self.assertIn('foregroundColor: modelData.name === "CHERRY" ? Colors.white : Colors.orange', view)
        self.assertIn('preferredGlowColor: modelData.name === "CHERRY" ? Colors.magenta : Colors.red', view)
        self.assertIn("z: -1", view)
        self.assertNotIn("layer.effect: DropShadow", view)

        palette = (ROOT / "components/Colors.qml").read_text()
        self.assertIn('#C74EC7', palette)
        self.assertIn('#ED981A', palette)
        for asset, color, min_paths in (
            ("cherry-outline.svg", "#DCF3FA", 6),
            ("maple-outline.svg", "#ED981A", 2),
        ):
            with self.subTest(icon=asset):
                filename = ROOT / "assets/forest" / asset
                svg = ET.parse(filename).getroot()
                ns = "{http://www.w3.org/2000/svg}"
                self.assertEqual(svg.tag, ns + "svg")
                self.assertEqual(svg.attrib.get("viewBox"), "0 0 48 48")
                descendants = list(svg.iter())
                self.assertTrue(any(el.attrib.get("stroke") == color for el in descendants))
                self.assertTrue(any(el.attrib.get("fill") == "none" for el in descendants))
                self.assertGreaterEqual(
                    sum(el.tag == ns + "path" for el in descendants), min_paths)
                # No gradients, masks, bitmap/foreign embeds or filled petals.
                forbidden = {"rect", "image", "foreignObject", "linearGradient",
                             "radialGradient", "filter", "pattern"}
                for el in descendants:
                    self.assertNotIn(el.tag.removeprefix(ns), forbidden)
                    self.assertIn(el.attrib.get("fill", "none"), ("none",))
                    if "stroke" in el.attrib:
                        self.assertEqual(el.attrib["stroke"], color)

        cherry = ET.parse(ROOT / "assets/forest/cherry-outline.svg").getroot()
        petals = cherry.find(".//" + ns + "g[@id='sakura-petals']")
        self.assertIsNotNone(petals)
        self.assertEqual(len(petals.findall(ns + "path")), 5)
        self.assertEqual(
            [petal.attrib.get("transform") for petal in petals.findall(ns + "path")],
            [None] + [f"rotate({i} 24 24)" for i in (72, 144, 216, 288)],
        )
        stamens = cherry.find(".//" + ns + "g[@id='sakura-stamens']")
        self.assertIsNotNone(stamens)
        self.assertGreaterEqual(len(stamens.findall(ns + "circle")), 6)
        maple = ET.parse(ROOT / "assets/forest/maple-outline.svg").getroot()
        contour = maple.find(".//" + ns + "path[@id='maple-contour']")
        veins = maple.find(".//" + ns + "path[@id='maple-veins']")
        self.assertIsNotNone(contour)
        self.assertIsNotNone(veins)
        self.assertGreaterEqual(contour.attrib["d"].count("C"), 8)

    def test_b0_inventory_ui_is_explicit_and_fail_closed(self):
        view = (ROOT / "widgets/ForestW.qml").read_text()
        adapter = (ROOT / "services/forest/ForestInventoryAdapter.qml").read_text()
        policy = (ROOT / "services/forest/ForestInventoryPolicy.js").read_text()
        self.assertIn("ForestInventoryAdapter {", view)
        self.assertIn("onClicked: localInventory.scanModels()", view)
        self.assertIn("SEND LOCKED // B4 TRUSTED HOST NOT CONNECTED", view)
        self.assertIn("B1 / B2 / B3 READY AS CONTRACTS", view)
        self.assertIn("running: false", adapter)
        self.assertIn('Quickshell.shellPath("scripts/forest/ollama_inventory.py")', adapter)
        self.assertIn('"list-models"', adapter)
        self.assertNotIn("ollama_chat_transport", adapter)
        self.assertNotIn("session_journal_v0", adapter)
        self.assertNotIn("Quickshell.execDetached", adapter)
        self.assertIn("generation_enabled !== false", policy)
        self.assertIn("model_count !== value.models.length", policy)
        self.assertIn("InventoryPolicy.beginScan()", adapter)
        self.assertIn("InventoryPolicy.captureStdoutScan(", adapter)
        self.assertIn("InventoryPolicy.captureStderrScan(", adapter)
        self.assertIn("InventoryPolicy.captureExitScan(", adapter)
        self.assertIn("models = scanState.accepted ? scanState.models : []", adapter)
        self.assertIn("if (!s.stdoutSeen || !s.stderrSeen || !s.exitSeen)", policy)
        self.assertIn("s.exitStatus !== 0", policy)
        self.assertNotIn("Qt.callLater(function() { inventory.complete(); })", adapter)
        self.assertTrue((ROOT / "scripts/forest/ollama_inventory.py").is_file())
        self.assertNotIn("Component.onCompleted", adapter)
        self.assertNotIn("running: true", adapter)

        node = r'''
const fs=require("fs"), vm=require("vm");
const ctx={}; vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),ctx);
const base={schema_version:1,provider:"ollama",status:"REACHABLE",
 models:[{name:"qwen3:1.7b",size_bytes:1024}],model_count:1,
 capabilities:["list_models"],generation_enabled:false,tools_enabled:false,sessions_enabled:false};
const parse=o=>ctx.parseInventory(JSON.stringify(o));
if (!parse(base).valid || parse(base).models[0].name!=="qwen3:1.7b")process.exit(1);
for(const x of [
 {...base,generation_enabled:true},{...base,sessions_enabled:true},
 {...base,tools_enabled:true},{...base,model_count:2},
 {...base,capabilities:["list_models","generate"]},
 {...base,models:[{name:"bad name",size_bytes:1}]},
 {...base,provider:"cloud"},
 {...base,models:[{name:"a",size_bytes:1},{name:"a",size_bytes:2}],model_count:2}
])if(parse(x).valid)process.exit(2);
const unavailable={...base,status:"UNAVAILABLE",models:[],model_count:0,capabilities:[],reason:"OLLAMA_UNAVAILABLE"};
if(!parse(unavailable).valid || parse(unavailable).status!=="UNAVAILABLE")process.exit(3);
if(ctx.parseInventory("not-json").valid)process.exit(4);
'''
        result = subprocess.run(
            ["node", "-e", node, str(ROOT / "services/forest/ForestInventoryPolicy.js")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        # All 6 event orders must defer publication until the final event.
        event_orders = r"""
const fs = require("fs"), vm = require("vm");
const ctx = {}; vm.runInNewContext(fs.readFileSync(process.argv[1], "utf8"),ctx);
const output = JSON.stringify({
  schema_version: 1, provider: "ollama", status: "REACHABLE",
  models: [{name:"qwen3:1.7b",size_bytes:100}], model_count:1,
  capabilities:["list_models"], generation_enabled:false,
  tools_enabled:false, sessions_enabled:false
});
const unavailable = JSON.stringify({
  schema_version:1, provider:"ollama", status:"UNAVAILABLE",
  models:[],model_count:0,capabilities:[],generation_enabled:false,
  tools_enabled:false,sessions_enabled:false,reason:"OLLAMA_UNAVAILABLE"
});
const events = {
  o:s=>ctx.captureStdoutScan(s,output),
  e:s=>ctx.captureStderrScan(s,""),
  x:s=>ctx.captureExitScan(s,0,0)
};
const permutations = [
  "oex","oxe","eox","exo","xoe","xeo"
];
for(const order of permutations) {
  let s = ctx.beginScan();
  for(let i=0;i<3;i++) {
    s=events[order[i]](s);
    if(i<2 && (s.complete || s.accepted || s.models.length))process.exit(10);
  }
  if(!s.complete||!s.accepted||s.status!=="REACHABLE"||s.models.length!==1)
    process.exit(11);
  if(ctx.captureStdoutScan(s,output).models.length!==1)process.exit(12);
}
const failures=[
  ["stderr",["o","e","x"],(s,k)=> k==="e" ? ctx.captureStderrScan(s,"unexpected") : events[k](s)],
  ["nonzero",["o","e","x"],(s,k)=> k==="x" ? ctx.captureExitScan(s,2,0) : events[k](s)],
  ["crash",["o","e","x"],(s,k)=> k==="x" ? ctx.captureExitScan(s,0,1) : events[k](s)],
  ["badjson",["x","o","e"],(s,k)=> k==="o" ? ctx.captureStdoutScan(s,"not-json") : events[k](s)],
  ["dup",["o","o","e","x"],(s,k)=> events[k](s)]
];
for(const [label,seq,fn] of failures) {
  let s=ctx.beginScan();
  for(const k of seq) s=fn(s,k);
  if(!s.complete||s.accepted||s.models.length||s.status!=="UNAVAILABLE")
    process.exit(20);
}
let s=ctx.beginScan();
s=ctx.captureExitScan(s,2,0);
s=ctx.captureStderrScan(s,"");
s=ctx.captureStdoutScan(s,unavailable);
if(!s.complete||!s.accepted||s.status!=="UNAVAILABLE"
   ||s.reason!=="OLLAMA_UNAVAILABLE"||s.models.length)process.exit(30);
"""
        result = subprocess.run(
            ["node", "-e", event_orders,
             str(ROOT / "services/forest/ForestInventoryPolicy.js")],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_live_status_is_between_resize_and_close(self):
        text = (ROOT / "widgets/ForestW.qml").read_text()
        first = text.index("id: expandButton")
        middle = text.index("id: liveIndicator")
        last = text.index("id: closeButton")
        self.assertLess(first, middle)
        self.assertLess(middle, last)
        self.assertIn("anchors.right: liveIndicator.left", text)
        self.assertIn("anchors.right: closeButton.left", text)
        self.assertIn('text: "LIVE"', text)
        self.assertIn("border.color: Colors.green", text)
        # LIVE reflects an open QML workspace, not an inference backend.
        self.assertIn("AI engine not connected", text)
        self.assertIn("ADAPTER NOT CONNECTED", text)

    def test_chassis_has_common_top_edge(self):
        text = (ROOT / "widgets/ForestChassisPolicy.js").read_text()
        view = (ROOT / "widgets/ForestW.qml").read_text()
        self.assertIn("function topMargin(", text)
        self.assertIn("    return 0;", text)
        self.assertNotIn("topAllowance = height >= 300 ? 80", text)
        self.assertIn("readonly property int frameTopInset: 9", view)
        self.assertIn("anchors.topMargin: root.frameTopInset", view)

    def test_geometry_script(self):
        script = ROOT / "tests/forest/forest_geometry_test.cjs"
        result = subprocess.run(["node", str(script)], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=10, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
